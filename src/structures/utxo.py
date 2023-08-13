from logger import log


class UTXO:
    def __init__(self, tx_id: str):
        log.debug(f"UTXO - Assigning {tx_id}")
        self.tx_id = tx_id
        self.assets = {}

    @property
    def asset_list(self):
        return list(self.assets.keys())

    def add_asset(self, asset_fqn: str, amount: int):
        self.assets[asset_fqn] = amount

    def get_asset_amount(self, asset_fqn: str):
        return self.assets.get(asset_fqn, None)

    def reduce_asset(self, asset_fqn: str, amount: int):
        log.debug(f"UTXO - Reduce {self.assets[asset_fqn]} : {asset_fqn} by {amount} in UTXO {self.tx_id}")
        self.assets[asset_fqn] -= amount
        if self.assets[asset_fqn] == 0:
            del self.assets[asset_fqn]
            log.debug(f"UTXO - {asset_fqn} all consumed, removing asset")
        else:
            log.debug(f"UTXO - {asset_fqn} change {self.assets[asset_fqn]}")

    def __str__(self):
        return str(self.assets)

    def __repr__(self):
        return self.__str__()
