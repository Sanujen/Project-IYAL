import logging
import os
from logging.handlers import RotatingFileHandler
from collections import deque

# In-memory ring buffer of recent log entries for the /admin observability dashboard
RECENT_LOGS = deque(maxlen=500)


class RingBufferHandler(logging.Handler):
    """Stores formatted log records in an in-memory ring buffer for admin inspection."""

    def emit(self, record: logging.LogRecord):
        try:
            RECENT_LOGS.append(
                {
                    "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )
        except Exception:
            self.handleError(record)

    def formatTime(self, record, datefmt=None):
        import datetime

        ct = datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc)
        if datefmt:
            return ct.strftime(datefmt) + " UTC"
        return ct.isoformat()


_RING_HANDLER = RingBufferHandler()
_RING_HANDLER.setLevel(logging.INFO)


def setup_logging(module_name: str = "iyal", log_level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a structured logger with console output, rotating file handlers,
    and an in-memory ring buffer for observability in the /admin portal.
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # 2. Rotating File Handlers (logs/app.log & logs/error.log)
    try:
        log_dir = os.getenv("LOG_DIR", os.path.join(os.getcwd(), "logs"))
        os.makedirs(log_dir, exist_ok=True)

        app_file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        app_file_handler.setLevel(log_level)
        app_file_handler.setFormatter(formatter)
        logger.addHandler(app_file_handler)

        err_file_handler = RotatingFileHandler(
            os.path.join(log_dir, "error.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        err_file_handler.setLevel(logging.WARNING)
        err_file_handler.setFormatter(formatter)
        logger.addHandler(err_file_handler)
    except Exception:
        # Fallback gracefully if filesystem is read-only
        pass

    # 3. In-memory Ring Buffer Handler
    logger.addHandler(_RING_HANDLER)
    logger.propagate = False

    return logger


def get_recent_logs(limit: int = 100, level: str = None) -> list:
    """Returns the most recent log entries from the ring buffer."""
    items = list(RECENT_LOGS)
    if level and level.upper() != "ALL":
        items = [x for x in items if x["level"] == level.upper()]
    return list(reversed(items))[:limit]
