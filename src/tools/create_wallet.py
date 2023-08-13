import argparse
from typing import Optional

from cardano import CLI
from helpers import fix_end_of_path, load_json, check_path, fetch_file_content
from logger import log, set_log_level

SETTINGS = {}
CARDANO_CLI: Optional[CLI] = None
PATH_ROOT: Optional[str] = None
PATH_WALLETS: Optional[str] = None
WALLET_NAME: Optional[str] = None
VALID_ADDRESS_START = "addr1"


def load_settings():
    global SETTINGS, CARDANO_CLI, PATH_ROOT, PATH_WALLETS, WALLET_NAME
    parser = argparse.ArgumentParser(description='Create wallet')
    parser.add_argument("--settings", required=True, help="A settings file")
    parser.add_argument("--wallet", required=True, help="A name for the wallet to be created")
    args = parser.parse_args()
    SETTINGS = load_json(
        args.settings,
        f"Error, could not find the settings file {args.settings}"
    )
    set_log_level(SETTINGS.get("log_level", "INFO"))
    CARDANO_CLI = CLI.create(SETTINGS.get("cardano_cli", None))
    PATH_ROOT = fix_end_of_path(SETTINGS.get("root_path", "./"))
    PATH_WALLETS = fix_end_of_path(check_path(SETTINGS.get("wallets", "wallets"), "wallets", PATH_ROOT))
    WALLET_NAME = args.wallet


def main():
    load_settings()

    log.info(f"Creating wallet {WALLET_NAME} in {PATH_WALLETS}")
    path_wallet = fix_end_of_path(f"{PATH_WALLETS}{WALLET_NAME}")
    CARDANO_CLI.create_wallet(path_wallet)
    address_payment = fetch_file_content(f"{path_wallet}payment.addr")
    log.info(f"Payment Address: {address_payment}")
    log.info("Done")


if __name__ == "__main__":
    main()
