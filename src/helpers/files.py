import glob
import json
import os
import sys

from atomicwrites import atomic_write

from logger import log


def file_exists(path):
    return True if os.path.exists(path) else False


def check_path_exists_or_stop(path, error_message=None):
    if file_exists(path):
        return True
    error_message = error_message if error_message else f"{path} does not exist when it should"
    log.error(error_message)
    sys.exit(1)


def check_path_does_not_exist_or_stop(path, error_message=None):
    if not file_exists(path):
        return True
    error_message = error_message if error_message else f"{path} exists when it shouldn't"
    log.error(error_message)
    sys.exit(1)


def create_folder_path(path):
    os.makedirs(path)


def fetch_file_content(path, error_message=None):
    check_path_exists_or_stop(path, error_message)
    with open(path, "r") as f:
        return f.read()


def load_json(path, error_message=None):
    error_message = error_message if error_message else f"Trying to load {path} failed"
    return json.loads(fetch_file_content(path, error_message))


def save_json(path, data, pretty=False, sort_keys=False):
    with atomic_write(path, overwrite=True) as w:
        if not pretty:
            w.write(json.dumps(data))
        else:
            w.write(json.dumps(data, sort_keys=sort_keys, indent=2, separators=(',', ':')))


def fix_end_of_path(path):
    path = path.strip()
    return path if path.endswith('/') else f"{path}/"


def delete_files(path, file_pattern):
    for filename in glob.glob(f"{path}{file_pattern}"):
        os.remove(filename)


def check_path(path, name, path_root="./", should_exist=True):
    path = path.replace("{root_path}", path_root)
    path = os.path.abspath(path)
    if should_exist:
        check_path_exists_or_stop(path, f"The path to {name} was not found {path}")
    return path
