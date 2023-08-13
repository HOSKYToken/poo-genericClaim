import json
import os
import subprocess
import sys
import time
import uuid
from collections import namedtuple

from .transaction_manager import TransactionManager
from helpers import (
    check_path_does_not_exist_or_stop,
    create_folder_path,
    fetch_file_content,
    file_exists,
    save_json,
    delete_files
)
from logger import log
from structures import Wallet, Wallets


class CLI:
    RETRIES = 5

    LOVELACES_IN_ADA = 1000000

    FEE_TOLERANCE = 2500

    PATH_TEMP = "/tmp/cardano_cli/"

    def __init__(self, cli_path, socket_path, network="--mainnet", era=None, debug=False, temp_path=PATH_TEMP):
        self.cli_path = cli_path
        self.socket_path = socket_path
        self.network = f"--{network}"
        self.era = f"--{era}-era" if era else ""
        self.debug = debug
        self.temp_path = temp_path
        if not file_exists(self.temp_path):
            create_folder_path(self.temp_path)

    @staticmethod
    def create(cli_settings):
        if cli_settings is None:
            msg = "The cardano_cli parameters were missing in the settings file"
            log.error(msg)
            from . import ExceptionCardanoCLISettingsNotSupplied
            raise ExceptionCardanoCLISettingsNotSupplied(msg)
        return CLI(
            cli_settings["path"],
            cli_settings["socket"],
            network=cli_settings["network"],
            era=cli_settings["era"],
            debug=cli_settings["debug"],
            temp_path=cli_settings["temp_path"] if "temp_path" in cli_settings else CLI.PATH_TEMP
        )

    def execute(self, params, stop_on_error=True):
        os.environ["CARDANO_NODE_SOCKET_PATH"] = self.socket_path
        retry = self.RETRIES
        completed = False
        rc = None
        while not completed and retry > 0:
            try:
                cmd = f"{self.cli_path} {params}"

                if self.debug:
                    log.debug(f"CLI - Parameters [{params}]")

                result = subprocess.run(cmd, shell=True, capture_output=True)
                stdout = result.stdout.decode().strip()
                stderr = result.stderr.decode().strip()

                if result.stderr:
                    log.error(f"CLI - Error [{params}] => {stderr}")
                    if stop_on_error:
                        sys.exit(1)

                if self.debug:
                    log.debug(f"CLI - Response {stdout if len(stdout) > 0 else None}")

                rc = namedtuple("Result", "stdout, stderr")(stdout, stderr)

                completed = True
            except Exception as e:
                log.error(f"CLI - Exception [{params}] {type(e).__name__} => {str(e)}")
                retry -= 1
                time.sleep(retry)
                log.info(f"CLI - Retry [{params}] : {self.RETRIES - retry} of {self.RETRIES}")

        if not completed:
            log.error(f"CLI - Terminating, unable to execute {params}")
            sys.exit(1)

        return rc

    def get_tip(self):
        cmd = f"query tip {self.network}"
        return json.loads(self.execute(cmd).stdout)

    def get_utxos(self, wallet):
        cmd = f"query utxo --address {wallet.address} {self.network}"
        return self.execute(cmd).stdout

    def does_utxo_exist(self, tx_id):
        cmd = f"query utxo --tx-in {tx_id} {self.network}"
        result = self.execute(cmd).stdout
        print(f"does_utxo_exist {tx_id} : {result}")
        if len(result.split("\n")[2:]) == 0:
            print("does_utxo_exist False")
            return False
        print("does_utxo_exist True")
        return True

    def have_utxos_been_spent(self, tx_ids):
        for tx_id in tx_ids:
            print(tx_id)
            if self.does_utxo_exist(tx_id):
                print("yes")
                return False
        return True

    def load_wallet(self, address):
        log.debug(f"CLI - Load wallet {address}")
        wallet = Wallet(address)
        wallet.populate_with_cli_utxos(self.get_utxos(wallet))
        log.debug(f"CLI - Wallet total lovelaces {wallet.total_lovelaces}")
        log.debug(f"CLI - Wallet available assets {wallet.available_assets}")
        return wallet

    def load_wallets(self, addresses):
        log.debug("CLI - Load wallets")
        wallets = Wallets()
        for address in addresses:
            wallet = self.load_wallet(address)
            wallets.attach_wallet(wallet)
        return wallets

    def fetch_and_cache_wallet_balance(self, wallet_path):
        log.debug(f"CLI - Fetch and cache wallet balance {wallet_path}")

        if file_exists(wallet_path):
            wallet = self.load_wallet(wallet_path)
            save_json(
                f"{wallet_path}/balance.json",
                {
                    "address": wallet.address,
                    "lovelaces": wallet.total_lovelaces,
                    "assets": wallet.available_assets
                },
                pretty=True
            )

    def create_keys(self, folder, staking=False):
        log.debug(f"CLI - Create keys {folder} : Staking={staking}]")

        key_type = 'staking' if staking else 'payment'
        folder_and_name = f'{folder}/{key_type}'
        vkey = f'{folder_and_name}.vkey'
        skey = f'{folder_and_name}.skey'
        addr = f'{folder_and_name}.addr'

        address = f"{'stake-address' if staking else 'address'} "
        self.execute(
            f"{address} key-gen --verification-key-file {vkey} --signing-key-file {skey}"
        )

        self.execute(
            f"{address} build "
            f"--{'stake-' if staking else 'payment-'}verification-key-file {vkey} --out-file {addr} {self.network}"
        )

        address = fetch_file_content(addr)

        return namedtuple('Keys', 'path, vkey, skey, address')(folder, vkey, skey, address)

    def create_wallet(self, folder, staking=False):
        log.debug(f"CLI - Create wallet {folder} : Staking={staking}]")
        check_path_does_not_exist_or_stop(folder, f"Folder {folder} exists, stopping!")
        create_folder_path(folder)

        keys_payment = self.create_keys(folder)
        keys_staking = self.create_keys(folder, staking=True) if staking else None

        return namedtuple("Address", "payment, staking")(keys_payment, keys_staking)

    def generate_protocol_file(self):
        log.debug("CLI - Generating protocol file")
        cmd = [
            f"query protocol-parameters {self.network} --out-file {self.PATH_TEMP}protocol.json",
        ]
        return int(self.execute(" ".join(cmd)).stdout.split(' ')[1])

    def calculate_min_lovelaces(self, tx_out):
        log.debug("CLI - Calculating minimum fees")
        if not file_exists(f"{self.PATH_TEMP}protocol.json"):
            self.generate_protocol_file()

        cmd = [
            f"transaction calculate-min-required-utxo {self.era}",
            f"--tx-out {tx_out}",
            f"--protocol-params-file {self.PATH_TEMP}protocol.json"
        ]

        return int(self.execute(" ".join(cmd)).stdout.split(' ')[1])

    def determine_min_lovelaces(self, address, current_min_lovelaces, asset_plus_list):
        address = address.split('#')[0]
        while True:
            tx_out = f"{address}+{current_min_lovelaces}{asset_plus_list}"
            min_lovelaces = self.calculate_min_lovelaces(tx_out)
            if min_lovelaces == current_min_lovelaces:
                return min_lovelaces
            current_min_lovelaces = min_lovelaces

    def build_raw_transaction(self, cmd_uuid, transaction_manager, fee):
        log.debug(f"CLI - Build raw transaction {cmd_uuid}")

        cmd = [f"transaction build-raw --fee {fee}"]

        count_tx_in = 0
        count_tx_out = 0
        count_witnesses = 0

        for tx_in in transaction_manager.spent_tx_ids:
            cmd.append(f"--tx-in {tx_in}")
            count_tx_in += 1

        for address in transaction_manager.spent.addresses:
            if address != "fee":
                cmd.append(f"--tx-out {transaction_manager.spent.tx_out_plus_list(address)}")
                count_tx_out += 1

        cmd.append(f"--out-file {self.temp_path}{cmd_uuid}.raw")

        rc = self.execute(" ".join(cmd))

        build_raw = namedtuple("BUILD_RAW", "stdout, stderr, count_tx_in, count_tx_out, count_witnesses")

        return build_raw(rc.stdout, rc.stderr, count_tx_in, count_tx_out, count_witnesses)

    def calculate_transaction_fee(self, cmd_uuid, transaction_manager):
        log.debug(f"CLI - Calculate transaction fee for {cmd_uuid}")

        raw = self.build_raw_transaction(cmd_uuid, transaction_manager, fee=transaction_manager.fee)

        cmd = [
            f"transaction calculate-min-fee {self.network}",
            f"--tx-body-file {self.temp_path}{cmd_uuid}.raw",
            f"--tx-in-count {raw.count_tx_in}", f"--tx-out-count {raw.count_tx_out}",
            f"--witness-count {raw.count_witnesses}",
            f"--protocol-params-file {self.PATH_TEMP}protocol.json"
        ]

        rc = self.execute(" ".join(cmd))
        fee = int(rc.stdout.split(' ')[0]) + self.FEE_TOLERANCE

        log.debug(f"CLI - Transaction fee is {fee}")

        return fee

    def sign(self, cmd_uuid, keys):
        log.debug(f"CLI - Signing transaction {cmd_uuid}")
        cmd = [f"transaction sign "]

        cmd.extend([f"--signing-key-file {key} " for key in keys])

        cmd.append(f"{self.network} ")
        cmd.append(f"--tx-body-file {self.temp_path}{cmd_uuid}.raw ")
        cmd.append(f"--out-file {self.temp_path}{cmd_uuid}.signed")

        return self.execute("".join(cmd))

    def get_transaction_id(self, cmd_uuid):
        cmd = f"transaction txid --tx-file {self.temp_path}{cmd_uuid}.signed"
        return self.execute(cmd).stdout

    def submit(self, cmd_uuid, transaction_id):
        log.debug(f"CLI - Submitting transaction {cmd_uuid} : {transaction_id}")
        cmd = f"transaction submit --tx-file {self.temp_path}{cmd_uuid}.signed {self.network}"
        return self.execute(cmd)

    def get_tx_out_min_lovelaces(self, transaction_manager, tx_out):
        tx_out_plus_list = transaction_manager.create_tx_out_plus_list(tx_out.address, tx_out.assets,
                                                                       self.LOVELACES_IN_ADA)
        return self.calculate_min_lovelaces(tx_out_plus_list)

    def send(self, wallet_addresses, spending, change_address=None):
        log.debug(f"CLI - Send")

        try:
            # Set a unique UUID to name the transaction files by
            cmd_uuid = str(uuid.uuid4())
            log.debug(f"CLI - UUID for transaction build {cmd_uuid}")

            tm = TransactionManager(self, wallet_addresses, spending, change_address)
            tm.send(cmd_uuid)

            self.build_raw_transaction(cmd_uuid, tm, fee=tm.fee)

            self.sign(cmd_uuid, tm.spending_wallet_keys)
            transaction_id = self.get_transaction_id(cmd_uuid)

            self.submit(cmd_uuid, transaction_id)
            log.debug(f"Transaction {transaction_id} now submitted")

            delete_files(self.temp_path, f"{cmd_uuid}.*")

            return namedtuple("Sent", "uuid, tx_id, tx_ids")(cmd_uuid, transaction_id, list(tm.spent.tx_ids))
        except Exception as e:
            log.error(f"Exception raised whilst sending transaction {e}")
