import secrets
import string
import uuid

ALPHABET = string.ascii_letters + string.digits


def generate_uuid():
    return str(uuid.uuid4())


def generate_uuid_without_dashes():
    return generate_uuid().replace('-', '')


def generate_rnd_claim_code(length=16):
    code = ''.join(secrets.choice(ALPHABET) for _ in range(length))
    return code
