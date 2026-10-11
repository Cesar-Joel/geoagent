"""Unit tests for geoagent.common.config."""

from __future__ import annotations

import contextlib
import dataclasses
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

from geoagent.common import config as config_module
from geoagent.common.config import (
    MASK,
    AgentConfig,
    BackendConfig,
    load_agent_config,
    load_backend_config,
    load_or_exit,
)
from geoagent.common.errors import ValidationError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

SOURCES = ("env", "file")
LOADERS = (load_agent_config, load_backend_config)
# No integer field is common to both loaders; each has its own.
_INT_FIELD = {load_agent_config: "max_workers", load_backend_config: "port"}
_OTHER_KEY = {load_agent_config: "port", load_backend_config: "max_workers"}
SECRET = "s3cr3t"


def _write(directory: str, content: str) -> str:
    path = os.path.join(directory, "config.toml")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


@contextlib.contextmanager
def _config_source(source, key, raw):
    """Yield `(path, env)` that set `key` to `raw` from the env ("env") or a TOML file ("file").

    For "env", `raw` is the variable's text; for "file", it is the TOML literal.
    """
    if source == "env":
        yield None, {f"GEOAGENT_{key.upper()}": raw}
        return
    with tempfile.TemporaryDirectory() as tmp:
        yield _write(tmp, f"{key} = {raw}\n"), {}


def _load_from(source, loader, key, raw):
    with _config_source(source, key, raw) as (path, env):
        return loader(path, env=env)


def _label(source, key):
    return f"GEOAGENT_{key.upper()}" if source == "env" else key


def _config_file_args(via_env, path):
    """`(path, env)` that point a loader at `path`: as the argument, or via GEOAGENT_CONFIG_FILE."""
    return (None, {"GEOAGENT_CONFIG_FILE": path}) if via_env else (path, {})


def _views(cfg):
    """The three views of a config, for absence checks (`assertNotIn`)."""
    return (repr(cfg), str(cfg), str(cfg.to_safe_dict()))


def _assert_shown(test, cfg, key, shown):
    """`key` appears as `shown` in `to_safe_dict()`, `repr()` and `str()` (presence check)."""
    test.assertEqual(cfg.to_safe_dict()[key], shown)
    test.assertIn(f"{key}={shown!r}", repr(cfg))
    test.assertIn(f"{key}={shown!r}", str(cfg))


# --- Validation types -------------------------------------------------------------------------
# Each type lists `invalid` rows `(env_text, toml_literal, reason)` and `valid` rows
# `(env_text, toml_literal, expected)`; `None` means "no case from that source". `reason` is the
# text the error must contain (the same from both sources), so a wrong reason fails the test.
# Numeric types carry the quoted number as its own TOML column (a quoted literal).
# `no_echo` is True unless a type says otherwise: the error must not repeat the value. Only the
# numeric types opt out ("no_echo": False), because point 5 of the spec lets `_describe` repeat a
# number or ASCII printable text (truncated); they get `test_numeric_error_echo_is_ascii_only`.


def _quoted(texts):
    return [(t, f'"{t}"') for t in texts]


def _because(reason, rows):
    """Add the expected `reason` to every `(env_text, toml_literal)` row."""
    return [(env_raw, toml_raw, reason) for env_raw, toml_raw in rows]


R_STR = "must be a string"
R_EMPTY = "must not be empty"
R_PRINTABLE = "must be printable text without control characters"
R_INT = "must be an integer"
R_NUMBER = "must be a number"
R_FINITE = "must be a finite number"
R_POSITIVE = "must be greater than 0"
R_PORT = "must be between 1 and 65535"
R_HOST = "must be an IP address or a valid host name"
R_LEVEL = "must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
R_URL = "must be a valid URL"
R_SEMICOLON = "must not contain ';' in the host or path (use %3B)"
R_HTTP_URL = "must be an http(s) URL with a host"
R_HTTP_CREDENTIALS = "must not embed credentials; use auth_token"
R_HTTP_QUERY = "must not contain a query or fragment"
R_QUEUE_URL = "must be a URL with scheme and host"
R_QUEUE_CREDENTIALS = "must not embed credentials; use queue_username and queue_password"
R_QUEUE_FRAGMENT = "must not contain a fragment"
R_UNKNOWN_KEY = "unknown configuration key"
R_UNSUPPORTED_CHARS = "(name has unsupported characters)"
R_CANNOT_READ = "cannot read "


_INT_VALID = [
    ("7", "7", 7),
    (" 3 ", '" 3 "', 3),
    (" +3 ", '"+3"', 3),
    ("3", '"3"', 3),
    (None, "3", 3),
]


def _int_invalid(not_positive):
    """Rows rejected by an integer type; `not_positive` is the reason for `-1` and `0`."""
    return _because(
        R_INT,
        [
            ("abc", '"abc"'),
            ("2.5", "2.5"),
            ("true", "true"),
            (None, '"2.5"'),
            (None, '"80.0"'),
            (None, '"true"'),
            ("80.0", "80.0"),
            ("1_0", '"1_0"'),
            ("١٢", '"١٢"'),
            ("", '""'),
            (" ", '" "'),
            (None, '["x"]'),
            (None, "{ p = 1 }"),
            (None, "1979-05-27"),
        ],
    ) + _because(not_positive, [("-1", "-1"), ("0", "0")])


_FLOAT_VALID = [
    ("5", "5", 5.0),
    ("7.5", "7.5", 7.5),
    ("5", '"5"', 5.0),
    ("7.5", '"7.5"', 7.5),
    (" 1.5e1 ", '"1.5e1"', 15.0),
    ("1.5e1", "1.5e1", 15.0),
    (".5e1", '".5e1"', 5.0),
    ("15.", '"15."', 15.0),
    (" +3 ", '"+3"', 3.0),
]
_FLOAT_INVALID = (
    _because(R_NUMBER, [("abc", '"abc"'), ("true", "true"), (None, '"true"')])
    + _because(R_NUMBER, [("1_0.5", '"1_0.5"'), ("١.5", '"١.5"'), ("", '""')])
    + _because(R_NUMBER, [(None, '["x"]'), (None, "{ p = 1 }"), (None, "1979-05-27")])
    + _because(R_POSITIVE, [("0", "0"), ("-1", "-1")])
    + _because(R_FINITE, [("nan", "nan"), ("NaN", '"NaN"'), ("inf", "inf"), ("-inf", "-inf")])
    + _because(R_FINITE, [("Infinity", '"Infinity"')])
)


def _url_invalid(scheme, credentials, no_host, fragment, semicolon_and_query):
    """Rows shared by `backend_url` (http) and `queue_url` (amqp), with the reason of each group.

    `semicolon_and_query` is the reason when a `;` comes before a query: http checks the query
    first, amqp the `;`.
    """
    credential_urls = [f"{scheme}://{c}" for c in ("u:s3cr3t@h", "s3cr3t@h", ":s3cr3t@h")]
    credential_urls += [f"{scheme}://s3cr3t:pw@h", f"{scheme}://u%3As3cr3t@h"]
    malformed_urls = [
        f"{scheme}://[s3cr3t",
        f"{scheme}://[s3cr3t]",
        f"{scheme}://u@[s3cr3t]/",
        f"{scheme}://[::1",
        f"{scheme}://h:abc",
        f"{scheme}://h:s3cr3t",
        f"{scheme}://h:0/s3cr3t",
        f"{scheme}://h:99999/s3cr3t",
        f"{scheme}://[::1]:99999/s3cr3t",
    ]
    semicolon_urls = [
        f"{scheme}://h/api;token=s3cr3t",
        f"{scheme}://h/a;token=s3cr3t/b",
        f"{scheme}://h/vhost;password=s3cr3t",
        f"{scheme}://h/api;",
        f"{scheme}://h;token=s3cr3t",
        f"{scheme}://h;password=s3cr3t/p",
        f"{scheme}://h;token=s3cr3t:80",
        f"{scheme}://;s3cr3t",
    ]
    semicolon_query_urls = [
        f"{scheme}://h/v;p=s3cr3t?heartbeat=1",
        f"{scheme}://h;token=s3cr3t?x=1",
    ]
    rows = _because(credentials, _quoted(credential_urls))
    rows += _because(no_host, _quoted(["s3cr3t.example/path", f"{scheme}:///s3cr3t"]))
    rows += _because(R_URL, _quoted(malformed_urls))
    rows += _because(fragment, _quoted([f"{scheme}://h/#s3cr3t"]))
    rows += _because(R_SEMICOLON, _quoted(semicolon_urls))
    rows += _because(semicolon_and_query, _quoted(semicolon_query_urls))
    rows += _because(R_EMPTY, [("", '""'), ("   ", '"   "')])
    rows += _because(
        R_URL,
        [
            (f"{scheme}://\udcffh/", None),
            (f"{scheme}://h\x00/", f'"{scheme}://h\\u0000/"'),
            (f"{scheme}://h\n/", f'"{scheme}://h\\n/"'),
            (f"{scheme}://\x07h/", f'"{scheme}://\\u0007h/"'),
        ],
    )
    rows += _because(
        R_STR,
        [
            (None, '["http://u:s3cr3t@h"]'),
            (None, '{ u = "s3cr3t" }'),
            (None, "1"),
            (None, "1.5"),
            (None, "true"),
            (None, "1979-05-27"),
        ],
    )
    return rows


# Non-printable text (control characters and invisible or separator ones) is rejected in the
# free-text fields (queue_username and the secrets); the secrets only come from the environment,
# so they have no TOML column.
_CONTROL_CHARS = [
    ("u\r\nX-Injected: 1", '"u\\r\\nX-Injected: 1"'),
    ("u\x00p", '"u\\u0000p"'),
    ("u\x1b[31mp", '"u\\u001b[31mp"'),
    ("u\x7fp", '"u\\u007fp"'),
    ("u\x85p", '"u\\u0085p"'),
    ("u\tp", '"u\\tp"'),
    ("u\ufeffp", '"u\\ufeffp"'),  # BOM / zero-width no-break space (Cf)
    ("u\u00a0p", '"u\\u00a0p"'),  # no-break space (Zs)
    ("u\u202ep", '"u\\u202ep"'),  # right-to-left override (Cf)
    ("u\u2028p", '"u\\u2028p"'),  # line separator (Zl)
    ("u\udcffp", None),  # lone surrogate: no TOML form
]
_CONTROL_CHARS_ENV_ONLY = [(env, None) for env, _ in _CONTROL_CHARS]

_HTTP_URL = {
    "invalid": _url_invalid("http", R_HTTP_CREDENTIALS, R_HTTP_URL, R_HTTP_QUERY, R_HTTP_QUERY)
    + _because(R_HTTP_URL, _quoted(["ftp://x", "ftp://u:s3cr3t@h"]))
    + _because(R_HTTP_QUERY, _quoted(["http://h/?token=s3cr3t", "http://h/p?x=1#s3cr3t"]))
    + _because(R_HTTP_QUERY, [("http://h/?a=1", '"http://h/?a=1"')]),
    "valid": [
        (t, f'"{t}"', t) for t in ("http://h", "http://h:8080/api", "https://h/a%3Bb", "http://h/p")
    ],
}
_QUEUE_URL = {
    "invalid": _url_invalid("amqp", R_QUEUE_CREDENTIALS, R_QUEUE_URL, R_QUEUE_FRAGMENT, R_SEMICOLON)
    + _because(R_QUEUE_URL, _quoted(["nohost"]))
    + _because(R_QUEUE_FRAGMENT, _quoted(["amqp://h/v?heartbeat=1#s3cr3t"]))
    + _because(R_QUEUE_CREDENTIALS, _quoted(["amqp://u:s3cr3t@h"])),
    "valid": [
        (t, f'"{t}"', t)
        for t in (
            "amqp://h:5672",
            "amqp://h:5672/vhost",
            "amqp://h/a%3Bb",
            "amqp://h/?heartbeat=1",
            "amqp://h/v?a=1;b=2",
        )
    ],
}
_PORT = {
    "no_echo": False,
    "invalid": _int_invalid(R_PORT) + _because(R_PORT, [("70000", "70000"), ("65536", '"65536"')]),
    "valid": _INT_VALID + [("1", "1", 1), ("65535", "65535", 65535)],
}
_POSITIVE_INT = {"no_echo": False, "invalid": _int_invalid(R_POSITIVE), "valid": _INT_VALID}
_POSITIVE_FINITE_FLOAT = {"no_echo": False, "invalid": _FLOAT_INVALID, "valid": _FLOAT_VALID}
_LOG_LEVEL = {
    "invalid": _because(R_LEVEL, _quoted(["LOUD", "\u0131nfo", "\u0131NFO"]))
    + _because(R_EMPTY, _quoted([""]))
    + _because(R_STR, [(None, "5"), (None, '["x"]'), (None, "true")]),
    "valid": [
        ("debug", '"debug"', "DEBUG"),
        (" Info ", '" Info "', "INFO"),
        ("CRITICAL", '"CRITICAL"', "CRITICAL"),
    ],
}
_BIND_HOST = {
    "invalid": _because(R_EMPTY, _quoted(["", "   "]))
    + _because(
        R_HOST,
        _quoted(
            ["h:80", "http://h", "[::1]", "-h-", "h-", "-h", "h h", "a..b", "h.", ".h"]
            + ["h_x", "h/", "a" * 64, "h:s3cr3t"]
            # IPv6 zone ids are not accepted (`%`), whatever follows
            + ["fe80::1%eth0", "fe80::1%1", "fe80::1%a b", "h%25", "%"]
            # purely numeric last label: ambiguous with an IPv4 address (inet_aton), not a valid TLD
            + [
                "010.0.0.1",
                "1.02.3.4",
                "::ffff:01.2.3.4",
                "00.0.0.0",
                "0x7f.1",
                "127.1",
                "2130706433",
                "999.1.1.1",
                "1",
                "a.1",
                "a.123",
                "1.2.3",
            ]
            # hexadecimal last label: getaddrinfo("0x7f.0x1") is 127.0.0.1
            + ["0x7f", "0X7F", "0x7f.0x1", "1.0x1", "0x", "a.0xAb", "0x0"]
            # longer than 253 characters
            + [".".join(["a" * 63] * 3 + ["a" * 62]), "a." * 126 + "ab"]
        ),
    )
    + _because(
        R_HOST,
        [
            ("fe80::1%a\nb", '"fe80::1%a\\nb"'),
            ("fe80::1%a\x00b", '"fe80::1%a\\u0000b"'),
            ("fe80::1%a\x1b[31m", '"fe80::1%a\\u001b[31m"'),
            ("h\tb", '"h\\tb"'),
            ("h\u00a0b", '"h\\u00a0b"'),
            ("h\u2028b", '"h\\u2028b"'),
            ("::1\nINFO fake", '"::1\\nINFO fake"'),
            ("1.2.3.4\x00", '"1.2.3.4\\u0000"'),
            ("h\x00", '"h\\u0000"'),
            ("h\nINFO fake", '"h\\nINFO fake"'),
            ("h\x07", '"h\\u0007"'),
            ("\udcffh", None),
        ],
    )
    + _because(R_STR, [(None, "1"), (None, "true"), (None, "1979-05-27"), (None, '["x"]')]),
    "valid": [
        (t, f'"{t}"', t)
        for t in (
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "2001:db8::1",
            "localhost",
            "a-b.example.com",
            "A1",
            "a" * 63,
            "1a",
            "a.b1",
            "1.example.com",
            "0xg",
            "a.0x1g",
            "0x1.example.com",
            "::ffff:1.2.3.4",
            ".".join(["a" * 63] * 3 + ["a" * 61]),  # 253 characters
        )
    ]
    + [("  h  ", '"  h  "', "h")],
}
_PATH = {
    "invalid": _because(R_EMPTY, _quoted(["", "   "]))
    + _because(
        R_PRINTABLE,
        [
            ("a\x00b", '"a\\u0000b"'),
            ("a\nb", '"a\\nb"'),
            ("a\x07", '"a\\u0007"'),
            ("a\x1b[31m", '"a\\u001b[31m"'),
            ("a\u2028b", '"a\\u2028b"'),  # line separator
            ("a\u202eb", '"a\\u202eb"'),  # right-to-left override
            ("a\u00a0b", '"a\\u00a0b"'),  # no-break space
            ("a\udcffb", None),  # lone surrogate: open() would fail with UnicodeEncodeError
        ],
    )
    + _because(R_STR, [(None, "1"), (None, "1979-05-27"), (None, "true"), (None, '["x"]')]),
    "valid": [("data/x.db", '"data/x.db"', "data/x.db"), (" x.db ", '" x.db "', "x.db")],
}
_ANY_STR = {
    "invalid": _because(R_STR, [(None, "1"), (None, "1.5"), (None, "true"), (None, "1979-05-27")])
    + _because(R_STR, [(None, '["s3cr3t"]'), (None, '{ a = "s3cr3t" }')])
    + _because(R_PRINTABLE, _CONTROL_CHARS),
    "valid": [("user", '"user"', "user"), ("", '""', ""), (" u ", '" u "', " u ")]
    + [("é ü", '"é ü"', "é ü")],
}
# Secrets are env-only: no invalid values (the file case is `test_secret_in_file_is_rejected`).
_SECRET_TYPE = {
    "invalid": _because(R_PRINTABLE, _CONTROL_CHARS_ENV_ONLY),
    "valid": [("pw", None, "pw"), ("", None, "")],
}

# Written by hand: what each field must validate is fixed here, not read from `_*_SPECS`.
_COMMON_TYPES = {
    "queue_url": _QUEUE_URL,
    "queue_username": _ANY_STR,
    "queue_password": _SECRET_TYPE,
    "request_timeout": _POSITIVE_FINITE_FLOAT,
    "log_level": _LOG_LEVEL,
}
FIELD_TYPES = {
    AgentConfig: {
        "backend_url": _HTTP_URL,
        "auth_token": _SECRET_TYPE,
        "max_workers": _POSITIVE_INT,
        "heartbeat_interval": _POSITIVE_FINITE_FLOAT,
        "store_path": _PATH,
        **_COMMON_TYPES,
    },
    BackendConfig: {
        "host": _BIND_HOST,
        "port": _PORT,
        "db_path": _PATH,
        "api_token": _SECRET_TYPE,
        **_COMMON_TYPES,
    },
}
_CONFIG_CLASS = {load_agent_config: AgentConfig, load_backend_config: BackendConfig}


def _field_cases():
    """Yield `(loader, key, validation_type)` for every field of both configs."""
    for loader in LOADERS:
        cls = _CONFIG_CLASS[loader]
        for key, vtype in FIELD_TYPES[cls].items():
            yield loader, key, vtype


def _raw_for(source, env_raw, toml_raw):
    return env_raw if source == "env" else toml_raw


class TestPrecedence(unittest.TestCase):
    AGENT_DEFAULTS = {
        "backend_url": "http://127.0.0.1:8080",
        "auth_token": "",
        "max_workers": 2,
        "heartbeat_interval": 30.0,
        "store_path": "agent_store.db",
        "queue_url": "amqp://127.0.0.1:5672",
        "queue_username": "",
        "queue_password": "",
        "request_timeout": 10.0,
        "log_level": "INFO",
    }
    BACKEND_DEFAULTS = {
        "host": "127.0.0.1",
        "port": 8080,
        "db_path": "backend_store.db",
        "api_token": "",
        "queue_url": "amqp://127.0.0.1:5672",
        "queue_username": "",
        "queue_password": "",
        "request_timeout": 10.0,
        "log_level": "INFO",
    }

    def test_defaults_when_no_file_and_no_env(self):
        for loader, expected in (
            (load_agent_config, self.AGENT_DEFAULTS),
            (load_backend_config, self.BACKEND_DEFAULTS),
        ):
            with self.subTest(loader=loader.__name__):
                values = loader(env={}).to_safe_dict()
                self.assertEqual(values, expected)
                # `30 == 30.0`: compare the exact types too.
                self.assertEqual(
                    {k: type(v) for k, v in values.items()},
                    {k: type(v) for k, v in expected.items()},
                )

    def test_invalid_default_is_rejected_naming_the_key(self):
        spec = config_module._Spec
        for loader, specs, key, bad, parser in (
            (
                load_agent_config,
                config_module._AGENT_SPECS,
                "max_workers",
                0,
                config_module._positive_int,
            ),
            (
                load_backend_config,
                config_module._BACKEND_SPECS,
                "port",
                70000,
                config_module._port,
            ),
            (
                load_backend_config,
                config_module._BACKEND_SPECS,
                "host",
                "h:80",
                config_module._bind_host,
            ),
        ):
            with self.subTest(loader=loader.__name__, key=key):
                with mock.patch.dict(specs, {key: spec(bad, parser)}):
                    with self.assertRaises(ValidationError) as ctx:
                        loader(env={})
                self.assertEqual(ctx.exception.field, key)
                self.assertIn("(default)", str(ctx.exception))

    def test_file_overrides_defaults(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                cfg = _load_from("file", loader, "request_timeout", "7.5")
                self.assertEqual(cfg.request_timeout, 7.5)

    def test_env_overrides_file(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = _write(tmp, "request_timeout = 5\n")
                    cfg = loader(path, env={"GEOAGENT_REQUEST_TIMEOUT": "9"})
                self.assertEqual(cfg.request_timeout, 9.0)

    def test_env_overrides_default(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                cfg = loader(env={"GEOAGENT_REQUEST_TIMEOUT": "7"})
                self.assertEqual(cfg.request_timeout, 7.0)

    def test_file_path_from_env(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = _write(tmp, 'log_level = "debug"\nrequest_timeout = 7.5\n')
                    cfg = loader(env={"GEOAGENT_CONFIG_FILE": path})
                self.assertEqual(cfg.log_level, "DEBUG")
                self.assertEqual(cfg.request_timeout, 7.5)
                self.assertIs(type(cfg.request_timeout), float)

    def test_unprefixed_env_is_ignored(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                cfg = loader(env={"REQUEST_TIMEOUT": "99"})
                self.assertEqual(cfg.request_timeout, 10.0)


class TestValidation(unittest.TestCase):
    """What is accepted and what is rejected, by validation type, from both sources."""

    def test_every_field_is_classified(self):
        for cls, types in FIELD_TYPES.items():
            names = {f.name for f in dataclasses.fields(cls)}
            with self.subTest(config=cls.__name__):
                self.assertEqual(sorted(names - set(types)), [], "unclassified field")
                self.assertEqual(sorted(set(types) - names), [], "classified, but not a field")

    def test_invalid_values_are_rejected_naming_the_key(self):
        for loader, key, vtype in _field_cases():
            for env_raw, toml_raw, reason in vtype["invalid"]:
                for source in SOURCES:
                    raw = _raw_for(source, env_raw, toml_raw)
                    if raw is None:
                        continue
                    with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                        with self.assertRaises(ValidationError) as ctx:
                            _load_from(source, loader, key, raw)
                        self.assertIn(_label(source, key), str(ctx.exception))
                        self.assertIn(reason, str(ctx.exception))
                        self.assertNotIn("(default)", str(ctx.exception))

    def test_valid_values_are_accepted_with_exact_type(self):
        for loader, key, vtype in _field_cases():
            for env_raw, toml_raw, expected in vtype["valid"]:
                for source in SOURCES:
                    raw = _raw_for(source, env_raw, toml_raw)
                    if raw is None:
                        continue
                    with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                        value = getattr(_load_from(source, loader, key, raw), key)
                        self.assertEqual(value, expected)
                        # `bool` is an `int`, and `5 == 5.0`: compare the exact type.
                        self.assertIs(type(value), type(expected))

    def test_unknown_file_key(self):
        for loader in LOADERS:
            for key in ("bogus", _OTHER_KEY[loader]):
                with self.subTest(loader=loader.__name__, key=key):
                    with self.assertRaises(ValidationError) as ctx:
                        _load_from("file", loader, key, "1")
                    self.assertEqual(ctx.exception.field, key)
                    self.assertIn(R_UNKNOWN_KEY, str(ctx.exception))
                    self.assertNotIn(R_UNSUPPORTED_CHARS, str(ctx.exception))

    def test_other_loaders_env_key_is_ignored(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                env = {f"GEOAGENT_{_OTHER_KEY[loader].upper()}": "not a number"}
                loader(env=env)

    def test_missing_file(self):
        for loader in LOADERS:
            for via_env in (False, True):
                with self.subTest(loader=loader.__name__, via_env=via_env):
                    path, env = _config_file_args(via_env, "/nonexistent/x.toml")
                    with self.assertRaises(ValidationError) as ctx:
                        loader(path, env=env)
                    self.assertEqual(ctx.exception.field, "config_file")
                    self.assertIn("file not found", str(ctx.exception))

    def test_invalid_toml(self):
        for loader in LOADERS:
            for via_env in (False, True):
                with self.subTest(loader=loader.__name__, via_env=via_env):
                    with tempfile.TemporaryDirectory() as tmp:
                        path, env = _config_file_args(
                            via_env, _write(tmp, "request_timeout = = 1\n")
                        )
                        with self.assertRaises(ValidationError) as ctx:
                            loader(path, env=env)
                    self.assertEqual(ctx.exception.field, "config_file")
                    self.assertIn("invalid TOML in", str(ctx.exception))

    def test_unreadable_files_raise_validation_error(self):
        for loader in LOADERS:
            with tempfile.TemporaryDirectory() as tmp:
                bad_utf8 = os.path.join(tmp, "bad.toml")
                with open(bad_utf8, "wb") as handle:
                    handle.write(b'log_level = "s3cr3t\xff\xfe"\n')
                deep = _write(tmp, "x = " + "[" * 5000 + "]" * 5000 + "\n")
                cases = {
                    "directory": (tmp, R_CANNOT_READ),
                    "non_utf8": (bad_utf8, "not valid UTF-8"),
                    "nul_in_path": ("/tmp/a\x00b", "invalid config file path"),
                    "deep_nesting": (deep, "nested too deeply"),
                }
                for name, (file_path, reason) in cases.items():
                    for via_env in (False, True):
                        with self.subTest(loader=loader.__name__, case=name, via_env=via_env):
                            path, env = _config_file_args(via_env, file_path)
                            with self.assertRaises(ValidationError) as ctx:
                                loader(path, env=env)
                            self.assertEqual(ctx.exception.field, "config_file")
                            self.assertIn(reason, str(ctx.exception))
                            self.assertNotIn(SECRET, str(ctx.exception))


def _decoded(source, raw):
    """The string a case sets: the env text, or the TOML literal decoded."""
    if source == "env":
        return raw
    return tomllib.loads(f"v = {raw}")["v"]


class TestErrorMessages(unittest.TestCase):
    """What the message says: names the key, never echoes a value that may be a secret."""

    def test_error_never_echoes_the_value(self):
        for loader, key, vtype in _field_cases():
            if not vtype.get("no_echo", True):
                continue
            for env_raw, toml_raw, _ in vtype["invalid"]:
                for source in SOURCES:
                    raw = _raw_for(source, env_raw, toml_raw)
                    if raw is None:
                        continue
                    value = _decoded(source, raw)
                    with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                        with self.assertRaises(ValidationError) as ctx:
                            _load_from(source, loader, key, raw)
                        texts = (str(ctx.exception), repr(ctx.exception))
                        for text in texts:
                            self.assertNotIn(SECRET, text)
                            if isinstance(value, str) and value.strip():
                                self.assertNotIn(value, text)  # as is
                                self.assertNotIn(repr(value)[1:-1], text)  # escaped

    def test_non_string_error_reports_only_the_type(self):
        fields = {
            load_agent_config: ("backend_url", "queue_username", "log_level"),
            load_backend_config: ("host", "queue_username", "log_level"),
        }
        for loader, keys in fields.items():
            for key in keys:
                with self.subTest(loader=loader.__name__, key=key):
                    with self.assertRaises(ValidationError) as ctx:
                        _load_from("file", loader, key, '["s3cr3t"]')
                    self.assertIn("got list", str(ctx.exception))
                    self.assertNotIn(SECRET, str(ctx.exception))

    def test_non_scalar_in_numeric_field_reports_only_the_type(self):
        for loader in LOADERS:
            for key in (_INT_FIELD[loader], "request_timeout"):
                for raw, type_name in (('{ p = "s3cr3t" }', "dict"), ('["s3cr3t"]', "list")):
                    with self.subTest(loader=loader.__name__, key=key, raw=raw):
                        with self.assertRaises(ValidationError) as ctx:
                            _load_from("file", loader, key, raw)
                        self.assertIn(f"got {type_name}", str(ctx.exception))
                        self.assertNotIn(SECRET, str(ctx.exception))

    def test_long_numeric_value_is_truncated_in_error(self):
        huge = "9" * 4300 + "x"
        for loader in LOADERS:
            for key in (_INT_FIELD[loader], "request_timeout"):
                for source, raw in (("env", huge), ("file", f'"{huge}"')):
                    with self.subTest(loader=loader.__name__, key=key, source=source):
                        with self.assertRaises(ValidationError) as ctx:
                            _load_from(source, loader, key, raw)
                        self.assertLess(len(str(ctx.exception)), 200)
                        self.assertIn("…", str(ctx.exception))

    def test_huge_digit_string_and_native_int_are_rejected_briefly(self):
        raw = "9" * 5000
        for loader in LOADERS:
            for key in (_INT_FIELD[loader], "request_timeout"):
                for source in SOURCES:
                    with self.subTest(loader=loader.__name__, key=key, source=source):
                        with self.assertRaises(ValidationError) as ctx:
                            _load_from(source, loader, key, raw)
                        self.assertLess(len(str(ctx.exception)), 200)

    def test_numeric_error_echo_is_ascii_only(self):
        # (env text, TOML literal, expected): numeric errors repeat only ASCII printable text.
        cases = (
            ("abc", '"abc"', "got 'abc'"),
            ("1\nINFO s3cr3t", '"1\\nINFO s3cr3t"', "got str"),
            ("1\x1b[31m", '"1\\u001b[31m"', "got str"),
            ("1\x00", '"1\\u0000"', "got str"),
            ("é1", '"é1"', "got str"),
            ("١٢", '"١٢"', "got str"),
            ("1" + chr(0x202E), '"1\\u202e"', "got str"),
        )
        for loader in LOADERS:
            for key in (_INT_FIELD[loader], "request_timeout"):
                for env_raw, toml_raw, expected in cases:
                    for source in SOURCES:
                        raw = _raw_for(source, env_raw, toml_raw)
                        with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                            with self.assertRaises(ValidationError) as ctx:
                                _load_from(source, loader, key, raw)
                            text = str(ctx.exception)
                            self.assertIn(expected, text)
                            self.assertTrue(text.isprintable(), repr(text))
                            if expected == "got str":
                                self.assertNotIn(env_raw, text)
                                self.assertNotIn(repr(env_raw)[1:-1], text)
                                self.assertNotIn(SECRET, text)


# Names that could forge log lines or escape a terminal if repeated as they are.
_BAD_NAMES = ("a\nINFO fake", "a\x1b[31mred", "a\rb", "a" + chr(0x2028) + "INFO fake", "a\udcffb")


@contextlib.contextmanager
def _file_named(name, content=None, directory=False, nul=False):
    """Yield the path of a file (or directory, or nothing) called `name` in a temp directory.

    With `nul`, nothing is created and a NUL byte is appended to the path (no file can have one).
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name)
        if nul:
            path += "\x00x"
        elif directory:
            os.mkdir(path)
        elif content is not None:
            with open(path, "wb") as handle:
                handle.write(content)
        yield path


# `_read_file` branches that repeat the path: how to build a path that fails that way.
_PATH_BRANCHES = {
    "not_found": {},
    "cannot_read": {"directory": True},
    "invalid_toml": {"content": b"request_timeout = = 1\n"},
    "not_utf8": {"content": b'log_level = "\xff\xfe"\n'},
    "too_deep": {"content": b"x = " + b"[" * 5000 + b"]" * 5000 + b"\n"},
    "nul_in_path": {"nul": True},  # the message must not repeat the path with its raw NUL
}


def _forgeable(text):
    """True if `text` has anything but printable characters (before the final newline)."""
    return not text.rstrip("\n").isprintable()


class TestUntrustedNamesInErrors(unittest.TestCase):
    """The file path and unknown TOML keys come from the user: no raw control characters."""

    def _assert_safe(self, exc, bad):
        message = str(exc)
        self.assertFalse(_forgeable(message), repr(message))
        self.assertNotIn("INFO fake", message)
        for text in (message, repr(exc)):
            self.assertNotIn(bad, text)
            self.assertNotIn(repr(bad)[1:-1], text)

    def test_path_with_control_characters_is_not_repeated(self):
        for loader in LOADERS:
            for branch, kwargs in _PATH_BRANCHES.items():
                for bad in _BAD_NAMES:
                    for via_env in (False, True):
                        with self.subTest(
                            loader=loader.__name__, branch=branch, bad=bad, via_env=via_env
                        ):
                            with _file_named(bad, **kwargs) as path:
                                arg, env = _config_file_args(via_env, path)
                                with self.assertRaises(ValidationError) as ctx:
                                    loader(arg, env=env)
                            self.assertEqual(ctx.exception.field, "config_file")
                            self._assert_safe(ctx.exception, bad)
                            self.assertNotIn(os.path.dirname(path), str(ctx.exception))

    def test_printable_path_is_still_shown(self):
        for loader in LOADERS:
            for branch, kwargs in _PATH_BRANCHES.items():
                if kwargs.get("nul"):
                    continue  # the message never shows that path
                with self.subTest(loader=loader.__name__, branch=branch):
                    with _file_named("plain name.toml", **kwargs) as path:
                        with self.assertRaises(ValidationError) as ctx:
                            loader(path, env={})
                    self.assertIn(path, str(ctx.exception))

    def test_path_with_control_characters_via_load_or_exit(self):
        for loader in LOADERS:
            for branch, kwargs in _PATH_BRANCHES.items():
                for bad in _BAD_NAMES:
                    for via_env in (False, True):
                        with self.subTest(
                            loader=loader.__name__, branch=branch, bad=bad, via_env=via_env
                        ):
                            err = io.StringIO()
                            with _file_named(bad, **kwargs) as path:
                                arg, env = _config_file_args(via_env, path)
                                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                                    load_or_exit(loader, arg, env=env)
                            text = err.getvalue()
                            self.assertTrue(text.startswith("invalid configuration: config_file:"))
                            self.assertEqual(text.count("\n"), 1)
                            self.assertFalse(_forgeable(text), repr(text))
                            self.assertNotIn("INFO fake", text)
                            self.assertNotIn(bad, text)
                            self.assertNotIn(repr(bad)[1:-1], text)

    def test_unknown_key_is_repeated_only_if_plain(self):
        bad_keys = (
            ("x\\nINFO fake", "x\nINFO fake"),
            ("x\\u001b[31m", "x\x1b[31m"),
            ("x\\r", "x\r"),
            ("x y", "x y"),
            ("x\\u2028INFO fake", "x" + chr(0x2028) + "INFO fake"),
            ("é", "é"),
            ("a/b", "a/b"),
        )
        for loader in LOADERS:
            for literal, key in bad_keys:
                with self.subTest(loader=loader.__name__, key=key):
                    with tempfile.TemporaryDirectory() as tmp:
                        path = _write(tmp, f'"{literal}" = 1\n')
                        with self.assertRaises(ValidationError) as ctx:
                            loader(path, env={})
                    self.assertEqual(ctx.exception.field, "config_file")
                    self.assertIn(R_UNKNOWN_KEY, str(ctx.exception))
                    self.assertIn(R_UNSUPPORTED_CHARS, str(ctx.exception))
                    self._assert_safe(ctx.exception, key)
                    err = io.StringIO()
                    with tempfile.TemporaryDirectory() as tmp:
                        path = _write(tmp, f'"{literal}" = 1\n')
                        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                            load_or_exit(loader, path, env={})
                    self.assertEqual(err.getvalue().count("\n"), 1)
                    self.assertFalse(_forgeable(err.getvalue()), repr(err.getvalue()))
                    self.assertNotIn("INFO fake", err.getvalue())

    def test_long_path_is_truncated(self):
        name = "n" * 200 + ".toml"
        for loader in LOADERS:
            for branch, kwargs in _PATH_BRANCHES.items():
                if kwargs.get("nul"):
                    continue
                for via_env in (False, True):
                    with self.subTest(loader=loader.__name__, branch=branch, via_env=via_env):
                        with _file_named(name, **kwargs) as path:
                            arg, env = _config_file_args(via_env, path)
                            with self.assertRaises(ValidationError) as ctx:
                                loader(arg, env=env)
                            self.assertEqual(ctx.exception.field, "config_file")
                            message = str(ctx.exception)
                            self.assertLess(len(message), 200)
                            self.assertIn("…" + path[-config_module._MAX_ECHO :], message)
                            self.assertIn(name[-config_module._MAX_ECHO :], message)
                            self.assertNotIn(path[: config_module._MAX_ECHO], message)
                            self.assertNotIn(name, message)
                            err = io.StringIO()
                            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                                load_or_exit(loader, arg, env=env)
                            self.assertLess(len(err.getvalue()), 220)

    def test_long_unknown_key_is_truncated(self):
        key = "k" * 100_000
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with self.assertRaises(ValidationError) as ctx:
                    _load_from("file", loader, key, "1")
                message = str(ctx.exception)
                self.assertLess(len(message), 200)
                self.assertIn("k" * config_module._MAX_ECHO + "…", message)
                self.assertNotIn("k" * (config_module._MAX_ECHO + 1), message)
                self.assertLess(len(ctx.exception.field), 100)

    def test_long_toml_error_text_is_truncated(self):
        name = "a" * 300
        for loader in LOADERS:
            for via_env in (False, True):
                with self.subTest(loader=loader.__name__, via_env=via_env):
                    with tempfile.TemporaryDirectory() as tmp:
                        file_path = _write(tmp, f"[{name}]\n[{name}]\n")
                        path, env = _config_file_args(via_env, file_path)
                        with self.assertRaises(ValidationError) as ctx:
                            loader(path, env=env)
                    message = str(ctx.exception)
                    self.assertIn("invalid TOML in", message)
                    self.assertNotIn(
                        "a" * (config_module._MAX_ECHO + 1), message.split(": ", 2)[-1]
                    )
                    self.assertLess(len(message), 250)
                    self.assertTrue(message.isprintable())

    def test_long_toml_syntax_error_keeps_position(self):
        # Long message (a 300-character key) plus a position suffix: the line must survive.
        name = "a" * 300
        cases = {
            "duplicate": f"[{name}]\n[{name}]\n",
            "nested duplicate": f"[x.{name}]\n[x.{name}]\n\n[y]\n",
        }
        for loader in LOADERS:
            for label, content in cases.items():
                with self.subTest(loader=loader.__name__, case=label):
                    with tempfile.TemporaryDirectory() as tmp:
                        with self.assertRaises(ValidationError) as ctx:
                            loader(_write(tmp, content), env={})
                    message = str(ctx.exception)
                    self.assertRegex(message, r" \(at line [0-9]+, column [0-9]+\)$")
                    self.assertIn("… (at ", message)
                    self.assertNotIn("a" * (config_module._MAX_ECHO + 1), message)
                    self.assertTrue(message.isprintable())

    def test_short_toml_syntax_error_shows_line(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ValidationError) as ctx:
                        loader(_write(tmp, "a = 1\nb = \x01\n"), env={})
                self.assertRegex(str(ctx.exception), r"\(at line 2, column [0-9]+\)$")

    def test_toml_position_suffix_is_strict(self):
        clip = config_module._clip_toml_error
        suffix = " (at line 2, column 3)"
        self.assertEqual(clip("x" * 100 + suffix), "x" * 40 + "…" + suffix)
        self.assertEqual(clip("short" + suffix), "short" + suffix)
        self.assertEqual(
            clip("x" * 100 + " (at end of document)"), "x" * 40 + "… (at end of document)"
        )
        # Anything else in the parentheses (non-digits, control characters) is not kept verbatim.
        for tail in (
            " (at line 2, column 3\n)",
            " (at line \u0663, column 3)",
            " (at line x, column 3)",
            " (at line 2, column 3) secret",
            " (at line 2, column 3)\n",
            " (at line 2, col 3)",
        ):
            with self.subTest(tail=tail):
                self.assertEqual(clip("x" * 100 + tail), "x" * 40 + "…")

    def test_plain_unknown_key_is_named(self):
        for loader in LOADERS:
            for key in ("bogus", "a-b_c", "s3cr3t"):
                with self.subTest(loader=loader.__name__, key=key):
                    with self.assertRaises(ValidationError) as ctx:
                        _load_from("file", loader, key, "1")
                    self.assertEqual(ctx.exception.field, key)
                    self.assertIn(key, str(ctx.exception))
                    self.assertIn(R_UNKNOWN_KEY, str(ctx.exception))
                    self.assertNotIn(R_UNSUPPORTED_CHARS, str(ctx.exception))


class TestConfigFilePath(unittest.TestCase):
    """The file path: `os.PathLike` is accepted, other types and empty paths are errors."""

    def _expect_error(self, loader, path, env, text):
        with self.assertRaises(ValidationError) as ctx:
            loader(path, env=env)
        self.assertEqual(ctx.exception.field, "config_file")
        self.assertIn(text, str(ctx.exception))
        return ctx.exception

    def test_pathlib_path_is_accepted(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = pathlib.Path(_write(tmp, "request_timeout = 7.5\n"))
                    cfg = loader(path, env={})
                    self.assertEqual(cfg.request_timeout, 7.5)
                    self.assertEqual(load_or_exit(loader, path, env={}).request_timeout, 7.5)

    def test_missing_pathlib_path_names_config_file(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                self._expect_error(loader, pathlib.Path("/nonexistent/x.toml"), {}, "not found")

    def test_non_text_paths_are_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = _write(tmp, "request_timeout = 7.5\n")
            bad_paths = (os.fsencode(existing), b"s3cr3t.toml", 5, ["s3cr3t"], object())
            for loader in LOADERS:
                for bad in bad_paths:
                    with self.subTest(loader=loader.__name__, bad=type(bad).__name__):
                        error = self._expect_error(loader, bad, {}, "must be a string or a path")
                        self.assertNotIn(SECRET, str(error))
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
                            load_or_exit(loader, bad, env={})
                        self.assertEqual(ctx.exception.code, 2)
                        self.assertIn("config_file", err.getvalue())
                        self.assertNotIn("Traceback", err.getvalue())

    def test_empty_path_argument_is_an_error(self):
        for loader in LOADERS:
            for empty in ("", "   "):
                with self.subTest(loader=loader.__name__, path=repr(empty)):
                    self._expect_error(loader, empty, {}, "must not be empty")

    def test_empty_env_variable_is_an_error_but_unset_is_not(self):
        for loader in LOADERS:
            for value in ("", "  "):
                with self.subTest(loader=loader.__name__, value=value):
                    self._expect_error(
                        loader, None, {"GEOAGENT_CONFIG_FILE": value}, "must not be empty"
                    )
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
                        load_or_exit(loader, env={"GEOAGENT_CONFIG_FILE": value})
                    self.assertEqual(ctx.exception.code, 2)
                    self.assertIn("config_file", err.getvalue())
            with self.subTest(loader=loader.__name__, case="unset"):
                loader(env={})  # environment + defaults, no error
                loader(env={"GEOAGENT_REQUEST_TIMEOUT": "7"})

    def test_explicit_path_wins_over_empty_env_variable(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = _write(tmp, "request_timeout = 7.5\n")
                    cfg = loader(path, env={"GEOAGENT_CONFIG_FILE": ""})
                self.assertEqual(cfg.request_timeout, 7.5)


class TestBindHostPythonCompat(unittest.TestCase):
    def test_leading_zero_octets_rejected_even_if_ipaddress_accepts_them(self):
        # Python 3.9.0-3.9.4 `ipaddress` accepts `010.0.0.1` (CVE-2021-29921).
        lenient = mock.Mock(side_effect=lambda text: text)
        for text in ("010.0.0.1", "1.2.3.04", "00.0.0.0", "::ffff:01.2.3.4"):
            with self.subTest(text=text):
                with mock.patch.object(config_module.ipaddress, "ip_address", lenient):
                    with self.assertRaises(ValidationError) as ctx:
                        _load_from("env", load_backend_config, "host", text)
                self.assertEqual(ctx.exception.field, "GEOAGENT_HOST")
        with mock.patch.object(config_module.ipaddress, "ip_address", lenient):
            for text in ("0.0.0.0", "10.0.0.1", "127.0.0.1"):
                with self.subTest(text=text):
                    cfg = _load_from("env", load_backend_config, "host", text)
                    self.assertEqual(cfg.host, text)


class TestLoadOrExit(unittest.TestCase):
    def run_failing(self, loader, source, key, raw):
        """Run `load_or_exit` as startup does; return `(exit code, stdout, stderr)`."""
        out, err = io.StringIO(), io.StringIO()
        with _config_source(source, key, raw) as (path, env):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    load_or_exit(loader, path, env=env)
        return ctx.exception.code, out.getvalue(), err.getvalue()

    def test_invalid_config_exits_2_naming_key(self):
        for loader in LOADERS:
            for source in SOURCES:
                with self.subTest(loader=loader.__name__, source=source):
                    code, _, err = self.run_failing(loader, source, "request_timeout", "0")
                    self.assertEqual(code, 2)
                    self.assertIn(_label(source, "request_timeout"), err)

    def test_error_goes_to_stderr_not_stdout(self):
        for loader in LOADERS:
            with self.subTest(loader=loader.__name__):
                _, out, err = self.run_failing(loader, "env", "request_timeout", "0")
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("invalid configuration:"))
                self.assertTrue(err.endswith("\n"))

    def test_malformed_url_exits_2_naming_key_without_secret(self):
        cases = (
            (load_agent_config, "backend_url", "http://[s3cr3t", '"http://[s3cr3t]"'),
            (load_agent_config, "queue_url", "amqp://h:s3cr3t", '"amqp://h:99999/s3cr3t"'),
            (load_backend_config, "queue_url", "amqp://h:s3cr3t", '"amqp://h:99999/s3cr3t"'),
            (load_agent_config, "backend_url", "http://h/a;t=s3cr3t", '"http://h/a;t=s3cr3t"'),
            (load_backend_config, "host", "h:s3cr3t", '"h:s3cr3t"'),
        )
        for loader, key, env_raw, toml_raw in cases:
            for source in SOURCES:
                with self.subTest(loader=loader.__name__, key=key, source=source):
                    raw = _raw_for(source, env_raw, toml_raw)
                    code, _, err = self.run_failing(loader, source, key, raw)
                    self.assertEqual(code, 2)
                    self.assertIn(_label(source, key), err)
                    self.assertNotIn(SECRET, err)
                    self.assertNotIn("Traceback", err)

    def test_non_utf8_file_via_load_or_exit_exits_2(self):
        for loader in LOADERS:
            for via_env in (False, True):
                with self.subTest(loader=loader.__name__, via_env=via_env):
                    with tempfile.TemporaryDirectory() as tmp:
                        file_path = os.path.join(tmp, "bad.toml")
                        with open(file_path, "wb") as handle:
                            handle.write(b'log_level = "s3cr3t\xff"\n')
                        path, env = _config_file_args(via_env, file_path)
                        stderr = io.StringIO()
                        with contextlib.redirect_stderr(stderr):
                            with self.assertRaises(SystemExit) as ctx:
                                load_or_exit(loader, path, env=env)
                    self.assertEqual(ctx.exception.code, 2)
                    self.assertIn("config_file", stderr.getvalue())
                    self.assertNotIn(SECRET, stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())

    def test_valid_config_is_returned(self):
        for loader, key, expected in (
            (load_agent_config, "max_workers", 2),
            (load_backend_config, "port", 8080),
        ):
            with self.subTest(loader=loader.__name__):
                cfg = load_or_exit(loader, env={})
                self.assertEqual(getattr(cfg, key), expected)


class TestSecretMasking(unittest.TestCase):
    ENV = {
        "GEOAGENT_AUTH_TOKEN": "tok-secret-123",
        "GEOAGENT_QUEUE_PASSWORD": "pw-secret-456",
        "GEOAGENT_API_TOKEN": "api-secret-789",
    }
    # Written by hand on purpose: deriving them from the specs would follow a removed flag.
    CASES = (
        (load_agent_config, {"auth_token": "tok-secret-123", "queue_password": "pw-secret-456"}),
        (load_backend_config, {"api_token": "api-secret-789", "queue_password": "pw-secret-456"}),
    )

    def test_secrets_hidden_in_every_view(self):
        for loader, secrets in self.CASES:
            with self.subTest(loader=loader.__name__):
                cfg = loader(env=self.ENV)
                for text in _views(cfg):
                    for value in secrets.values():
                        self.assertNotIn(value, text)
                for key in secrets:
                    _assert_shown(self, cfg, key, MASK)

    def test_secret_value_still_accessible(self):
        for loader, secrets in self.CASES:
            cfg = loader(env=self.ENV)
            for key, value in secrets.items():
                with self.subTest(loader=loader.__name__, key=key):
                    self.assertEqual(getattr(cfg, key), value)

    def test_unset_secret_not_masked(self):
        for loader, secrets in self.CASES:
            cfg = loader(env={})
            for key in secrets:
                with self.subTest(loader=loader.__name__, key=key):
                    _assert_shown(self, cfg, key, "")

    def test_non_secret_fields_visible(self):
        for loader, secrets in self.CASES:
            cfg = loader(env=self.ENV)
            for f in dataclasses.fields(cfg):
                if f.name in secrets:
                    continue
                with self.subTest(loader=loader.__name__, key=f.name):
                    _assert_shown(self, cfg, f.name, getattr(cfg, f.name))

    def test_secrets_from_env_masked_with_non_secret_file(self):
        for loader, secrets in self.CASES:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = _write(tmp, 'log_level = "debug"\n')
                    cfg = loader(path, env=self.ENV)
                self.assertEqual(cfg.log_level, "DEBUG")
                for text in _views(cfg):
                    for value in secrets.values():
                        self.assertNotIn(value, text)

    def test_secret_in_file_is_rejected(self):
        for loader, secrets in self.CASES:
            for key in secrets:
                for via_env in (False, True):
                    with self.subTest(loader=loader.__name__, key=key, via_env=via_env):
                        with tempfile.TemporaryDirectory() as tmp:
                            file_path = _write(tmp, f'{key} = "hunter2"\n')
                            arg, env = _config_file_args(via_env, file_path)
                            with self.assertRaises(ValidationError) as ctx:
                                loader(arg, env=env)
                        self.assertEqual(ctx.exception.field, key)
                        text = str(ctx.exception)
                        self.assertIn("secrets must not be stored in the config file", text)
                        self.assertIn(f"set GEOAGENT_{key.upper()}", text)
                        self.assertNotIn("hunter2", str(ctx.exception))


class TestQueueUrlQueryMasking(unittest.TestCase):
    URL = "amqp://h:5672/vhost?heartbeat=60&password=s3cr3t"
    MASKED = f"amqp://h:5672/vhost?heartbeat={MASK}&password={MASK}"

    def test_query_values_masked_keys_visible(self):
        for loader in LOADERS:
            for source in SOURCES:
                raw = self.URL if source == "env" else f'"{self.URL}"'
                with self.subTest(loader=loader.__name__, source=source):
                    cfg = _load_from(source, loader, "queue_url", raw)
                    _assert_shown(self, cfg, "queue_url", self.MASKED)
                    for text in _views(cfg):
                        self.assertNotIn(SECRET, text)
                    self.assertEqual(cfg.queue_url, self.URL)

    def test_valueless_query_item_is_masked(self):
        rows = (
            ("amqp://h/?s3cr3t", f"amqp://h/?{MASK}"),
            ("amqp://h/?a=1&s3cr3t", f"amqp://h/?a={MASK}&{MASK}"),
        )
        for loader in LOADERS:
            for source in SOURCES:
                for url, shown in rows:
                    with self.subTest(loader=loader.__name__, source=source, url=url):
                        raw = url if source == "env" else f'"{url}"'
                        cfg = _load_from(source, loader, "queue_url", raw)
                        _assert_shown(self, cfg, "queue_url", shown)
                        for text in _views(cfg):
                            self.assertNotIn(SECRET, text)
                        self.assertEqual(cfg.queue_url, url)

    def test_url_without_query_unchanged(self):
        for loader in LOADERS:
            for source in SOURCES:
                for url in ("amqp://h:5672", "amqp://h:5672/vhost", "amqp://h/a%3Bb"):
                    with self.subTest(loader=loader.__name__, source=source, url=url):
                        raw = url if source == "env" else f'"{url}"'
                        cfg = _load_from(source, loader, "queue_url", raw)
                        _assert_shown(self, cfg, "queue_url", url)

    def test_backend_url_has_no_masking(self):
        for source in SOURCES:
            with self.subTest(source=source):
                raw = "http://h/path" if source == "env" else '"http://h/path"'
                cfg = _load_from(source, load_agent_config, "backend_url", raw)
                _assert_shown(self, cfg, "backend_url", "http://h/path")


if __name__ == "__main__":
    unittest.main()
