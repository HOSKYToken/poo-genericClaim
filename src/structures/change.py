from collections import OrderedDict

from helpers import merge_dicts
from logger import log


class Change:

    def __init__(self):
        self.addresses = None
        self.recipients = None
        self.utxos = {}

    def allocate(self, unspent):
        log.debug(f"Change - Allocating {unspent.asset_string()} in {unspent.tx_id} from {unspent.address}")
        if unspent.tx_id in self.utxos:
            self.utxos[unspent.tx_id].merge(unspent)
        else:
            self.utxos[unspent.tx_id] = unspent

    def get(self, tx_id):
        return self.utxos[tx_id]

    def find_unspent_by_address(self, address):
        found = [unspent for tx_id, unspent in self.utxos.items() if
                 unspent.address == address and unspent.lovelaces > 0]
        return sorted(found, key=lambda unspent: unspent.lovelaces, reverse=True)

    @property
    def tx_ids(self):
        return list(self.utxos.keys())

    @property
    def available_lovelaces(self):
        return {tx_id: unspent.lovelaces for tx_id, unspent in self.utxos.items() if unspent.lovelaces > 0}

    @property
    def total_available_lovelaces(self):
        return sum(self.available_lovelaces.values())

    def set_min_lovelaces(self, address, min_lovelaces):
        self.recipients[address].min_lovelaces = min_lovelaces

    def remove_if_spent(self, tx_id):
        if self.utxos[tx_id].is_empty:
            del self.utxos[tx_id]

    def __str__(self):
        out = ['{']
        for tx_id in self.utxos:
            if len(out) > 1:
                out.append(',')
            out.append(f"'{tx_id}':{{")
            out.append(str(self.utxos[tx_id]))
            out.append("}")
        out.append('}')
        return "".join(out)

    def consume(self, address, asset_fqn, amount):
        log.info(f"Spending - Consuming {amount} {asset_fqn} for {address}")
        if asset_fqn in self.recipients[address]:
            self.recipients[address][asset_fqn] -= amount
            if self.recipients[address][asset_fqn] == 0:
                del self.recipients[address][asset_fqn]
            if len(self.recipients[address]) == 0:
                del self.recipients[address]

    @property
    def all_assets(self):
        return merge_dicts(self.recipients.values())

    @property
    def ordered_by_most_consuming(self):
        def score(recipient):
            assets = self.recipients[recipient]
            return len(assets), sum(val for val in assets.values())

        return OrderedDict(sorted(self.recipients.items(), key=lambda item: score(item[0]), reverse=True))
