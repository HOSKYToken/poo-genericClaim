import argparse
import sys
from typing import Optional

from cardano import CLI
from helpers import fix_end_of_path, file_exists, load_json, check_path
from logger import log, set_log_level

SETTINGS = {}
CARDANO_CLI: Optional[CLI] = None
PATH_ROOT: Optional[str] = None
PATH_WALLETS: Optional[str] = None
WALLET_ADDRESS: Optional[str] = None
VALID_ADDRESS_START = "addr1"


def load_settings():
    global SETTINGS, CARDANO_CLI, PATH_ROOT, PATH_WALLETS, WALLET_ADDRESS
    parser = argparse.ArgumentParser(description='Get wallet balance')
    parser.add_argument("--settings", required=True, help="A settings file")
    parser.add_argument("--wallet", required=True, help="A wallet path or address")
    args = parser.parse_args()
    SETTINGS = load_json(
        args.settings,
        f"Error, could not find the settings file {args.settings}"
    )
    set_log_level(SETTINGS.get("log_level", "INFO"))
    CARDANO_CLI = CLI.create(SETTINGS.get("cardano_cli", None))
    PATH_ROOT = fix_end_of_path(SETTINGS.get("root_path", "./"))
    PATH_WALLETS = fix_end_of_path(check_path(SETTINGS.get("wallets", "wallets"), "wallets", PATH_ROOT))
    WALLET_ADDRESS = args.wallet


def main():
    load_settings()

    if WALLET_ADDRESS.startswith(VALID_ADDRESS_START):
        log.info(f"Loading wallet {WALLET_ADDRESS}")
        wallet_to_load = WALLET_ADDRESS
    else:
        log.info(f"Loading wallet {WALLET_ADDRESS} in {PATH_WALLETS}")
        wallet_to_load = fix_end_of_path(f"{PATH_WALLETS}{WALLET_ADDRESS}")
        if not file_exists(wallet_to_load):
            log.error(f"Wallet {wallet_to_load} not found!")
            sys.exit(1)

    wallet = CARDANO_CLI.load_wallet(wallet_to_load)
    log.info(f"{wallet.address} Balance:\n\n{wallet.formatted}")


if __name__ == "__main__":
    main()
