# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import os
import json
import ctypes as ct
from .._constants import VSCODE_CREDENTIALS_SECTION


def _c_str(string):
    return ct.c_char_p(string.encode("utf-8"))


class _SECRET_SCHEMA_ATTRIBUTE(ct.Structure):
    _fields_ = [
        ("name", ct.c_char_p),
        ("type", ct.c_uint),
    ]


class _SECRET_SCHEMA(ct.Structure):
    _fields_ = [
        ("name", ct.c_char_p),
        ("flags", ct.c_uint),
        ("attributes", _SECRET_SCHEMA_ATTRIBUTE * 2),
    ]
_PSECRET_SCHEMA = ct.POINTER(_SECRET_SCHEMA)


try:
    _libsecret = ct.cdll.LoadLibrary("libsecret-1.so.0")
    _libsecret.secret_password_lookup_sync.argtypes = [
        ct.c_void_p,
        ct.c_void_p,
        ct.c_void_p,
        ct.c_char_p,
        ct.c_char_p,
        ct.c_char_p,
        ct.c_char_p,
        ct.c_void_p,
    ]
    _libsecret.secret_password_lookup_sync.restype = ct.c_char_p
except OSError:
    _libsecret = None


def _get_user_settings_path():
    app_data_folder = os.environ["HOME"]
    return os.path.join(app_data_folder, ".config", "Code", "User", "settings.json")


def _get_user_settings():
    path = _get_user_settings_path()
    try:
        with open(path) as file:
            data = json.load(file)
            environment_name = data.get("azure.cloud", "Azure")
            return environment_name
    except IOError:
        return "Azure"


def _get_refresh_token(service_name, account_name):
    if not _libsecret:
        return None

    err = ct.c_int()
    attribute1 = _SECRET_SCHEMA_ATTRIBUTE()
    setattr(attribute1, "name", _c_str("service"))
    setattr(attribute1, "type", 0)
    attribute2 = _SECRET_SCHEMA_ATTRIBUTE()
    setattr(attribute2, "name", _c_str("account"))
    setattr(attribute2, "type", 0)
    attributes = [attribute1, attribute2]
    pattributes = (_SECRET_SCHEMA_ATTRIBUTE * 2)(*attributes)
    schema = _SECRET_SCHEMA()
    pschema = _SECRET_SCHEMA(schema)
    ct.memset(pschema, 0, ct.sizeof(schema))
    setattr(schema, "name", _c_str("org.freedesktop.Secret.Generic"))
    setattr(schema, "flags", 2)
    setattr(schema, "attributes", pattributes)
    p_str = _libsecret.secret_password_lookup_sync(
        pschema,
        None,
        ct.byref(err),
        _c_str("service"),
        _c_str(service_name),
        _c_str("account"),
        _c_str(account_name),
        None,
    )
    if err.value == 0:
        return p_str.decode("utf-8")

    return None


def get_credentials():
    try:
        environment_name = _get_user_settings()
        credentials = _get_refresh_token(VSCODE_CREDENTIALS_SECTION, environment_name)
        return credentials
    except Exception:  # pylint: disable=broad-except
        return None
