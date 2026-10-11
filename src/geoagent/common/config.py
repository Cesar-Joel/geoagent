"""Layered configuration (defaults < TOML file < GEOAGENT_ env vars) for agent and backend."""

from __future__ import annotations

import ipaddress
import math
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any, Callable
from urllib.parse import ParseResult, urlparse, urlsplit, urlunsplit

from geoagent.common.errors import ValidationError

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:  # pragma: no cover
        tomllib = None

ENV_PREFIX = "GEOAGENT_"
CONFIG_FILE_ENV = "GEOAGENT_CONFIG_FILE"
MASK = "***"
EXIT_CODE_INVALID_CONFIG = 2

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


_MAX_ECHO = 40
_MAX_HOST_LEN = 253  # RFC 1035 / RFC 1123: longest DNS name, without the trailing dot
_KEY_RE = re.compile(r"[A-Za-z0-9_.-]+")
_NON_PRINTABLE_PATH = "<path with non-printable characters>"
_DNS_LABEL_RE = re.compile(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
_HEX_LABEL_RE = re.compile(r"0[xX][0-9A-Fa-f]*")  # inet_aton reads `0x7f` as a number
_INT_RE = re.compile(r"[+-]?[0-9]+")
_FLOAT_RE = re.compile(
    r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?|[+-]?(inf|infinity|nan)", re.IGNORECASE
)


def _clip(text: str) -> str:
    """Truncate text that is repeated in a message (same limit as `_describe`)."""
    return text if len(text) <= _MAX_ECHO else text[:_MAX_ECHO] + "\u2026"


# Position suffix of a `TOMLDecodeError`; strictly digits, so keeping it verbatim echoes nothing.
_TOML_POSITION_RE = re.compile(
    r" \(at (?:line [0-9]+, column [0-9]+|end of document)\)\Z", re.ASCII
)


def _clip_tail(text: str) -> str:
    """Truncate keeping the end (a path is identified by its file name)."""
    return text if len(text) <= _MAX_ECHO else "\u2026" + text[-_MAX_ECHO:]


def _clip_toml_error(detail: str) -> str:
    """Truncate the text of a TOML error but keep its `(at line L, column C)` suffix."""
    match = _TOML_POSITION_RE.search(detail)
    if match is None:
        return _clip(detail)
    return _clip(detail[: match.start()]) + match.group()


def _describe(value: Any) -> str:
    """Repeat numbers and ASCII printable text (truncated); only name the type of anything else."""
    if not isinstance(value, (str, int, float)):
        return type(value).__name__
    if isinstance(value, str) and not (value.isascii() and value.isprintable()):
        return type(value).__name__
    try:
        text = repr(value)
    except ValueError:  # int too large to render
        return type(value).__name__
    return _clip(text)


def _parse_int(key: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValidationError("must be an integer", field=key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _INT_RE.fullmatch(text):
            try:
                return int(text)
            except ValueError:  # more digits than the interpreter allows
                pass
    raise ValidationError(f"must be an integer (got {_describe(value)})", field=key)


def _parse_float(key: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError("must be a number", field=key)
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except OverflowError:
            pass
    elif isinstance(value, str):
        text = value.strip()
        if _FLOAT_RE.fullmatch(text):
            try:
                return float(text)
            except ValueError:
                pass
    raise ValidationError(f"must be a number (got {_describe(value)})", field=key)


def _finite_float(key: str, value: Any) -> float:
    number = _parse_float(key, value)
    if not math.isfinite(number):
        raise ValidationError("must be a finite number", field=key)
    return number


def _parse_str(key: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"must be a string (got {type(value).__name__})", field=key)
    return value


def _plain_str(key: str, value: Any) -> str:
    """Printable text (no control, invisible or separator characters); never repeats the value."""
    text = _parse_str(key, value)
    if not text.isprintable():
        raise ValidationError("must be printable text without control characters", field=key)
    return text


def _positive_int(key: str, value: Any) -> int:
    number = _parse_int(key, value)
    if number <= 0:
        raise ValidationError(f"must be greater than 0 (got {_describe(number)})", field=key)
    return number


def _positive_float(key: str, value: Any) -> float:
    number = _finite_float(key, value)
    if number <= 0:
        raise ValidationError(f"must be greater than 0 (got {_describe(number)})", field=key)
    return number


def _port(key: str, value: Any) -> int:
    number = _parse_int(key, value)
    if not 1 <= number <= 65535:
        raise ValidationError(f"must be between 1 and 65535 (got {_describe(number)})", field=key)
    return number


def _non_empty(key: str, value: Any) -> str:
    text = _parse_str(key, value).strip()
    if not text:
        raise ValidationError("must not be empty", field=key)
    return text


def _fs_path(key: str, value: Any) -> str:
    """Non-empty printable path (no control characters, surrogates, ...); never repeats it."""
    text = _non_empty(key, value)
    if not text.isprintable():
        raise ValidationError("must be printable text without control characters", field=key)
    return text


def _bind_host(key: str, value: Any) -> str:
    """An IP address (no brackets, no IPv6 zone) or a DNS name; never repeats the value."""
    text = _non_empty(key, value)
    error = ValidationError("must be an IP address or a valid host name", field=key)
    if not text.isprintable() or " " in text or "%" in text:
        raise error
    try:
        ipaddress.ip_address(text)
    except ValueError:
        pass
    else:
        # Python 3.9.0-3.9.4 accept leading zeros (CVE-2021-29921): `010.0.0.1` would bind
        # to 8.0.0.1. Reject them by hand so the result does not depend on the interpreter.
        octets = text.rsplit(":", 1)[-1].split(".") if "." in text else []
        if any(len(octet) > 1 and octet.startswith("0") for octet in octets):
            raise error
        return text
    labels = text.split(".")
    # A numeric last label (decimal or hexadecimal) is ambiguous: getaddrinfo reads `010.0.0.1`
    # and `0x7f.0x1` as IPv4 addresses, and RFC 3696 section 2 forbids it as a TLD.
    last = labels[-1]
    if (
        len(text) <= _MAX_HOST_LEN
        and all(_DNS_LABEL_RE.fullmatch(label) for label in labels)
        and not last.isdigit()
        and not _HEX_LABEL_RE.fullmatch(last)
    ):
        return text
    raise error


def _check_semicolon(key: str, text: str) -> None:
    """Reject a literal ';' in the host part or the path (urlparse only splits the last segment)."""
    parts = urlsplit(text)
    if ";" in parts.netloc or ";" in parts.path:
        raise ValidationError("must not contain ';' in the host or path (use %3B)", field=key)


def _parse_url(key: str, text: str) -> ParseResult:
    """Parse a URL, rejecting malformed hosts and invalid ports without echoing the value."""
    try:
        parsed = urlparse(text)
        port = parsed.port
    except ValueError:
        raise ValidationError("must be a valid URL", field=key) from None
    if port is not None and not 1 <= port <= 65535:
        raise ValidationError("must be a valid URL", field=key)
    return parsed


def _check_host(key: str, text: str, parsed: ParseResult) -> None:
    """Reject control/non-printable characters (urlparse silently drops \\t \\r \\n)."""
    if not text.isprintable() or not (parsed.hostname or "").isprintable():
        raise ValidationError("must be a valid URL", field=key)


def _http_url(key: str, value: Any) -> str:
    text = _non_empty(key, value)
    parsed = _parse_url(key, text)
    _check_host(key, text, parsed)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValidationError("must be an http(s) URL with a host", field=key)
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError("must not embed credentials; use auth_token", field=key)
    if parsed.query or parsed.fragment:
        raise ValidationError("must not contain a query or fragment", field=key)
    _check_semicolon(key, text)
    return text


def _queue_url(key: str, value: Any) -> str:
    text = _non_empty(key, value)
    parsed = _parse_url(key, text)
    _check_host(key, text, parsed)
    if not parsed.scheme or not parsed.hostname:
        raise ValidationError("must be a URL with scheme and host", field=key)
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError(
            "must not embed credentials; use queue_username and queue_password", field=key
        )
    if parsed.fragment:
        raise ValidationError("must not contain a fragment", field=key)
    _check_semicolon(key, text)
    return text


def _log_level(key: str, value: Any) -> str:
    text = _non_empty(key, value)
    # `upper()` is Unicode-aware: `\u0131nfo` (dotless i) would become `INFO`.
    text = text.upper() if text.isascii() else ""
    if text not in LOG_LEVELS:
        raise ValidationError(f"must be one of {', '.join(LOG_LEVELS)}", field=key)
    return text


def _mask_query(value: Any) -> Any:
    """Mask every value in the query string of a URL, keeping the keys visible."""
    if not isinstance(value, str):
        return value
    parts = urlsplit(value)
    if not parts.query:
        return value
    masked = []
    for item in parts.query.split("&"):
        if not item:
            continue
        name, sep, _ = item.partition("=")
        masked.append(f"{name}={MASK}" if sep else MASK)
    return urlunsplit(parts._replace(query="&".join(masked)))


@dataclass(frozen=True)
class _Spec:
    default: Any
    parser: Callable[[str, Any], Any]
    secret: bool = False
    mask: Callable[[Any], Any] | None = None


_COMMON_SPECS: dict[str, _Spec] = {
    "queue_url": _Spec("amqp://127.0.0.1:5672", _queue_url, mask=_mask_query),
    "queue_username": _Spec("", _plain_str),
    "queue_password": _Spec("", _plain_str, secret=True),
    "request_timeout": _Spec(10.0, _positive_float),
    "log_level": _Spec("INFO", _log_level),
}

_AGENT_SPECS: dict[str, _Spec] = {
    "backend_url": _Spec("http://127.0.0.1:8080", _http_url),
    "auth_token": _Spec("", _plain_str, secret=True),
    "max_workers": _Spec(2, _positive_int),
    "heartbeat_interval": _Spec(30.0, _positive_float),
    "store_path": _Spec("agent_store.db", _fs_path),
    **_COMMON_SPECS,
}

_BACKEND_SPECS: dict[str, _Spec] = {
    "host": _Spec("127.0.0.1", _bind_host),
    "port": _Spec(8080, _port),
    "db_path": _Spec("backend_store.db", _fs_path),
    "api_token": _Spec("", _plain_str, secret=True),
    **_COMMON_SPECS,
}


class _Config:
    """Mixin giving configs a secret-safe repr and dict view."""

    _SECRETS: frozenset[str] = frozenset()
    _MASKS: Mapping[str, Callable[[Any], Any]] = {}

    def to_safe_dict(self) -> dict[str, Any]:
        """Return all fields with secret values masked; safe to log."""
        result: dict[str, Any] = {}
        for f in fields(self):  # type: ignore[arg-type]
            value = getattr(self, f.name)
            if f.name in self._SECRETS and value:
                value = MASK
            elif f.name in self._MASKS:
                value = self._MASKS[f.name](value)
            result[f.name] = value
        return result

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.to_safe_dict().items())
        return f"{type(self).__name__}({items})"

    __str__ = __repr__


@dataclass(frozen=True, repr=False)
class AgentConfig(_Config):
    backend_url: str
    auth_token: str
    max_workers: int
    heartbeat_interval: float
    store_path: str
    queue_url: str
    queue_username: str
    queue_password: str
    request_timeout: float
    log_level: str

    _SECRETS = frozenset(k for k, s in _AGENT_SPECS.items() if s.secret)
    _MASKS = {k: s.mask for k, s in _AGENT_SPECS.items() if s.mask is not None}


@dataclass(frozen=True, repr=False)
class BackendConfig(_Config):
    host: str
    port: int
    db_path: str
    api_token: str
    queue_url: str
    queue_username: str
    queue_password: str
    request_timeout: float
    log_level: str

    _SECRETS = frozenset(k for k, s in _BACKEND_SPECS.items() if s.secret)
    _MASKS = {k: s.mask for k, s in _BACKEND_SPECS.items() if s.mask is not None}


def _shown_path(path: str) -> str:
    """The path for an error message, unless it could forge log lines (non-printable)."""
    return _clip_tail(path) if path.isprintable() else _NON_PRINTABLE_PATH


def _config_path(path: Any) -> str:
    """The config file path as `str` (accepts `os.PathLike`); never repeats a bad value."""
    try:
        path = os.fspath(path)
    except TypeError:
        path = None
    if not isinstance(path, str):
        raise ValidationError("config file path must be a string or a path", field="config_file")
    if not path.strip():
        raise ValidationError("config file path must not be empty", field="config_file")
    return path


def _read_file(path: str) -> dict[str, Any]:
    if tomllib is None:  # pragma: no cover
        raise ValidationError("TOML support requires the 'tomli' package", field="config_file")
    shown = _shown_path(path)
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ValidationError(f"file not found: {shown}", field="config_file") from None
    except OSError as exc:
        raise ValidationError(
            f"cannot read {shown}: {exc.strerror or type(exc).__name__}", field="config_file"
        ) from None
    except tomllib.TOMLDecodeError as exc:
        detail = str(exc)
        detail = f": {_clip_toml_error(detail)}" if detail.isprintable() else ""
        raise ValidationError(f"invalid TOML in {shown}{detail}", field="config_file") from None
    except UnicodeDecodeError:
        raise ValidationError(f"{shown} is not valid UTF-8", field="config_file") from None
    except ValueError:  # e.g. embedded null byte in the path
        raise ValidationError("invalid config file path", field="config_file") from None
    except RecursionError:
        raise ValidationError(f"{shown} is nested too deeply", field="config_file") from None


def _resolve(
    specs: Mapping[str, _Spec],
    path: str | os.PathLike[str] | None,
    env: Mapping[str, str],
) -> dict[str, Any]:
    if path is None and CONFIG_FILE_ENV in env:  # defined but empty is an error, not "unset"
        path = env[CONFIG_FILE_ENV]
    file_values = _read_file(_config_path(path)) if path is not None else {}

    for key in file_values:
        if key not in specs:
            if _KEY_RE.fullmatch(key):
                raise ValidationError("unknown configuration key", field=_clip(key))
            raise ValidationError(
                "unknown configuration key (name has unsupported characters)",
                field="config_file",
            )
        if specs[key].secret:
            raise ValidationError(
                f"secrets must not be stored in the config file; set {ENV_PREFIX}{key.upper()}",
                field=key,
            )

    resolved: dict[str, Any] = {}
    for key, spec in specs.items():
        env_name = f"{ENV_PREFIX}{key.upper()}"
        if env_name in env:
            raw, label = env[env_name], env_name
        elif key in file_values:
            raw, label = file_values[key], key
        else:
            try:  # defaults are validated too
                resolved[key] = spec.parser(key, spec.default)
            except ValidationError as exc:
                raise ValidationError(f"{exc.message} (default)", field=key) from None
            continue
        resolved[key] = spec.parser(label, raw)
    return resolved


def load_agent_config(
    path: str | os.PathLike[str] | None = None, env: Mapping[str, str] | None = None
) -> AgentConfig:
    """Load and validate the agent configuration; raises ValidationError naming the bad key."""
    values = _resolve(_AGENT_SPECS, path, os.environ if env is None else env)
    return AgentConfig(**values)


def load_backend_config(
    path: str | os.PathLike[str] | None = None, env: Mapping[str, str] | None = None
) -> BackendConfig:
    """Load and validate the backend configuration; raises ValidationError naming the bad key."""
    values = _resolve(_BACKEND_SPECS, path, os.environ if env is None else env)
    return BackendConfig(**values)


def load_or_exit(loader: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a loader at startup; on invalid config write the error to stderr and exit non-zero."""
    try:
        return loader(*args, **kwargs)
    except ValidationError as exc:
        sys.stderr.write(f"invalid configuration: {exc}\n")
        raise SystemExit(EXIT_CODE_INVALID_CONFIG) from None
