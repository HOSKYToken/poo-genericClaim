from collections import namedtuple

from logger import log
from structures import Spendable, Wallet, Spent, Change, Spend, Unspent


class TransactionManager:

    def __init__(self, cli, wallet_addresses, spending, change_address):
        log.debug(f"TransactionManager - Allocating wallets {wallet_addresses}")
        self.cli = cli
        self.wallets = self.cli.load_wallets(wallet_addresses)
        self.spendable = Spendable(self.wallets)
        self.spending = spending
        self.change_address = Wallet.resolve_address(change_address)
        self.spent = Spent()
        self.change = Change()
        self.fee = 0

        log.debug(f"TransactionManager - Change address {self.change_address}")

    # TODO Need to alter this for multiple different source wallets, i.e. to take tx_in's specific!

    def send(self, cmd_uuid):
        self.verify_availability()

        self.allocate_spends()
        self.allocate_change()

        while True:
            self.move_change_assets_to_spent()
            self.allocate_non_roll_up_change_lovelace_to_spent()
            self.allocate_spent_min_lovelaces()

            self.fee = self.cli.calculate_transaction_fee(cmd_uuid, self)
            log.debug(f"TransactionManager - Fee {self.fee}")

            required_spent_lovelaces = self.spent.total_lovelaces_needed_to_meet_minimum
            log.debug(
                f"TransactionManager - {required_spent_lovelaces} total lovelaces required for spent transactions")

            available_change_lovelaces = self.change.total_available_lovelaces
            log.debug(f"TransactionManager - {available_change_lovelaces} total change lovelaces")

            if available_change_lovelaces < self.fee + required_spent_lovelaces:
                log.debug("TransactionManager - Not enough lovelace available in change")
                if self.spendable.has_available_transactions():
                    log.info("TransactionManager - Need to add another spendable transaction")
                    next_spendable_tx_id = self.spendable.sorted_by_most_lovelaces_with_least_assets()[0][0]
                    self.move_spendable_tx_to_change(next_spendable_tx_id)
                else:
                    msg = f"TransactionManager - Not enough available assets to complete send"
                    log.error(msg)
                    from . import ExceptionNotEnoughAssets
                    raise ExceptionNotEnoughAssets(msg)
            else:
                log.debug(
                    "TransactionManager - We potentially have enough available change lovelace to finalise transactions"
                )
                allocated_count = self.allocate_minimum_change_needed()

                if allocated_count == 0:
                    log.debug(f"TransactionManager - We have enough to send transaction!")
                    break

        self.allocate_fee(cmd_uuid)
        self.allocate_remaining_change()

        self.log_spend_state()

    def verify_availability(self):
        log.info("TransactionManager - Verifying availability")

        spendable_assets = self.spendable.available_assets
        spending_assets = self.spending.all_assets

        for coin, required_amount in spending_assets.items():
            if coin not in spendable_assets:
                msg = f"TransactionManager - Asset {coin} not found as a spendable asset"
                log.error(msg)
                from . import ExceptionAssetNotFound
                raise ExceptionAssetNotFound(msg)
            if spending_assets[coin] > spendable_assets[coin]:
                msg = f"TransactionManager - Not enough {coin}, {spending_assets[coin]} > {spendable_assets[coin]}"
                log.error(msg)
                from . import ExceptionNotEnoughAssets
                raise ExceptionNotEnoughAssets(msg)

    def consume_spendable(self, ordered_spendable, address, asset_fqn, amount):
        amount_needed = amount
        for i, (tx_id, spendable_assets) in enumerate(ordered_spendable):
            if asset_fqn in spendable_assets and spendable_assets[asset_fqn] > 0:
                available_spend_amount = min(spendable_assets[asset_fqn], amount_needed)
                spend = Spend(address, tx_id)
                log.debug(f"TransactionManager - Reducing spendable {tx_id} by {available_spend_amount} {asset_fqn}")
                spendable_assets[asset_fqn] -= available_spend_amount
                spend.add_asset(asset_fqn, available_spend_amount)
                amount_needed -= available_spend_amount
                self.spent.allocate(spend)
                self.spending.add_consumption(address, asset_fqn, amount)

                if amount_needed == 0:
                    return

        from . import ExceptionNotEnoughAssets
        raise ExceptionNotEnoughAssets(f'Not enough {asset_fqn}')

    def allocate_spends(self):
        log.info("TransactionManager - Allocate spends to spent")

        ordered_spending = self.spending.ordered_by_most_consuming
        ordered_spendable = self.spendable.sorted_by_largest_first(ordered_spending)

        for address, assets in ordered_spending.items():
            for asset_fqn, asset_amount in assets.items():
                log.debug(f"TransactionManager - Send {asset_amount} {asset_fqn} to {address}")
                self.consume_spendable(ordered_spendable, address, asset_fqn, asset_amount)

        self.spending.apply_consumptions()

    @property
    def roll_up_change(self):
        return self.change_address is not None

    def allocate_change(self):
        log.info("TransactionManager - Allocating change")

        spent_tx_ids = self.spent.tx_ids

        for tx_id, utxo_assets in self.spendable.utxos.items():
            if tx_id in spent_tx_ids or self.roll_up_change:
                if utxo_assets:
                    address = self.change_address if self.roll_up_change else self.wallets.get_wallet_by_tx_id(
                        tx_id).address
                    unspent = Unspent(tx_id, address)
                    for asset_fqn, asset_amount in utxo_assets.items():
                        if asset_amount > 0:
                            unspent.add_asset(asset_fqn, asset_amount)
                            self.spendable.add_consumption(tx_id, address, asset_fqn, asset_amount)
                    self.change.allocate(unspent)

        self.spendable.apply_consumptions()

    def move_change_assets_to_spent(self):
        log.info("TransactionManager - Moving any assets in change to spent")

        for tx_id in self.change.tx_ids:
            change = self.change.get(tx_id)
            if change.has_assets:
                self.spent.allocate(change.separate_assets_as_spend())

    def allocate_non_roll_up_change_lovelace_to_spent(self):
        log.info("TransactionManager - Allocate lovelace only change to spent")

        for tx_id in self.change.tx_ids:
            change = self.change.get(tx_id)
            if not change.has_assets:
                if not self.roll_up_change and change.address not in self.spent.recipients:
                    spend = Spend(change.address, change.tx_id)
                    self.spent.allocate(spend)

    def allocate_spent_min_lovelaces(self):
        log.info("TransactionManager - Allocate minimum lovelaces from change to spent transactions")

        for address in self.spent.addresses:
            spent = self.spent.get(address)

            min_lovelaces = self.cli.determine_min_lovelaces(spent.address, spent.min_lovelaces, spent.asset_plus_list)
            spent.min_lovelaces = min_lovelaces

            needed_lovelaces = spent.lovelaces_needed_to_meet_minimum

            if needed_lovelaces > 0:
                unspent_found = self.change.find_unspent_by_address(address)

                if bool(unspent_found):
                    for unspent in unspent_found:
                        if unspent.lovelaces > 0:
                            available_lovelaces = min(needed_lovelaces, unspent.lovelaces)
                            log.debug(f"TransactionManager - allocating {available_lovelaces} lovelaces to {address}")
                            spent.lovelaces += available_lovelaces
                            unspent.lovelaces -= available_lovelaces
                            self.change.remove_if_spent(unspent.tx_id)
                            needed_lovelaces -= available_lovelaces
                            if needed_lovelaces == 0:
                                break

    """
    def allocate_change_min_lovelaces(self):
        log.info("TransactionManager - Allocate change minimum lovelaces")

        for address in self.change.addresses:
            min_lovelaces = self.cli.calc_min_lovelaces(self.change.tx_out_plus_list(address))
            self.change.set_min_lovelaces(address, min_lovelaces)
    """

    def move_spendable_tx_to_change(self, tx_id):
        log.debug(f"TransactionManager - Moving spendable transaction to change {tx_id}")
        address = self.wallets.get_wallet_by_tx_id(tx_id).address

        unspent = Unspent(tx_id, address)
        for asset_fqn, asset_amount in self.spendable.utxos[tx_id].items():
            if asset_amount > 0:
                unspent.add_asset(asset_fqn, asset_amount)
                self.spendable.add_consumption(tx_id, address, asset_fqn, asset_amount)

        self.change.allocate(unspent)
        self.spendable.apply_consumptions()

    @staticmethod
    def allocate_remaining_change_by_ratio(target_amounts, change_amounts):
        total_target_amount = sum(target_amounts.values())
        total_change_amount = sum(change_amounts.values())
        target_ratios = {target: target_amount / total_target_amount for target, target_amount in
                         target_amounts.items()}
        ratio = total_target_amount / total_change_amount
        allocations = []
        total_allocation = 0  # keep track of total allocated amount

        for change_address, change_amount in change_amounts.items():
            for target, target_ratio in target_ratios.items():
                allocation_amount = int(change_amount * ratio * target_ratio)
                total_allocation += allocation_amount
                allocations.append(
                    namedtuple("SPEND", ["spend_address", "change_address", "lovelaces"])(
                        target, change_address, allocation_amount
                    )
                )

        # Check if there's a rounding discrepancy
        discrepancy = total_target_amount - total_allocation

        if discrepancy != 0:
            # Allocate the remaining amount to the last allocation
            last_allocation = allocations[-1]
            allocations[-1] = namedtuple("SPEND", ["spend_address", "change_address", "lovelaces"])(
                last_allocation.spend_address, last_allocation.change_address, last_allocation.lovelaces + discrepancy
            )

        return allocations

    def process_ratio_allocation(self, needed, available):
        allocations = TransactionManager.allocate_remaining_change_by_ratio(needed, available)

        count = 0
        for allocate in allocations:
            change = self.change.get(allocate.change_address)
            spend = Spend(allocate.spend_address, change.tx_id)
            spend.lovelaces = allocate.lovelaces
            log.debug(f"TransactionManager - spending {allocate.lovelaces} change")
            change.lovelaces -= allocate.lovelaces
            self.spent.allocate(spend)
            self.change.remove_if_spent(change.tx_id)
            count += 1
        return count

    def allocate_minimum_change_needed(self):
        log.info("TransactionManager - Allocating fee and remaining change")
        lovelaces_needed = self.spent.lovelaces_needed_to_meet_minimum
        available_lovelaces = self.change.available_lovelaces
        return self.process_ratio_allocation(lovelaces_needed, available_lovelaces)

    def allocate_fee(self, cmd_uuid):
        self.fee = self.cli.calculate_transaction_fee(cmd_uuid, self)
        log.debug(f"TransactionManager - Allocating fee {self.fee}")
        available_lovelaces = self.change.available_lovelaces
        self.process_ratio_allocation({"fee": self.fee}, available_lovelaces)

    def allocate_remaining_change(self):
        log.info("TransactionManager - Allocating remaining change")

        for tx_id in self.change.tx_ids:
            change = self.change.get(tx_id)
            self.spent.allocate(change.as_spend)
            log.debug(f"TransactionManager - spending {change.lovelaces} change")
            change.lovelaces -= change.lovelaces
            self.change.remove_if_spent(change.tx_id)

    @property
    def spent_tx_ids(self):
        return self.spent.tx_ids

    @property
    def spending_wallet_keys(self):
        return [f"{wallet.path}/payment.skey" for wallet in self.wallets.list]

    def log_spend_state(self):
        log.debug("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        log.debug(f"TransactionManager - Spending: {self.spending.recipients}")
        log.debug(f"TransactionManager - Spendable: {self.spendable.utxos}")
        log.debug(f"TransactionManager - Spent: {self.spent}")
        log.debug(f"TransactionManager - Change: {self.change}")
        log.debug("====================================")
