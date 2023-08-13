import sys
import time
from threading import Thread, Event

from daos import DAOSendingQueue, DAOClaimCodes
from helpers import load_json, save_json, fix_end_of_path, file_exists
from logger import log
from structures import Spending
from cardano import CLI

# TODO For now, asset names are kept in human readable form, but database is aware of hex; get wallet returns HRF


class TaskSender(Thread):

    @property
    def service_type(self):
        return "Task"

    @property
    def service_name(self):
        return self.__class__.__name__

    def __init__(self, sessionmaker, settings, path_wallets):
        super().__init__()

        self.sessionmaker = sessionmaker
        self.cli = CLI.create(settings["cardano_cli"])
        self.max_batch_send = settings.get("max_batch_send", 1)
        self.path_wallets = path_wallets
        self.last_state = None
        self.stop = Event()
        self.root_path = fix_end_of_path(settings.get("root_path", "./"))
        self.file_checkpoint = settings.get("file_checkpoint", "checkpoint.json").replace("{root_path}", self.root_path)
        self.checkpoint = load_json(self.file_checkpoint) if file_exists(self.file_checkpoint) else {}
        self.state = self.checkpoint.get("state", "next")

    def change_state(self, state):
        self.checkpoint["state"] = self.state = state
        save_json(self.file_checkpoint, self.checkpoint, pretty=True)

    def start(self):
        super().start()
        return True

    def terminate(self):
        log.info(f"{self.service_name} - Terminating, please wait...")
        self.stop.set()

    def state_next(self):
        if self.last_state != "next":
            log.debug(f"{self.service_name} - Next")

        with self.sessionmaker() as session:
            batch = DAOSendingQueue.get_next_batch(session, self.max_batch_send)

        # log.error(f"{self.service_name} - Terminated early for testing")
        # sys.exit(1)

        if len(batch) > 0:
            log.info(f"{self.service_name} - Got {len(batch)} claim(s) to send")
            self.checkpoint["send_rewards"] = batch
            self.change_state("send")

    def state_send(self):
        log.debug(f"{self.service_name} - Sending")

        # log.error(f"{self.service_name} - Terminated early for testing")
        # sys.exit(1)

        fountain_wallets = set()
        spent = []
        test_claims = []

        with self.sessionmaker() as session:
            for queue_id in self.checkpoint["send_rewards"]:
                claim_code = DAOSendingQueue.get_claim_code(session, queue_id)

                if claim_code is not None:

                    if not claim_code.test_claim:
                        log.debug(f"{self.service_name} - Send {claim_code.address}")
                        log.debug(f"{self.service_name} - Lovelaces: {claim_code.lovelaces}")

                        assets = {"lovelaces": claim_code.lovelaces}

                        for reward in claim_code.rewards:
                            log.debug(f"{self.service_name} - {reward.fqn_asset()}: {reward.amount}")
                            assets[reward.fqn_asset(hex_encoded=True)] = reward.amount

                        log.debug(f"{self.service_name} - Code {claim_code.code}")
                        log.debug(f"{self.service_name} - From Wallet: {claim_code.fountain.wallet}")

                        spent.append({
                            claim_code.address: assets
                        })

                    else:
                        log.debug(f"{self.service_name} - Send {claim_code.address} [TEST CLAIM]")
                        test_claims.append(claim_code.id)

                    fountain_wallets.add(f"{self.path_wallets}{claim_code.fountain.wallet}")

                else:
                    log.error(f"{self.service_name} - Error no claim code found for claim code id: {id}")
                    log.error(f"{self.service_name} - Checkpoint:\n{self.checkpoint}")
                    sys.exit(1)

        if len(spent) > 0:
            result = self.cli.send(list(fountain_wallets), Spending(spent))

            if result.uuid:
                log.debug(f"{self.service_name} - Result {result}")

                self.checkpoint["transaction_uuid"] = result.uuid
                self.checkpoint["sent_tx_id"] = result.tx_id
                self.checkpoint["spent_tx_ids"] = result.tx_ids
            else:
                log.error(f"{self.service_name} - Error, failed to send transaction!")
                sys.exit(1)

        self.checkpoint["spent"] = spent
        self.checkpoint["test_claims"] = test_claims

        self.change_state("wait")

    def state_wait(self):
        log.debug(f"{self.service_name} - Waiting")

        # log.error(f"{self.service_name} - Terminated early for testing")
        # sys.exit(1)

        if len(self.checkpoint["spent"]) > 0:
            spent_tx_ids = self.checkpoint["spent_tx_ids"]
            log.debug(f"{self.service_name} - Checking if {spent_tx_ids} have been spent?")
            complete = self.cli.have_utxos_been_spent(spent_tx_ids)

            if complete:
                sent_tx_id = f"{self.checkpoint['sent_tx_id']}#0"
                log.debug(f"{self.service_name} - Checking if {sent_tx_id} exists?")
                complete = self.cli.does_utxo_exist(sent_tx_id)
        else:
            complete = True

        if complete:
            log.debug(f"{self.service_name} - The wait is over, send transaction confirmed!")
            self.change_state("complete")
        else:
            log.debug(f"{self.service_name} - Send transaction not confirmed yet!")

    def state_complete(self):
        log.debug(f"{self.service_name} - Complete")

        # log.error(f"{self.service_name} - Terminated early for testing")
        # sys.exit(1)

        with self.sessionmaker() as session:
            if len(self.checkpoint["spent"]) > 0:
                for queue_id in self.checkpoint["send_rewards"]:
                    claim_code = DAOSendingQueue.get_claim_code(session, queue_id)
                    DAOClaimCodes.claimed(session, claim_code, tx_hash=self.checkpoint["sent_tx_id"])
                    DAOSendingQueue.delete(session, claim_code)

            if len(self.checkpoint["test_claims"]):
                for claim_code_id in self.checkpoint["test_claims"]:
                    claim_code = DAOClaimCodes.get_by_id(session, claim_code_id)
                    DAOClaimCodes.claimed(session, claim_code, test=True)
                    DAOSendingQueue.delete(session, claim_code)

            session.commit()

            # noinspection PyAttributeOutsideInit
            self.checkpoint = {}
            self.change_state("next")

    def run(self):
        log.info(f"{self.service_name} - Has started")

        while not self.stop.is_set():
            self.last_state = self.state
            getattr(self, f"state_{self.state}")()
            if self.state == self.last_state:
                time.sleep(0.1)

        log.info(f"{self.service_name} - Has stopped")
