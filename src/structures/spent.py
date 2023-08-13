from logger import log


class Spent:

    def __init__(self):
        self.recipients = {}
        self.tx_ids = set()

    def allocate(self, spend):
        log.debug(f"Spent - allocating {spend.asset_string()} in {spend.tx_id} to {spend.address}")
        if spend.address in self.recipients:
            self.recipients[spend.address].merge(spend)
        else:
            self.recipients[spend.address] = spend

        self.tx_ids.add(spend.tx_id)

    def has(self, address):
        return address in self.recipients

    def get(self, address):
        return self.recipients[address]

    @property
    def addresses(self):
        return list(self.recipients.keys())

    @property
    def total_lovelaces_needed_to_meet_minimum(self):
        return sum(self.lovelaces_needed_to_meet_minimum.values())

    @property
    def lovelaces_needed_to_meet_minimum(self):
        recipients = {}
        for address in self.recipients:
            lovelaces_needed = self.recipients[address].lovelaces_needed_to_meet_minimum
            if lovelaces_needed > 0:
                recipients[address] = lovelaces_needed
        return recipients

    def tx_out_plus_list(self, address):
        return self.recipients[address].tx_out_plus_list

    def set_min_lovelaces(self, address, min_lovelaces):
        self.recipients[address].min_lovelaces = min_lovelaces

    def needed_lovelaces_to_meet_minimum(self, address):
        return self.recipients[address].needed_lovelaces_to_meet_minimum

    def __str__(self):
        out = ['{']
        for address in self.recipients:
            if len(out) > 1:
                out.append(',')
            out.append(f"'{address}':{{")
            out.append(str(self.recipients[address]))
            out.append("}")
        out.append('}')
        return "".join(out)
