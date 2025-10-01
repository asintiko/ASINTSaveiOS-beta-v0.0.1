"""Project-wide logging configuration helpers."""

from __future__ import annotations

import logging
import os
from typing import Iterable, Mapping, MutableMapping

try:  # Prefer rich logs when available
    from rich.console import Console
    from rich.logging import RichHandler
except ImportError:  # pragma: no cover - rich is optional at runtime
    RichHandler = None  # type: ignore[assignment]
    Console = None  # type: ignore[assignment]

_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_TEXT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)

_BASE_LANGUAGE = "en"
_DEFAULT_LANGUAGE = "ru"
_LOG_LANGUAGE = _DEFAULT_LANGUAGE
_LOG_MESSAGES: dict[str, dict[str, str]] = {}
_AVAILABLE_LANGUAGES: set[str] = {_BASE_LANGUAGE, _DEFAULT_LANGUAGE}


class _LocalizationFilter(logging.Filter):
    """Translate known log messages into the configured language."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - logging contract
        message_template = record.msg
        if not isinstance(message_template, str):
            return True

        translations = _LOG_MESSAGES.get(message_template)
        if not translations:
            return True

        localized = translations.get(_LOG_LANGUAGE)
        if not localized:
            return True

        record.msg = localized
        return True


def _coerce_level(value: str | int | None, fallback: int) -> int:
    """Translate string or numeric level declarations into logging levels."""

    if value is None:
        return fallback
    if isinstance(value, int):
        return value
    candidate = value.strip().upper()
    if candidate.isdigit():
        return int(candidate)
    return getattr(logging, candidate, fallback)


def set_log_language(language: str | None) -> None:
    """Change the active language for subsequent log messages."""

    global _LOG_LANGUAGE
    if not language:
        _LOG_LANGUAGE = _DEFAULT_LANGUAGE
        return

    normalized = language.strip().lower()
    if not normalized or normalized not in _AVAILABLE_LANGUAGES:
        _LOG_LANGUAGE = _DEFAULT_LANGUAGE
        return
    _LOG_LANGUAGE = normalized


def get_log_language() -> str:
    """Return the current logging language identifier."""

    return _LOG_LANGUAGE


def register_log_translations(
    translations: Mapping[str, Mapping[str, str]]
) -> None:
    """Register additional localized strings for log messages.

    The keys must match the *English* (or baseline) message templates used as
    the first argument in ``logger`` calls. Placeholders (``%s``/``%(name)s``)
    must be kept intact so that the logging module can interpolate values.
    """

    for template, localized in translations.items():
        if not isinstance(template, str):
            continue
        bucket = _LOG_MESSAGES.setdefault(template, {})
        for language, message in localized.items():
            normalized_lang = language.strip().lower()
            if not normalized_lang:
                continue
            bucket[normalized_lang] = message
            _AVAILABLE_LANGUAGES.add(normalized_lang)


def available_log_languages() -> tuple[str, ...]:
    """Return a sorted tuple of languages supported for logging."""

    return tuple(sorted(_AVAILABLE_LANGUAGES))


def get_default_log_language() -> str:
    """Return the default logging language identifier."""

    return _DEFAULT_LANGUAGE


def setup_logging(
    *,
    level: str | int | None = None,
    module_levels: Mapping[str, str | int] | None = None,
    noisy_modules: Iterable[str] | None = None,
    language: str | None = None,
) -> None:
    """Configure root logging with readable formatting and sane defaults.

    Parameters
    ----------
    level:
        Base log level for the application. Defaults to ``LOG_LEVEL`` env var or
        ``INFO`` when unset.
    module_levels:
        Explicit per-module overrides. Provided values take precedence over the
        built-in suggestions used to silence particularly noisy libraries.
    noisy_modules:
        Additional module names to downshift to ``INFO`` level automatically.
    """

    env_level = os.getenv("LOG_LEVEL")
    env_language = language or os.getenv("LOG_LANGUAGE")
    set_log_language(env_language)
    base_level = _coerce_level(level or env_level, logging.INFO)

    handlers: list[logging.Handler] = []
    log_format = _DEFAULT_TEXT_FORMAT

    loc_filter = _LocalizationFilter()

    if RichHandler is not None:
        console = Console(stderr=True, soft_wrap=False) if Console else None
        handlers.append(
            RichHandler(
                markup=True,
                rich_tracebacks=True,
                show_path=False,
                show_time=True,
                log_time_format=_DEFAULT_DATE_FORMAT,
                console=console,
            )
        )
        log_format = "%(name)s | %(message)s"
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter(_DEFAULT_TEXT_FORMAT, _DEFAULT_DATE_FORMAT)
        )
        handlers.append(stream_handler)

    logging.basicConfig(
        level=base_level,
        format=log_format,
        datefmt=_DEFAULT_DATE_FORMAT,
        handlers=handlers,
        force=True,  # Replace any handlers pre-configured by libraries
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(loc_filter)

    logging.captureWarnings(True)

    default_levels: MutableMapping[str, str | int] = {
        "aiosqlite": os.getenv("SQL_LOG_LEVEL", "INFO"),
        "aiogram.event": os.getenv("AIOGRAM_EVENT_LOG_LEVEL", "INFO"),
        "aiogram.dispatcher": os.getenv("AIOGRAM_DISPATCHER_LOG_LEVEL", "INFO"),
        "aiohttp.access": os.getenv("AIOHTTP_ACCESS_LOG_LEVEL", "WARNING"),
        "asyncio": os.getenv("ASYNCIO_LOG_LEVEL", "WARNING"),
    }

    if module_levels:
        default_levels.update(module_levels)

    if noisy_modules:
        for module_name in noisy_modules:
            default_levels.setdefault(module_name, "INFO")

    for module_name, module_level in default_levels.items():
        logging.getLogger(module_name).setLevel(
            _coerce_level(module_level, logging.INFO)
        )


def get_logger(name: str | None = None, **context: object) -> logging.Logger:
    """Retrieve a logger, optionally wrapping it with contextual information."""

    base_logger = logging.getLogger(name if name else "SaveMod")
    if not context:
        return base_logger
    return logging.LoggerAdapter(base_logger, context)  # type: ignore[return-value]


__all__ = [
    "setup_logging",
    "set_log_language",
    "get_log_language",
    "register_log_translations",
    "available_log_languages",
    "get_default_log_language",
    "get_logger",
]
