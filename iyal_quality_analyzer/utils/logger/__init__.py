from .setup_logging import (
    setup_logging,
    get_recent_logs,
    RECENT_LOGS,
    clear_recent_logs,
    truncate_log_files,
)

__all__ = [
    "setup_logging",
    "get_recent_logs",
    "RECENT_LOGS",
    "clear_recent_logs",
    "truncate_log_files",
]
