"""Unit tests for geoagent.common.config."""

from __future__ import annotations

import contextlib
import dataclasses
import io
import os
import tempfile
import unittest

from geoagent.common.config import (
    MASK,
    load_agent_config,
    load_backend_config,
    load_or_exit,
)
from geoagent.common.errors import ValidationError


def _write(directory: str, content: str) -> str:
    path = os.path.join(directory, "config.toml")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _load_from(source, loader, key, raw):
    """Load config with `key` set to `raw` from the env ("env") or a TOML file ("file").

    For "env", `raw` is the variable's text; for "file", it is the TOML literal.
    """
    if source == "env":
        return loader(env={f"GEOAGENT_{key.upper()}": raw})
    with tempfile.TemporaryDirectory() as tmp:
        return loader(_write(tmp, f"{key} = {raw}\n"), env={})


def _label(source, key):
    return f"GEOAGENT_{key.upper()}" if source == "env" else key


SOURCES = ("env", "file")


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

    def test_agent_defaults_when_no_file_and_no_env(self):
        cfg = load_agent_config(env={})
        self.assertEqual(cfg.to_safe_dict(), self.AGENT_DEFAULTS)

    def test_backend_defaults_when_no_file_and_no_env(self):
        cfg = load_backend_config(env={})
        self.assertEqual(cfg.to_safe_dict(), self.BACKEND_DEFAULTS)

    def test_file_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "max_workers = 5\n")
            cfg = load_agent_config(path, env={})
        self.assertEqual(cfg.max_workers, 5)

    def test_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "port = 9000\n")
            cfg = load_backend_config(path, env={"GEOAGENT_PORT": "9100"})
        self.assertEqual(cfg.port, 9100)

    def test_env_overrides_default(self):
        cfg = load_agent_config(env={"GEOAGENT_MAX_WORKERS": "7"})
        self.assertEqual(cfg.max_workers, 7)

    def test_file_path_from_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, 'log_level = "debug"\n')
            cfg = load_agent_config(env={"GEOAGENT_CONFIG_FILE": path})
        self.assertEqual(cfg.log_level, "DEBUG")

    def test_unprefixed_env_is_ignored(self):
        cfg = load_agent_config(env={"MAX_WORKERS": "9"})
        self.assertEqual(cfg.max_workers, 2)


class TestValidation(unittest.TestCase):
    # (loader, key, invalid env text, invalid TOML literal); checked from BOTH sources.
    INVALID = (
        (load_backend_config, "port", "abc", '"abc"'),
        (load_backend_config, "port", "70000", "70000"),
        (load_backend_config, "port", "0", "0"),
        (load_agent_config, "max_workers", "0", "0"),
        (load_agent_config, "max_workers", "-1", "-1"),
        (load_agent_config, "heartbeat_interval", "0", "0"),
        (load_agent_config, "heartbeat_interval", "nan", "nan"),
        (load_agent_config, "heartbeat_interval", "inf", "inf"),
        (load_agent_config, "heartbeat_interval", "-inf", "-inf"),
        (load_agent_config, "request_timeout", "0", "0"),
        (load_agent_config, "request_timeout", "nan", "nan"),
        (load_agent_config, "request_timeout", "inf", "inf"),
        (load_backend_config, "request_timeout", "0", "0"),
        (load_backend_config, "request_timeout", "-inf", "-inf"),
        (load_backend_config, "request_timeout", "NaN", "nan"),
        (load_agent_config, "backend_url", "", '""'),
        (load_agent_config, "backend_url", "ftp://x", '"ftp://x"'),
        (load_agent_config, "backend_url", "http://u:p@h", '"http://u:p@h"'),
        (load_agent_config, "backend_url", "http://h/?a=1", '"http://h/?a=1"'),
        (load_agent_config, "backend_url", "http://h/#a", '"http://h/#a"'),
        (load_agent_config, "backend_url", "http://[::1", '"http://[::1"'),
        (load_agent_config, "backend_url", "http://[abc]", '"http://[abc]"'),
        (load_agent_config, "backend_url", "http://h:abc", '"http://h:abc"'),
        (load_agent_config, "backend_url", "http://h:0", '"http://h:0"'),
        (load_agent_config, "backend_url", "http://h:99999", '"http://h:99999"'),
        (load_agent_config, "queue_url", "amqp://[::1", '"amqp://[::1"'),
        (load_agent_config, "queue_url", "amqp://h:abc", '"amqp://h:abc"'),
        (load_backend_config, "queue_url", "amqp://h:99999", '"amqp://h:99999"'),
        (load_agent_config, "queue_url", "", '""'),
        (load_agent_config, "queue_url", "nohost", '"nohost"'),
        (load_agent_config, "queue_url", "amqp://u:p@h", '"amqp://u:p@h"'),
        (load_agent_config, "queue_url", "amqp://h/#a", '"amqp://h/#a"'),
        (load_backend_config, "queue_url", "amqp://h/#a", '"amqp://h/#a"'),
        (load_backend_config, "queue_url", "", '""'),
        (load_backend_config, "queue_url", "amqp://u:p@h", '"amqp://u:p@h"'),
        (load_agent_config, "log_level", "LOUD", '"LOUD"'),
        (load_backend_config, "log_level", "LOUD", '"LOUD"'),
        (load_backend_config, "host", "", '""'),
        (load_backend_config, "host", "   ", '"   "'),
        (load_agent_config, "store_path", "", '""'),
        (load_backend_config, "db_path", "", '""'),
    )

    def assert_invalid(self, source, loader, key, raw):
        with self.assertRaises(ValidationError) as ctx:
            _load_from(source, loader, key, raw)
        self.assertIn(_label(source, key), str(ctx.exception))

    def test_invalid_values_rejected_from_both_sources(self):
        for loader, key, env_raw, toml_raw in self.INVALID:
            for source in SOURCES:
                raw = env_raw if source == "env" else toml_raw
                with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                    self.assert_invalid(source, loader, key, raw)

    def test_invalid_toml_native_types_rejected(self):
        cases = (
            (load_agent_config, "max_workers", "true"),
            (load_agent_config, "max_workers", "2.5"),
            (load_backend_config, "port", "80.0"),
            (load_backend_config, "host", "1"),
            (load_agent_config, "store_path", "1979-05-27"),
            (load_agent_config, "log_level", "5"),
        )
        for loader, key, raw in cases:
            with self.subTest(key=key, raw=raw):
                self.assert_invalid("file", loader, key, raw)

    def test_invalid_env_text_rejected(self):
        cases = (
            (load_agent_config, "max_workers", "2.5"),
            (load_agent_config, "max_workers", "true"),
            (load_backend_config, "port", "80.0"),
            (load_backend_config, "host", "   "),
        )
        for loader, key, raw in cases:
            with self.subTest(key=key, raw=raw):
                self.assert_invalid("env", loader, key, raw)

    def test_valid_native_and_text_values_accepted(self):
        cfg = _load_from("file", load_agent_config, "heartbeat_interval", "5")
        self.assertEqual(cfg.heartbeat_interval, 5.0)
        self.assertIsInstance(cfg.heartbeat_interval, float)
        self.assertEqual(_load_from("env", load_agent_config, "max_workers", " 3 ").max_workers, 3)

    def test_quoted_number_in_file_is_accepted(self):
        cfg = _load_from("file", load_agent_config, "max_workers", '"3"')
        self.assertEqual(cfg.max_workers, 3)

    def test_unknown_file_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "bogus = 1\n")
            with self.assertRaises(ValidationError) as ctx:
                load_agent_config(path, env={})
        self.assertIn("bogus", str(ctx.exception))

    def test_missing_file(self):
        with self.assertRaises(ValidationError) as ctx:
            load_agent_config("/nonexistent/x.toml", env={})
        self.assertEqual(ctx.exception.field, "config_file")

    def test_invalid_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "max_workers = = 1\n")
            with self.assertRaises(ValidationError) as ctx:
                load_agent_config(path, env={})
        self.assertEqual(ctx.exception.field, "config_file")

    def test_unreadable_files_raise_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_utf8 = os.path.join(tmp, "bad.toml")
            with open(bad_utf8, "wb") as handle:
                handle.write(b'log_level = "s3cr3t\xff\xfe"\n')
            deep = _write(tmp, "x = " + "[" * 5000 + "]" * 5000 + "\n")
            paths = {"non_utf8": bad_utf8, "nul_in_path": "/tmp/a\x00b", "deep_nesting": deep}
            for name, path in paths.items():
                for via_env in (False, True):
                    with self.subTest(case=name, via_env=via_env):
                        with self.assertRaises(ValidationError) as ctx:
                            if via_env:
                                load_agent_config(env={"GEOAGENT_CONFIG_FILE": path})
                            else:
                                load_agent_config(path, env={})
                        self.assertEqual(ctx.exception.field, "config_file")
                        self.assertNotIn("s3cr3t", str(ctx.exception))

    def test_non_utf8_file_via_load_or_exit_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.toml")
            with open(path, "wb") as handle:
                handle.write(b'log_level = "s3cr3t\xff"\n')
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
                load_or_exit(load_agent_config, path, env={})
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("config_file", stderr.getvalue())
        self.assertNotIn("s3cr3t", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class TestUrlSecretsNeverEchoed(unittest.TestCase):
    SECRET = "s3cr3t"
    CREDENTIALS = (
        "u:s3cr3t@h",
        "s3cr3t@h",
        ":s3cr3t@h",
        "s3cr3t:pw@h",
        "u%3As3cr3t@h",
    )

    def cases(self):
        """Yield (loader, key, source, raw) covering every rejection branch of both URLs."""
        for loader, key, scheme, bad_scheme in (
            (load_agent_config, "backend_url", "http", "ftp"),
            (load_backend_config, "queue_url", "amqp", None),
            (load_agent_config, "queue_url", "amqp", None),
        ):
            texts = [f"{scheme}://{c}" for c in self.CREDENTIALS]
            texts += ["s3cr3t.example/path", f"{scheme}:///s3cr3t"]
            texts += [
                f"{scheme}://[s3cr3t",
                f"{scheme}://[s3cr3t]",
                f"{scheme}://u@[s3cr3t]/",
                f"{scheme}://h:s3cr3t",
                f"{scheme}://h:99999/s3cr3t",
                f"{scheme}://h:0/s3cr3t",
                f"{scheme}://[::1]:99999/s3cr3t",
            ]
            if bad_scheme:
                texts.append(f"{bad_scheme}://u:s3cr3t@h")
            if key == "backend_url":
                texts += ["http://h/?token=s3cr3t", "http://h/#s3cr3t", "http://h/p?x=1#s3cr3t"]
            else:
                texts += ["amqp://h/#s3cr3t", "amqp://h/v?heartbeat=1#s3cr3t"]
            for text in texts:
                yield loader, key, "env", text
                yield loader, key, "file", f'"{text}"'
            for raw in ('["http://u:s3cr3t@h"]', '{ u = "s3cr3t" }'):
                yield loader, key, "file", raw

    def test_url_secret_never_appears_in_error(self):
        for loader, key, source, raw in self.cases():
            with self.subTest(loader=loader.__name__, key=key, source=source, raw=raw):
                with self.assertRaises(ValidationError) as ctx:
                    _load_from(source, loader, key, raw)
                self.assertIn(_label(source, key), str(ctx.exception))
                self.assertNotIn(self.SECRET, str(ctx.exception))
                self.assertNotIn(self.SECRET, repr(ctx.exception))

    def test_long_numeric_value_is_truncated_in_error(self):
        huge = "9" * 4300 + "x"
        for source, raw in (("env", huge), ("file", f'"{huge}"')):
            with self.subTest(source=source):
                with self.assertRaises(ValidationError) as ctx:
                    _load_from(source, load_agent_config, "max_workers", raw)
                self.assertLess(len(str(ctx.exception)), 200)
                self.assertIn("\u2026", str(ctx.exception))

    def test_huge_digit_string_and_native_int_are_rejected_briefly(self):
        for source, raw in (("env", "9" * 5000), ("file", "9" * 5000)):
            with self.subTest(source=source):
                with self.assertRaises(ValidationError) as ctx:
                    _load_from(source, load_agent_config, "heartbeat_interval", raw)
                self.assertLess(len(str(ctx.exception)), 200)
        with self.assertRaises(ValidationError) as ctx:
            _load_from("file", load_backend_config, "port", "9" * 5000)
        self.assertLess(len(str(ctx.exception)), 200)

    def test_numeric_text_accepts_only_ascii_digits_without_underscores(self):
        bad = (
            ("max_workers", "\u0661\u0662"),
            ("max_workers", "1_0"),
            ("heartbeat_interval", "1_0.5"),
            ("heartbeat_interval", "\u0661.5"),
        )
        for key, raw in bad:
            with self.subTest(key=key, raw=raw):
                with self.assertRaises(ValidationError):
                    _load_from("env", load_agent_config, key, raw)
                with self.assertRaises(ValidationError):
                    _load_from("file", load_agent_config, key, f'"{raw}"')

    def test_numeric_text_still_accepts_spaces_sign_and_exponent(self):
        for source, raw in (("env", " +3 "), ("file", '" 3 "')):
            cfg = _load_from(source, load_agent_config, "max_workers", raw)
            self.assertEqual(cfg.max_workers, 3)
        for source, raw in (("env", " 1.5e1 "), ("file", '"15."'), ("env", ".5e1")):
            cfg = _load_from(source, load_agent_config, "heartbeat_interval", raw)
            self.assertGreater(cfg.heartbeat_interval, 0)
        self.assertEqual(
            _load_from("file", load_agent_config, "heartbeat_interval", "1.5e1").heartbeat_interval,
            15.0,
        )

    def test_control_characters_in_host_are_rejected_without_echo(self):
        hosts = ("http://\udcffh/", "http://h\x00/", "http://h\n/", "http://\x07h/")
        for key in ("backend_url", "queue_url"):
            for raw in hosts:
                with self.subTest(key=key, raw=raw):
                    with self.assertRaises(ValidationError) as ctx:
                        _load_from("env", load_agent_config, key, raw)
                    self.assertNotIn("udcff", str(ctx.exception))
                    self.assertIn("valid URL", str(ctx.exception))

    def test_non_string_error_reports_only_the_type(self):
        with self.assertRaises(ValidationError) as ctx:
            _load_from("file", load_agent_config, "backend_url", '["x"]')
        self.assertIn("got list", str(ctx.exception))

    def test_non_scalar_in_numeric_field_reports_only_the_type(self):
        for key, raw in (("port", '{ p = "s3cr3t" }'), ("port", '["s3cr3t"]')):
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError) as ctx:
                    _load_from("file", load_backend_config, key, raw)
                self.assertNotIn(self.SECRET, str(ctx.exception))
        with self.assertRaises(ValidationError) as ctx:
            _load_from("file", load_agent_config, "heartbeat_interval", '["s3cr3t"]')
        self.assertNotIn(self.SECRET, str(ctx.exception))


class TestLoadOrExit(unittest.TestCase):
    def test_invalid_config_exits_nonzero_naming_key(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
            load_or_exit(load_agent_config, env={"GEOAGENT_MAX_WORKERS": "0"})
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("GEOAGENT_MAX_WORKERS", stderr.getvalue())

    def test_error_goes_to_stderr_not_stdout(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                load_or_exit(load_agent_config, env={"GEOAGENT_MAX_WORKERS": "0"})
        self.assertEqual(out.getvalue(), "")
        self.assertTrue(err.getvalue().startswith("invalid configuration:"))
        self.assertTrue(err.getvalue().endswith("\n"))

    def test_malformed_url_exits_2_naming_key_without_secret(self):
        for source, key, raw in (
            ("env", "backend_url", "http://[s3cr3t"),
            ("env", "queue_url", "amqp://h:s3cr3t"),
            ("file", "backend_url", '"http://[s3cr3t]"'),
            ("file", "queue_url", '"amqp://h:99999/s3cr3t"'),
        ):
            with self.subTest(source=source, key=key):
                loader = load_agent_config
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
                    load_or_exit(_load_from, source, loader, key, raw)
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn(_label(source, key), stderr.getvalue())
                self.assertNotIn("s3cr3t", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_valid_config_is_returned(self):
        cfg = load_or_exit(load_backend_config, env={})
        self.assertEqual(cfg.port, 8080)


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

    def views(self, cfg):
        return (repr(cfg), str(cfg), str(cfg.to_safe_dict()))

    def test_secrets_hidden_in_every_view(self):
        for loader, secrets in self.CASES:
            with self.subTest(loader=loader.__name__):
                cfg = loader(env=self.ENV)
                for text in self.views(cfg):
                    for value in secrets.values():
                        self.assertNotIn(value, text)
                safe = cfg.to_safe_dict()
                for key in secrets:
                    self.assertEqual(safe[key], MASK)

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
                    self.assertEqual(cfg.to_safe_dict()[key], "")
                    self.assertIn(f"{key}=''", repr(cfg))
                    self.assertIn(f"{key}=''", str(cfg))

    def test_non_secret_fields_visible(self):
        for loader, secrets in self.CASES:
            cfg = loader(env=self.ENV)
            for f in dataclasses.fields(cfg):
                if f.name in secrets:
                    continue
                value = getattr(cfg, f.name)
                with self.subTest(loader=loader.__name__, key=f.name):
                    self.assertEqual(cfg.to_safe_dict()[f.name], value)
                    self.assertIn(f"{f.name}={value!r}", repr(cfg))
                    self.assertIn(f"{f.name}={value!r}", str(cfg))

    def test_secrets_from_env_masked_with_non_secret_file(self):
        for loader, secrets in self.CASES:
            with self.subTest(loader=loader.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    path = _write(tmp, 'log_level = "debug"\n')
                    cfg = loader(path, env=self.ENV)
                self.assertEqual(cfg.log_level, "DEBUG")
                for text in self.views(cfg):
                    for value in secrets.values():
                        self.assertNotIn(value, text)

    def test_secret_in_file_is_rejected(self):
        for loader, secrets in self.CASES:
            for key in secrets:
                for via_env in (False, True):
                    with self.subTest(loader=loader.__name__, key=key, via_env=via_env):
                        with tempfile.TemporaryDirectory() as tmp:
                            path = _write(tmp, f'{key} = "hunter2"\n')
                            with self.assertRaises(ValidationError) as ctx:
                                if via_env:
                                    loader(env={"GEOAGENT_CONFIG_FILE": path})
                                else:
                                    loader(path, env={})
                        self.assertEqual(ctx.exception.field, key)
                        self.assertNotIn("hunter2", str(ctx.exception))


class TestQueueUrlQueryMasking(unittest.TestCase):
    URL = "amqp://h:5672/vhost?heartbeat=60&password=s3cr3t"
    MASKED = f"amqp://h:5672/vhost?heartbeat={MASK}&password={MASK}"

    def test_query_values_masked_keys_visible(self):
        for loader in (load_agent_config, load_backend_config):
            for source in SOURCES:
                raw = self.URL if source == "env" else f'"{self.URL}"'
                with self.subTest(loader=loader.__name__, source=source):
                    cfg = _load_from(source, loader, "queue_url", raw)
                    self.assertEqual(cfg.to_safe_dict()["queue_url"], self.MASKED)
                    for text in (repr(cfg), str(cfg), str(cfg.to_safe_dict())):
                        self.assertNotIn("s3cr3t", text)
                        self.assertIn(f"heartbeat={MASK}", text)
                        self.assertIn(f"password={MASK}", text)
                    self.assertEqual(cfg.queue_url, self.URL)

    def test_valueless_query_item_is_masked(self):
        cfg = load_agent_config(env={"GEOAGENT_QUEUE_URL": "amqp://h/?s3cr3t"})
        self.assertNotIn("s3cr3t", repr(cfg))
        self.assertEqual(cfg.queue_url, "amqp://h/?s3cr3t")

    def test_url_without_query_unchanged(self):
        for url in ("amqp://h:5672", "amqp://h:5672/vhost"):
            with self.subTest(url=url):
                cfg = load_agent_config(env={"GEOAGENT_QUEUE_URL": url})
                self.assertEqual(cfg.to_safe_dict()["queue_url"], url)
                self.assertIn(f"queue_url={url!r}", repr(cfg))

    def test_backend_url_has_no_masking(self):
        cfg = load_agent_config(env={"GEOAGENT_BACKEND_URL": "http://h/path"})
        self.assertEqual(cfg.to_safe_dict()["backend_url"], "http://h/path")


if __name__ == "__main__":
    unittest.main()
