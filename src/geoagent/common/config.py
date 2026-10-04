"""Layered configuration (defaults < TOML file < GEOAGENT_ env vars) for agent and backend."""

from __future__ import annotations

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
_INT_RE = re.compile(r"[+-]?[0-9]+")
_FLOAT_RE = re.compile(
    r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?|[+-]?(inf|infinity|nan)", re.IGNORECASE
)


def _describe(value: Any) -> str:
    """Repeat scalars (truncated); only name the type of anything else."""
    if not isinstance(value, (str, int, float)):
        return type(value).__name__
    try:
        text = repr(value)
    except ValueError:  # int too large to render
        return type(value).__name__
    return text if len(text) <= _MAX_ECHO else text[:_MAX_ECHO] + "\u2026"


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
    return text


def _log_level(key: str, value: Any) -> str:
    text = _non_empty(key, value).upper()
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
    "queue_username": _Spec("", _parse_str),
    "queue_password": _Spec("", _parse_str, secret=True),
    "request_timeout": _Spec(10.0, _positive_float),
    "log_level": _Spec("INFO", _log_level),
}

_AGENT_SPECS: dict[str, _Spec] = {
    "backend_url": _Spec("http://127.0.0.1:8080", _http_url),
    "auth_token": _Spec("", _parse_str, secret=True),
    "max_workers": _Spec(2, _positive_int),
    "heartbeat_interval": _Spec(30.0, _positive_float),
    "store_path": _Spec("agent_store.db", _non_empty),
    **_COMMON_SPECS,
}

_BACKEND_SPECS: dict[str, _Spec] = {
    "host": _Spec("127.0.0.1", _non_empty),
    "port": _Spec(8080, _port),
    "db_path": _Spec("backend_store.db", _non_empty),
    "api_token": _Spec("", _parse_str, secret=True),
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


def _read_file(path: str) -> dict[str, Any]:
    if tomllib is None:  # pragma: no cover
        raise ValidationError("TOML support requires the 'tomli' package", field="config_file")
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ValidationError(f"file not found: {path}", field="config_file") from None
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}", field="config_file") from None
    except tomllib.TOMLDecodeError as exc:
        raise ValidationError(f"invalid TOML in {path}: {exc}", field="config_file") from None
    except UnicodeDecodeError:
        raise ValidationError(f"{path} is not valid UTF-8", field="config_file") from None
    except ValueError:  # e.g. embedded null byte in the path
        raise ValidationError("invalid config file path", field="config_file") from None
    except RecursionError:
        raise ValidationError(f"{path} is nested too deeply", field="config_file") from None


def _resolve(
    specs: Mapping[str, _Spec],
    path: str | None,
    env: Mapping[str, str],
) -> dict[str, Any]:
    if path is None:
        path = env.get(CONFIG_FILE_ENV) or None
    file_values = _read_file(path) if path is not None else {}

    for key in file_values:
        if key not in specs:
            raise ValidationError("unknown configuration key", field=key)
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
            resolved[key] = spec.default
            continue
        resolved[key] = spec.parser(label, raw)
    return resolved


def load_agent_config(path: str | None = None, env: Mapping[str, str] | None = None) -> AgentConfig:
    """Load and validate the agent configuration; raises ValidationError naming the bad key."""
    values = _resolve(_AGENT_SPECS, path, os.environ if env is None else env)
    return AgentConfig(**values)


def load_backend_config(
    path: str | None = None, env: Mapping[str, str] | None = None
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
