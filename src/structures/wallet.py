from collections import namedtuple

from helpers import file_exists, fetch_file_content, asset_name_decode_hex, indent_block
from logger import log


class Wallet:

    @property
    def total_lovelaces(self):
        total = 0
        for utxo_type in self.utxos:
            for tx_id in self.utxos[utxo_type]:
                total += self.utxos[utxo_type][tx_id].get_asset_amount("lovelaces")
        return total

    @property
    def available_assets(self):
        assets = {}
        for utxo_type in self.utxos:
            for tx_id in self.utxos[utxo_type]:
                utxo = self.utxos[utxo_type][tx_id]
                for asset_name in utxo.asset_list:
                    if asset_name != "lovelaces":
                        assets[asset_name] = assets.get(asset_name, 0) + utxo.get_asset_amount(asset_name)
        return assets

    def __init__(self, address):
        self.path = None
        self.address = None
        self.spendable = None

        log.debug(f"Wallet - Initialising wallet {address}")

        self.set_address_and_spend_state(address)
        self.tx_ins = set()
        self.utxos = {
            "unspent": {},
            "change": {}
        }

    def add_utxo(self, utxo, utxo_type="unspent"):
        self.utxos[utxo_type][utxo.tx_id] = utxo
        self.tx_ins.add(utxo.tx_id)

    @staticmethod
    def resolve_address(address):
        if file_exists(f"{address}/payment.addr"):
            return fetch_file_content(f"{address}/payment.addr")
        return address

    def set_address_and_spend_state(self, address):
        if file_exists(f"{address}/payment.addr"):
            self.path = address
            self.address = fetch_file_content(f"{address}/payment.addr")
            log.debug(f"Wallet - Address {self.address}")
            self.spendable = True
        else:
            self.path = None
            self.address = address
            self.spendable = False
            log.debug("Wallet is NOT spendable (READ ONLY)")

    def populate_with_cli_utxos(self, raw):
        for transaction in raw.split("\n")[2:]:
            items = transaction.strip().split()

            from . import UTXO
            utxo = UTXO(items[0] + '#' + items[1])
            utxo.add_asset("lovelaces", int(items[2]))

            assets = items[4:]

            while len(assets) > 2 and assets[0] == '+':
                utxo.add_asset(assets[2], int(assets[1]))
                assets = assets[3:]

            self.add_utxo(utxo)

    def has_transaction(self, utxo_type, tx_id):
        return any(utxo.tx_id == tx_id for utxo in self.utxos[utxo_type].values())

    @property
    def unspent_tx_ids(self):
        return list(self.utxos["unspent"].keys())

    def get_unspent_tx_assets(self, tx_id):
        return self.utxos["unspent"][tx_id].assets

    def list_utxos_values(self, utxo_type):
        return self.utxos[utxo_type].values()

    def get_wallet_type_total_assets(self, utxo_type):
        assets = {}
        for utxo in self.list_utxos_values(utxo_type):
            for asset_fqn, amount in utxo.assets.items():
                assets[asset_fqn] = assets.get(asset_fqn, 0) + amount
        return assets

    def get_utxo(self, utxo_type, tx_id):
        for utxo in self.utxos[utxo_type].values():
            if utxo.tx_id == tx_id:
                return self, utxo
        return None

    def get_asset(self, utxo_type, asset_fqn):
        return [
            namedtuple("Asset", ["utxo_type", "tx_id", "amount"])(utxo_type, utxo.tx_id,
                                                                  utxo.get_asset_amount(asset_fqn))
            for utxo in self.utxos[utxo_type].values()
            if utxo.get_asset_amount(asset_fqn) is not None
        ]

    def pop_utxo(self, utxo_type, tx_id):
        if self.has_transaction(utxo_type, tx_id):
            utxo = self.get_utxo(utxo_type, tx_id)
            self.utxos[utxo_type] = {key: utxo for key, utxo in self.utxos[utxo_type].items() if utxo.tx_id != tx_id}
            return utxo
        return None

    def add_change(self, tx_id, utxo):
        self.utxos["change"][tx_id] = utxo

    def __str__(self):
        return f"[{self.address}] {'' if self.spendable else '(READ ONLY)'}\n{self.utxos}\n"

    @property
    def formatted_assets(self):
        out = ["List of Assets:\n"]
        out_hex = ["  Hex:\n"]
        out_ascii = ["  Ascii:\n"]
        assets = self.available_assets
        for i, (asset_fqn, asset_amount) in enumerate(assets.items()):
            comma = ',' if i < len(assets) - 1 else ''
            out_hex.append(f"    '{asset_fqn}': {asset_amount:,}{comma}\n")
            out_ascii.append(f"    '{asset_name_decode_hex(asset_fqn)}': {asset_amount:,}{comma}\n")
        out.extend(out_hex)
        out.extend(out_ascii)
        return ''.join(out)

    @property
    def formatted_utxos(self):
        out = ["UTXOs:\n"]
        for tx_id in self.unspent_tx_ids:
            out.append(f"  {tx_id}:\n")
            assets = self.get_unspent_tx_assets(tx_id)
            out_hex = ["  Hex:\n"]
            out_ascii = ["  Ascii:\n"]
            for i, (asset_fqn, asset_amount) in enumerate(assets.items()):
                comma = ',' if i < len(assets) - 1 else ''
                out_hex.append(f"      '{asset_fqn}': {asset_amount:,}{comma}\n")
                out_ascii.append(f"      '{asset_name_decode_hex(asset_fqn)}': {asset_amount:,}{comma}\n")
            out.extend(out_hex)
            out.extend(out_ascii)
        return "".join(out)

    @property
    def formatted(self):
        out = [
            f"Lovelaces: {self.total_lovelaces:,} / {self.total_lovelaces / 1e6:.6f} ADA\n",
            f"{indent_block(self.formatted_assets, 2)}\n",
            f"{indent_block(self.formatted_utxos, 2)}\n",
            "\n "
        ]
        return indent_block(''.join(out), 6)
