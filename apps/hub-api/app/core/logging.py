from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        event = getattr(record, "event", None)
        if isinstance(event, dict):
            payload["event"] = event

        return json.dumps(payload, sort_keys=True)


class PrettyLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = f"{record.levelname:<5}"
        logger_name = record.name
        event = getattr(record, "event", None)

        if isinstance(event, dict):
            action = event.get("action")
            if action == "http.request":
                parts = [
                    str(event.get("method", "-")),
                    str(event.get("path", "-")),
                    str(event.get("status_code", "-")),
                    f"{event.get('duration_ms', '-')}ms",
                    f"rid={event.get('request_id', '-')}",
                ]
                message = " ".join(parts)
            elif action == "http.request_failed":
                parts = [
                    str(event.get("method", "-")),
                    str(event.get("path", "-")),
                    "FAILED",
                    f"{event.get('duration_ms', '-')}ms",
                    f"rid={event.get('request_id', '-')}",
                ]
                message = " ".join(parts)
            else:
                message = f"{action} {record.getMessage()}"

            extras = []
            for key in (
                "device_id",
                "status",
                "topic",
                "target_id",
                "actor_id",
                "body",
                "error",
            ):
                if key in event and event[key] not in (None, "", {}):
                    extras.append(f"{key}={event[key]}")

            if extras:
                message = f"{message} | " + " | ".join(extras)
        else:
            message = record.getMessage()

        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"

        return f"{timestamp} | {level} | {logger_name} | {message}"


def configure_logging(settings: Settings) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)

    pretty_formatter = PrettyLogFormatter()
    json_formatter = JsonLogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(pretty_formatter)

    pretty_file_handler = RotatingFileHandler(
        log_dir / settings.log_filename,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    pretty_file_handler.setLevel(level)
    pretty_file_handler.setFormatter(pretty_formatter)

    json_file_handler = RotatingFileHandler(
        log_dir / settings.log_json_filename,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    json_file_handler.setLevel(level)
    json_file_handler.setFormatter(json_formatter)

    root.addHandler(stream_handler)
    root.addHandler(pretty_file_handler)
    root.addHandler(json_file_handler)

    for logger_name in ("app", "alice"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.handlers.clear()
        logger.addHandler(stream_handler)
        logger.addHandler(pretty_file_handler)
        logger.addHandler(json_file_handler)
        logger.propagate = False


def close_logging() -> None:
    handlers = []
    for logger_name in ("", "app", "alice"):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers:
            if handler not in handlers:
                handlers.append(handler)
        logger.handlers.clear()

    for handler in handlers:
        try:
            handler.flush()
        except Exception:
            pass
        try:
            handler.close()
        except Exception:
            pass
