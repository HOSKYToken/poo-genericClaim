import argparse
import signal
import time
import webbrowser
from typing import Optional

from cardano import CLI
from database import POODatabase
from helpers import fix_end_of_path, check_path, load_json
from logger import log, set_log_level
from server import Server
from tasks import TaskWalletBalances, TaskSender

SETTINGS = {}
CARDANO_CLI: Optional[CLI] = None
PATH_ROOT: Optional[str] = ""
PATH_WALLETS: Optional[str] = ""
DATABASE: Optional[POODatabase] = None
PROCESSES = {}
MAIN_SLEEP = 1
RUNNING = True
ADMIN_URL: Optional[str] = ""


def load_settings():
    global SETTINGS, CARDANO_CLI, PATH_ROOT, PATH_WALLETS
    parser = argparse.ArgumentParser(description='Proof of Onboarding process')
    parser.add_argument("--settings", required=True, help="A settings file")
    args = parser.parse_args()
    SETTINGS = load_json(args.settings, f"Error, could not find the settings file {args.settings}")
    set_log_level(SETTINGS.get("log_level", "INFO"))
    CARDANO_CLI = CLI.create(SETTINGS.get("cardano_cli", None))
    PATH_ROOT = fix_end_of_path(SETTINGS.get("root_path", "./"))
    PATH_WALLETS = fix_end_of_path(check_path(SETTINGS.get("wallets", "wallets"), "wallets", PATH_ROOT))


def init_database():
    path_database = fix_end_of_path(check_path(SETTINGS.get("database", ""), "poo.db", PATH_ROOT, should_exist=False))
    global DATABASE
    DATABASE = POODatabase(path_database)
    DATABASE.base.metadata.create_all(bind=DATABASE.db_engine)


def start_process(name, process):
    global PROCESSES
    if process.start():
        PROCESSES[name] = process


def set_admin_and_claims_parameters():
    if "Admin" in PROCESSES:
        PROCESSES["Admin"].app.wallet_path = PATH_WALLETS
        PROCESSES["Admin"].app.cardano_cli = CARDANO_CLI

        if "Claims" in PROCESSES:
            PROCESSES["Admin"].app.claims_url = PROCESSES["Claims"].url

    if "Claims" in PROCESSES:
        PROCESSES["Claims"].app.security = SETTINGS.get("security", None)


def set_database_session(server):
    server.app.sessionmaker = DATABASE.sessionmaker


def set_cors_for_claims(server):
    if server.name == "Claims":
        server.app.after_request(set_cors)


def establish_cert_paths():
    certs = SETTINGS["certs"]
    for k in certs:
        certs[k] = check_path(certs[k], k, PATH_ROOT)
    return certs


def start_services():
    certs = establish_cert_paths()
    for client_name in SETTINGS["clients"]:
        if "static" in SETTINGS["clients"][client_name]:
            check_path(SETTINGS["clients"][client_name]["static"], f"{client_name} static", PATH_ROOT)
        server = Server(client_name, SETTINGS["clients"][client_name], certs, PATH_ROOT)
        set_database_session(server)
        set_cors_for_claims(server)
        start_process(client_name, server)

    set_admin_and_claims_parameters()

    start_process("Wallet_Balances", TaskWalletBalances(PATH_WALLETS, CARDANO_CLI))

    start_process("Sender", TaskSender(DATABASE.sessionmaker, SETTINGS, PATH_WALLETS))


def set_cors(response):
    response.headers["Access-Control-Allow-Origin"] = PROCESSES["Admin"].url
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def stop_services(stop_signal, frame):
    global RUNNING
    if RUNNING:
        log.info("Main - Stopping services")
        for client in PROCESSES:
            log.info(f"{client} {PROCESSES[client].service_type} - Stopping")
            PROCESSES[client].terminate()
        RUNNING = False


def start():
    log.info("Main - Starting services...")
    start_services()

    signal.signal(signal.SIGINT, stop_services)

    if "Admin" in PROCESSES:
        webbrowser.open_new_tab(PROCESSES["Admin"].url)

    while RUNNING:
        time.sleep(MAIN_SLEEP)

    log.info("Main - Everything has now stopped!")


def main():
    load_settings()
    init_database()
    start()


if __name__ == "__main__":
    main()
