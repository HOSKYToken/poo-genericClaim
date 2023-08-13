import os
from threading import Thread, Event

from logger import log


class TaskWalletBalances(Thread):

    @property
    def service_type(self):
        return "Task"

    @property
    def service_name(self):
        return self.__class__.__name__

    def __init__(self, wallet_path, cli):
        super().__init__()
        self.wallet_path = wallet_path
        self.cli = cli
        self.stop = Event()

    def run(self):
        while not self.stop.is_set():
            self.update_wallet_balances()
        log.info(f"{self.service_name} - Stopped")

    def update_wallet_balances(self):
        log.debug(f"{self.service_name} - Updating wallet balances")
        try:
            wallets = os.listdir(self.wallet_path)
        except FileNotFoundError:
            log.error(f"{self.service_name} - Wallet path not found")
            return

        for wallet_name in wallets:
            if not self.stop.is_set():
                wallet_path = f"{self.wallet_path}{wallet_name}"
                try:
                    self.cli.fetch_and_cache_wallet_balance(wallet_path)
                    log.debug(f"{self.service_name} - Updated balance for wallet: {wallet_name}")
                except Exception as e:
                    log.error(f"{self.service_name} - Error updating wallet balance: {wallet_name}, error: {str(e)}")

    def start(self):
        super().start()
        return True

    def terminate(self):
        log.info(f"{self.service_name} - Terminating, please wait....")
        self.stop.set()
