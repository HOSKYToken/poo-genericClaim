class Wallets:
    def __init__(self):
        self.wallets = {}

    @property
    def list(self):
        return [self.get_wallet(address) for address in self.wallets]

    def get_wallet(self, address):
        return self.wallets[address]

    def get_wallet_by_tx_id(self, tx_id):
        for address, wallet in self.wallets.items():
            if tx_id in wallet.tx_ins:
                return wallet
        return None

    def create_wallet(self, address):
        self.attach_wallet(Wallet(address))
        return self.wallets[address]

    def attach_wallet(self, wallet):
        self.wallets[wallet.address] = wallet

    def get_all_spendable_utxos(self):
        utxos = {}
        for utxo_type in ["unspent", "change"]:
            for wallet in self.wallets.values():
                if wallet.spendable:
                    for tx_id in wallet.utxos[utxo_type]:
                        if tx_id not in utxos:
                            utxos[tx_id] = {}
                        for asset_fqn, asset_amount in wallet.utxos[utxo_type][tx_id].assets.items():
                            utxos[tx_id][asset_fqn] = utxos[tx_id].get(asset_fqn, 0) + asset_amount
        return utxos

    def get_total_spendable_assets(self):
        assets = {}
        for utxo_type in ["unspent", "change"]:
            for wallet in self.wallets.values():
                if wallet.spendable:
                    for asset_fqn, amount in wallet.get_wallet_type_total_assets(utxo_type).items():
                        assets[asset_fqn] = assets.get(asset_fqn, 0) + amount
        return assets

    def get_change_address(self, tx_id):
        for address, wallet in self.wallets.items():
            if tx_id in wallet.tx_ins:
                return wallet.address
        return None

    def get_sorted_spendable_assets_by_asset(self, asset_fqn):
        assets = []
        for utxo_type in ["unspent", "change"]:
            for wallet in self.wallets.values():
                if wallet.spendable:
                    assets.extend(wallet.get_asset(utxo_type, asset_fqn))

        return sorted(assets, key=lambda x: (x.utxo_type, x.amount))

    def pop_utxo(self, utxo_type, tx_id):
        for wallet in self.wallets.values():
            utxo = wallet.pop_utxo(utxo_type, tx_id)
            if utxo:
                return utxo

    def __str__(self):
        return '\n'.join(str(wallet) for wallet in self.wallets.values())
