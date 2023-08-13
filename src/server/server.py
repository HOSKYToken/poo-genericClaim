import os
import ssl
import threading
import traceback

from werkzeug.serving import make_server

from helpers import file_exists
from logger import log
from routes import app_admin, app_claims
from . import ExceptionBadCertificate, ExceptionBadStaticPath


class Server:
    APPS = {
        "Admin": app_admin,
        "Claims": app_claims
    }

    @property
    def service_type(self):
        return "server"

    @property
    def url(self):
        return f"https://{self.domain}:{self.port}"

    def check_and_set_certificates(self, certs):
        self.certificate = certs["certificate"]
        self.key = certs["key"]

        if not file_exists(self.certificate):
            raise ExceptionBadCertificate(f"Failed to find the certificate: {self.certificate}")

        if not file_exists(self.key):
            raise ExceptionBadCertificate(f"Failed to find the certificate key: {self.key}")

    def check_and_set_static_path(self, root_path, client):
        if "static" in client:
            static_path = client["static"].replace("{root_path}", root_path)
            static_path = os.path.abspath(static_path)
            if not file_exists(static_path):
                raise ExceptionBadStaticPath(f"Failed to find the static path: {static_path}")
            log.info(f"{self.name} {self.service_type} - Setting static folder to {static_path}")
            self.app.static_folder = static_path

    def __init__(self, name, client, certs, root_folder):
        super().__init__()

        self.task_name = None
        self.name = name

        self.server_socket = None
        self.server_thread = None

        self.key = None
        self.certificate = None

        log.info(f"{self.name} {self.service_type} - Creating")

        self.app = self.APPS[name]

        self.check_and_set_certificates(certs)
        self.check_and_set_static_path(root_folder, client)

        self.domain = client["domain"]
        self.port = client["port"]

    def create_server_thread(self):
        log.info(f"{self.name} {self.service_type} - Starting on port {self.url}")

        self.server_socket = None

        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=self.certificate, keyfile=self.key)
            self.server_socket = make_server(self.domain, self.port, self.app, ssl_context=ssl_context)
            self.server_socket.serve_forever()
            log.info(f"{self.name} {self.service_type} - Stopped on port {self.url}")
        except Exception as e:
            log.error(f"{self.name} {self.service_type} - server thread exception {e}")
            self.server_socket = None

    def start(self):
        try:
            # noinspection PyTypeChecker
            self.server_thread = threading.Thread(target=self.create_server_thread)
            self.server_thread.start()
            return True

        except Exception as e:
            log.error(f"{self.name} {self.service_type} - server start exception {e}")
            traceback.print_exc()

        return False

    def is_alive(self):
        return self.server_thread.is_alive()

    def terminate(self):
        self.server_socket.shutdown()
