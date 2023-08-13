import json
from collections import Counter


class ExceptionCantPrettify(Exception):
    pass


CIP68_CODES = [
    "00064",  # 100 - NFT
    "000DE",  # 222 - NFT
    "0014D",  # 333 - FT
    "001BC"   # 444 - RFT
]


def is_hex_string(value):
    try:
        int(value, 16)
        return len(value) % 2 == 0 and decode_hex(value)
    except ValueError as e:
        return False
    except TypeError as e:
        return False


def is_cip68_string(value: str):
    return value[:5].upper() in CIP68_CODES


def decode_hex(value):
    if is_cip68_string(value):
        value = value[6:]
    return bytes.fromhex(value).decode('utf-8')


def asset_name_decode_hex(asset_fqn):
    if '.' not in asset_fqn:
        return asset_fqn
    parts = asset_fqn.split('.')

    return f"{parts[0]}.{decode_hex(parts[1])}"


def encode_hex(value):
    return value.encode('utf-8').hex()


def asset_name_encode_hex(asset_fqn):
    if '.' not in asset_fqn:
        return asset_fqn
    parts = asset_fqn.split('.')
    name = encode_hex('.'.join(parts[1:]))
    return f"{parts[0]}.{name}"


def convert_asset_to_hrf_and_hex_form(asset_name):
    if is_hex_string(asset_name) or is_cip68_string(asset_name):
        print(f"{asset_name} is hex!")
        return decode_hex(asset_name), asset_name
    else:
        return asset_name, encode_hex(asset_name)


def prettify(data):
    if data is None:
        return {}
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, sort_keys=False, indent=2, separators=(',', ':'))

    # noinspection PyUnresolvedReferences
    raise ExceptionCantPrettify(f'Can not prettify data because of its type is {data.__class__}')


def to_ascii_named_assets(balance):
    ascii_named_assets = {}
    for hex_name_asset in balance["assets"]:
        ascii_name_asset = asset_name_decode_hex(hex_name_asset)
        ascii_named_assets[ascii_name_asset] = balance["assets"][hex_name_asset]
    balance["assets"] = ascii_named_assets
    return balance


def merge_dicts(dicts):
    d = {}
    for n in dicts:
        d = dict(Counter(d) + Counter(n))
    return d
