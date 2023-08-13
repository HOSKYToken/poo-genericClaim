from collections import OrderedDict, namedtuple

from helpers import merge_dicts
from logger import log
from structures import Wallet


class Spending:

    def __init__(self, spending=None, roll_up=True):
        self.recipients = {}
        self.roll_up = roll_up
        self.consumption = []
        self.allocate(spending)

    def allocate(self, spending):
        for recipient in spending:
            for address in recipient:
                spend_address = Wallet.resolve_address(address)
                if not self.roll_up:
                    spend_address += '#' + str(
                        sum(1 for key in self.recipients.keys() if key.startswith(f"{spend_address}#")))
                for asset_fqn, asset_amount in recipient[address].items():
                    if spend_address not in self.recipients:
                        self.recipients[spend_address] = {}
                    self.recipients[spend_address][asset_fqn] = self.recipients[spend_address].get(asset_fqn,
                                                                                                   0) + asset_amount

    def consume(self, address, asset_fqn, amount):
        if address in self.recipients:
            if asset_fqn in self.recipients[address]:
                self.recipients[address][asset_fqn] -= amount
                self.remove_asset(address, asset_fqn)

    def remove_asset(self, address, asset_fqn):
        if self.recipients[address][asset_fqn] == 0:
            del self.recipients[address][asset_fqn]
        if len(self.recipients[address]) == 0:
            del self.recipients[address]

    def add_consumption(self, address, asset_fqn, asset_amount):
        self.consumption.append(
            namedtuple("CONSUMED", ["address", "asset_fqn", "asset_amount"])(address, asset_fqn, asset_amount)
        )

    def apply_consumptions(self):
        log.debug("Spending - Apply consumptions")

        for consumed in self.consumption:
            self.consume(consumed.address, consumed.asset_fqn, consumed.asset_amount)

        self.consumption = []

    @property
    def all_assets(self):
        return merge_dicts(self.recipients.values())

    @property
    def ordered_by_most_consuming(self):
        def score(recipient):
            assets = self.recipients[recipient]
            return len(assets), sum(val for val in assets.values())

        return OrderedDict(sorted(self.recipients.items(), key=lambda item: score(item[0]), reverse=True))
