from helpers import merge_dicts


class Spend:
    def __init__(self, address, tx_id):
        self.address = address
        self.tx_id = tx_id
        self.lovelaces = 0
        self.min_lovelaces = 0
        self.assets = {}

    def add_asset(self, asset_fqn: str, amount: int):
        if asset_fqn == "lovelaces":
            self.lovelaces += amount
        else:
            self.assets[asset_fqn] = self.assets.get(asset_fqn, 0) + amount

    def separate_asset_spend(self):
        spend = Spend(self.address, self.tx_id)
        spend.assets = self.assets
        self.assets = {}
        return spend

    def merge(self, spend):
        self.lovelaces += spend.lovelaces
        self.assets = merge_dicts([self.assets, spend.assets])

    @property
    def available_lovelaces(self):
        return self.lovelaces - self.min_lovelaces

    @property
    def lovelaces_needed_to_meet_minimum(self):
        return self.min_lovelaces - self.lovelaces

    @property
    def is_empty(self):
        return self.lovelaces == 0 and not self.has_assets

    @property
    def has_assets(self):
        return len(self.assets) > 0

    @property
    def tx_out_plus_list(self):
        return f"{self.address.split('#')[0]}+{max(self.lovelaces, self.min_lovelaces)}{self.asset_plus_list}"

    @property
    def asset_plus_list(self):
        asset_list = []
        for asset_fqn, asset_amount in self.assets.items():
            asset_list.append(f"{asset_amount} {asset_fqn}")
        return f'+"{"+".join(asset_list)}"' if len(asset_list) > 0 else ""

    def asset_string(self):
        out = []
        if self.lovelaces > 0:
            out.append(f"lovelaces: {self.lovelaces}")
        for asset_fqn, asset_amount in self.assets.items():
            out.append(f"{asset_fqn}: {asset_amount}")
        return ",".join(out)

    def __str__(self):
        return ",".join([
            # f"'address': {self.address}",
            f"'lovelaces': {self.lovelaces}",
            f"'min_lovelaces': {self.min_lovelaces}",
            # f"'tx_ids': {self.tx_ids}",
            f"'tx_id': {self.tx_id}",
            f"'assets': {self.assets}"
        ])
