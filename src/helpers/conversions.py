import json
from collections import Counter


class ExceptionCantPrettify(Exception):
    pass


def is_hex_string(s):
    try:
        int(s, 16)
        return len(s) % 2 == 0 and decode_hex(s)
    except ValueError:
        return False


def decode_hex(value):
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
    if is_hex_string(asset_name):
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


def merge_dicts(dicts):
    d = {}
    for n in dicts:
        d = dict(Counter(d) + Counter(n))
    return d
