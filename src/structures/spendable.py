from collections import namedtuple

from helpers import merge_dicts
from logger import log


class Spendable:
    def __init__(self, wallets):
        self.utxos = wallets.get_all_spendable_utxos()
        self.consumption = []

    def has_available_transactions(self):
        return len(self.utxos) > 0

    def consume(self, tx_id, address, asset_fqn, amount):
        log.debug(f"Spendable - Consuming {amount} {asset_fqn} from {tx_id} to {address}")
        if asset_fqn in self.utxos[tx_id]:
            self.utxos[tx_id][asset_fqn] -= amount
            self.remove_asset(tx_id, asset_fqn)

    def remove_asset(self, tx_id, asset_fqn):
        if self.utxos[tx_id][asset_fqn] == 0:
            del self.utxos[tx_id][asset_fqn]
        if not self.utxos[tx_id]:
            del self.utxos[tx_id]

    def add_consumption(self, tx_id, address, asset_fqn, asset_amount):
        self.consumption.append(
            namedtuple("CONSUMED", ["tx_id", "address", "asset_fqn", "asset_amount"])(tx_id, address, asset_fqn,
                                                                                      asset_amount)
        )

    def apply_consumptions(self):
        log.debug("Spendable - Apply consumptions")

        for consumed in self.consumption:
            self.consume(consumed.tx_id, consumed.address, consumed.asset_fqn, consumed.asset_amount)

        self.consumption = []

    @property
    def available_assets(self):
        return merge_dicts(self.utxos.values())

    def pop(self, tx_id):
        return self.utxos.pop(tx_id)

    def sorted_by_largest_first(self, ordered_spending):
        spending_assets = {key for value in ordered_spending.values() for key in value.keys()}

        def score(utxo):
            matching_assets = spending_assets & utxo.keys()
            total_amount = sum(utxo.values())
            return len(matching_assets), total_amount

        return sorted(self.utxos.items(), key=lambda item: score(item[1]), reverse=True)

    def sorted_by_most_lovelaces_with_least_assets(self):
        def sort_key(assets):
            num_assets = len(assets) - 1
            return num_assets, -assets.get('lovelaces', 0)

        return sorted(self.utxos.items(), key=lambda item: sort_key(item[1]))
