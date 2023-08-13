import secrets
import string
import uuid

ALPHABET = string.ascii_letters + string.digits


def generateUUID():
    return str(uuid.uuid4())


def generateUUIDWithoutDashes():
    return generateUUID().replace('-', '')


def generateRndClaimCode(length=16):
    code = ''.join(secrets.choice(ALPHABET) for _ in range(length))
    return code
