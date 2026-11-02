import asyncio
import datetime
import os
import shutil
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.config import settings
from server.database import SessionLocal, engine
from server.models_db import AdminUser, AuditLog, Feedback, ProtectedWord, RetentionConfig, utcnow
from iyal_quality_analyzer.utils.logger import setup_logging, truncate_log_files, clear_recent_logs

logger = setup_logging("iyal.retention")


def format_bytes(num_bytes: int) -> str:
    """Formats raw bytes into a human-readable size string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def _get_sqlite_db_paths() -> dict:
    """Returns filesystem paths for the SQLite DB and its WAL/SHM companion files."""
    db_url = settings.DATABASE_URL
    if not ("sqlite" in db_url):
        return {"is_sqlite": False, "main": None, "wal": None, "shm": None}

    # Extract file path from sqlite:///path
    prefix = "sqlite:///"
    if db_url.startswith(prefix):
        raw_path = db_url[len(prefix):]
    else:
        raw_path = os.path.join(settings.DATA_DIR, "iyal.db")

    # Normalize absolute path
    main_path = os.path.abspath(raw_path)
    wal_path = f"{main_path}-wal"
    shm_path = f"{main_path}-shm"

    return {
        "is_sqlite": True,
        "main": main_path,
        "wal": wal_path,
        "shm": shm_path,
    }


def _get_db_total_size() -> int:
    """Calculates total size of SQLite DB on disk including WAL and SHM."""
    paths = _get_sqlite_db_paths()
    if not paths["is_sqlite"] or not paths["main"]:
        return 0

    total = 0
    for p in (paths["main"], paths["wal"], paths["shm"]):
        if p and os.path.exists(p):
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
    return total


def get_or_create_retention_config(db: Session) -> RetentionConfig:
    """Retrieves or creates the persistent retention configuration singleton."""
    cfg = db.query(RetentionConfig).first()
    if not cfg:
        cfg = RetentionConfig(
            audit_log_retention_days=settings.RETENTION_AUDIT_LOG_DAYS,
            feedback_retention_days=settings.RETENTION_FEEDBACK_RESOLVED_DAYS,
            cleanup_interval_hours=settings.RETENTION_CLEANUP_INTERVAL_HOURS,
            auto_vacuum=settings.RETENTION_AUTO_VACUUM,
            updated_by="system",
            updated_at=utcnow(),
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_retention_config(
    db: Session,
    audit_log_retention_days: int,
    feedback_retention_days: int,
    cleanup_interval_hours: int,
    auto_vacuum: bool,
    actor: str = "admin",
) -> RetentionConfig:
    """Updates retention policy settings."""
    cfg = get_or_create_retention_config(db)
    cfg.audit_log_retention_days = max(1, min(3650, int(audit_log_retention_days)))
    cfg.feedback_retention_days = max(0, min(3650, int(feedback_retention_days)))
    cfg.cleanup_interval_hours = max(1, min(720, int(cleanup_interval_hours)))
    cfg.auto_vacuum = bool(auto_vacuum)
    cfg.updated_by = actor
    cfg.updated_at = utcnow()
    db.commit()
    db.refresh(cfg)
    return cfg


def get_storage_telemetry(db: Session) -> dict:
    """
    Collects comprehensive storage capacity and retention telemetry:
    - SQLite database size (main, wal, shm, freelist)
    - Row counts across audit_logs, feedback, etc.
    - Application log file sizes (logs/app.log, error.log, etc.)
    - Host filesystem disk space (free, used, total)
    - Active retention policy & last cleanup details
    """
    cfg = get_or_create_retention_config(db)
    now = utcnow()

    # 1. SQLite Database Storage
    paths = _get_sqlite_db_paths()
    is_sqlite = paths["is_sqlite"]
    main_size = 0
    wal_size = 0
    shm_size = 0

    if is_sqlite and paths["main"] and os.path.exists(paths["main"]):
        main_size = os.path.getsize(paths["main"])
        if paths["wal"] and os.path.exists(paths["wal"]):
            wal_size = os.path.getsize(paths["wal"])
        if paths["shm"] and os.path.exists(paths["shm"]):
            shm_size = os.path.getsize(paths["shm"])

    total_db_bytes = main_size + wal_size + shm_size

    # Freelist & Page Stats for SQLite
    freelist_pages = 0
    page_count = 0
    page_size = 4096
    reclaimable_freelist_bytes = 0

    if is_sqlite:
        try:
            with engine.connect() as conn:
                res_fc = conn.execute(text("PRAGMA freelist_count;")).scalar()
                res_pc = conn.execute(text("PRAGMA page_count;")).scalar()
                res_ps = conn.execute(text("PRAGMA page_size;")).scalar()
                if res_fc is not None:
                    freelist_pages = int(res_fc)
                if res_pc is not None:
                    page_count = int(res_pc)
                if res_ps is not None:
                    page_size = int(res_ps)
                reclaimable_freelist_bytes = freelist_pages * page_size
        except Exception as e:
            logger.debug(f"Failed to fetch SQLite page pragmas: {e}")

    # 2. Database Table Row Counts & Expiration Analysis
    audit_total = db.query(AuditLog).count()
    audit_cutoff = now - datetime.timedelta(days=cfg.audit_log_retention_days)
    audit_expired = db.query(AuditLog).filter(AuditLog.timestamp < audit_cutoff).count()

    fb_total = db.query(Feedback).count()
    fb_new = db.query(Feedback).filter(Feedback.status == "new").count()
    fb_reviewed = db.query(Feedback).filter(Feedback.status == "reviewed").count()
    fb_resolved = db.query(Feedback).filter(Feedback.status == "resolved").count()

    fb_expired = 0
    if cfg.feedback_retention_days > 0:
        fb_cutoff = now - datetime.timedelta(days=cfg.feedback_retention_days)
        fb_expired = (
            db.query(Feedback)
            .filter(
                Feedback.status.in_(["resolved", "reviewed"]),
                Feedback.created_at < fb_cutoff,
            )
            .count()
        )

    users_total = db.query(AdminUser).count()
    words_total = db.query(ProtectedWord).count()

    # 3. Application Log Files Storage
    log_dir = settings.LOG_DIR
    log_files_info = []
    total_logs_bytes = 0

    if os.path.exists(log_dir):
        for entry in os.scandir(log_dir):
            if entry.is_file():
                try:
                    f_size = entry.stat().st_size
                    total_logs_bytes += f_size
                    mtime = datetime.datetime.fromtimestamp(
                        entry.stat().st_mtime, tz=datetime.timezone.utc
                    ).isoformat()
                    log_files_info.append(
                        {
                            "name": entry.name,
                            "size_bytes": f_size,
                            "size_formatted": format_bytes(f_size),
                            "modified_at": mtime,
                        }
                    )
                except OSError:
                    pass

    # Sort log files alphabetically
    log_files_info.sort(key=lambda x: x["name"])

    # 4. Host Filesystem Disk Capacity
    check_dir = settings.DATA_DIR if os.path.exists(settings.DATA_DIR) else os.getcwd()
    try:
        du = shutil.disk_usage(check_dir)
        disk_total = du.total
        disk_used = du.used
        disk_free = du.free
        disk_percent_used = round((disk_used / disk_total) * 100, 1)
    except Exception:
        disk_total = 0
        disk_used = 0
        disk_free = 0
        disk_percent_used = 0.0

    return {
        "database": {
            "engine": "SQLite (WAL Mode)" if is_sqlite else "PostgreSQL",
            "is_sqlite": is_sqlite,
            "main_file": paths["main"],
            "main_size_bytes": main_size,
            "main_size_formatted": format_bytes(main_size),
            "wal_size_bytes": wal_size,
            "wal_size_formatted": format_bytes(wal_size),
            "shm_size_bytes": shm_size,
            "shm_size_formatted": format_bytes(shm_size),
            "total_size_bytes": total_db_bytes,
            "total_size_formatted": format_bytes(total_db_bytes),
            "page_size": page_size,
            "page_count": page_count,
            "freelist_pages": freelist_pages,
            "reclaimable_freelist_bytes": reclaimable_freelist_bytes,
            "reclaimable_freelist_formatted": format_bytes(reclaimable_freelist_bytes),
        },
        "tables": {
            "audit_logs": {
                "total": audit_total,
                "expired_pending_cleanup": audit_expired,
            },
            "feedback": {
                "total": fb_total,
                "new": fb_new,
                "reviewed": fb_reviewed,
                "resolved": fb_resolved,
                "expired_pending_cleanup": fb_expired,
            },
            "admin_users": users_total,
            "protected_words": words_total,
        },
        "logs": {
            "directory": os.path.abspath(log_dir),
            "total_size_bytes": total_logs_bytes,
            "total_size_formatted": format_bytes(total_logs_bytes),
            "files": log_files_info,
            "rotation_max_bytes": settings.LOG_ROTATION_MAX_BYTES,
            "rotation_max_formatted": format_bytes(settings.LOG_ROTATION_MAX_BYTES),
            "rotation_backup_count": settings.LOG_ROTATION_BACKUP_COUNT,
        },
        "disk": {
            "directory": os.path.abspath(check_dir),
            "total_bytes": disk_total,
            "total_gb": round(disk_total / (1024**3), 2),
            "used_bytes": disk_used,
            "used_gb": round(disk_used / (1024**3), 2),
            "free_bytes": disk_free,
            "free_gb": round(disk_free / (1024**3), 2),
            "percent_used": disk_percent_used,
        },
        "policy": {
            "audit_log_retention_days": cfg.audit_log_retention_days,
            "feedback_retention_days": cfg.feedback_retention_days,
            "cleanup_interval_hours": cfg.cleanup_interval_hours,
            "auto_vacuum": cfg.auto_vacuum,
            "last_cleanup_at": cfg.last_cleanup_at.isoformat() if cfg.last_cleanup_at else None,
            "last_cleaned_audit_count": cfg.last_cleaned_audit_count,
            "last_cleaned_feedback_count": cfg.last_cleaned_feedback_count,
            "last_reclaimed_bytes": cfg.last_reclaimed_bytes,
            "last_reclaimed_formatted": format_bytes(cfg.last_reclaimed_bytes),
            "updated_by": cfg.updated_by,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
        },
    }


def execute_retention_cleanup(db: Session, actor: str = "system", clear_active_logs: bool = False, clear_all_audit_logs: bool = False) -> dict:
    """
    Executes the retention policy:
    1. Prunes audit logs older than audit_log_retention_days.
    2. Prunes resolved/reviewed feedback older than feedback_retention_days.
    3. Truncates SQLite WAL log and executes VACUUM to reclaim filesystem disk space.
    4. Rotates/cleans old auxiliary log files.
    5. Records an audit event and updates last_cleanup telemetry.
    """
    cfg = get_or_create_retention_config(db)
    now = utcnow()
    initial_db_size = _get_db_total_size()

    # 1. Prune Audit Logs (either all or expired)
    audit_cutoff = now - datetime.timedelta(days=cfg.audit_log_retention_days)
    if clear_all_audit_logs:
        audit_deleted = db.query(AuditLog).delete()
    else:
        audit_deleted = (
            db.query(AuditLog).filter(AuditLog.timestamp < audit_cutoff).delete()
        )

    # 2. Prune expired Feedback (only resolved or reviewed; new feedback is always preserved)
    feedback_deleted = 0
    if cfg.feedback_retention_days > 0:
        fb_cutoff = now - datetime.timedelta(days=cfg.feedback_retention_days)
        feedback_deleted = (
            db.query(Feedback)
            .filter(
                Feedback.status.in_(["resolved", "reviewed"]),
                Feedback.created_at < fb_cutoff,
            )
            .delete()
        )

    db.commit()

    # 3. Checkpoint WAL and optionally VACUUM SQLite DB
    vacuum_executed = False
    paths = _get_sqlite_db_paths()
    if paths["is_sqlite"]:
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE);")
                if cfg.auto_vacuum:
                    conn.exec_driver_sql("VACUUM;")
                    vacuum_executed = True
        except Exception as e:
            logger.warning(f"Error during SQLite WAL checkpoint or VACUUM: {e}")

    final_db_size = _get_db_total_size()
    reclaimed_bytes = max(0, initial_db_size - final_db_size)

    # 4. Clean old rotated log files in logs directory & optionally truncate active logs
    log_dir = settings.LOG_DIR
    pruned_log_files = []
    active_logs_truncated = False
    if clear_active_logs:
        trunc_info = truncate_log_files()
        pruned_log_files.extend(trunc_info.get("truncated_files", []))
        active_logs_truncated = True

    if os.path.exists(log_dir):
        cutoff_epoch = (now - datetime.timedelta(days=cfg.audit_log_retention_days)).timestamp()
        for entry in os.scandir(log_dir):
            if entry.is_file() and any(entry.name.endswith(f".{i}") for i in range(1, 100)):
                try:
                    if entry.stat().st_mtime < cutoff_epoch or clear_active_logs:
                        os.remove(entry.path)
                        pruned_log_files.append(entry.name)
                except OSError as e:
                    logger.debug(f"Failed to remove expired log backup {entry.name}: {e}")

    # 5. Update RetentionConfig with execution telemetry
    cfg.last_cleanup_at = now
    cfg.last_cleaned_audit_count = audit_deleted
    cfg.last_cleaned_feedback_count = feedback_deleted
    cfg.last_reclaimed_bytes = reclaimed_bytes
    db.commit()

    # 6. Record security & operational audit event
    details_str = (
        f"Retention policy cleanup executed by '{actor}': "
        f"Pruned {audit_deleted} audit logs (> {cfg.audit_log_retention_days}d), "
        f"{feedback_deleted} resolved feedbacks (> {cfg.feedback_retention_days}d). "
        f"Reclaimed {format_bytes(reclaimed_bytes)} disk space. "
        f"Vacuum executed: {vacuum_executed}. "
        f"Pruned log archives: {len(pruned_log_files)}."
    )

    audit_entry = AuditLog(
        timestamp=now,
        level="INFO",
        event_type="retention_cleanup",
        actor=actor,
        details=details_str,
    )
    db.add(audit_entry)
    db.commit()

    logger.info(details_str)

    return {
        "success": True,
        "timestamp": now.isoformat(),
        "actor": actor,
        "audit_logs_pruned": audit_deleted,
        "feedback_pruned": feedback_deleted,
        "reclaimed_bytes": reclaimed_bytes,
        "reclaimed_formatted": format_bytes(reclaimed_bytes),
        "vacuum_executed": vacuum_executed,
        "pruned_log_files": pruned_log_files,
        "active_logs_truncated": active_logs_truncated,
        "initial_db_size_formatted": format_bytes(initial_db_size),
        "final_db_size_formatted": format_bytes(final_db_size),
    }


class BackgroundRetentionWorker:
    """
    Lightweight asynchronous background loop that checks and executes
    the retention policy periodically according to cleanup_interval_hours.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

    def start(self):
        if self._running or self._task:
            return
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Background retention worker task started.")

    async def stop(self):
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Background retention worker task stopped.")

    async def _worker_loop(self):
        # Initial sleep on startup so heavy ML warmup or initialization finishes first
        await asyncio.sleep(60)

        while self._running:
            try:
                db = SessionLocal()
                try:
                    cfg = get_or_create_retention_config(db)
                    interval_sec = cfg.cleanup_interval_hours * 3600
                    should_run = False

                    if not cfg.last_cleanup_at:
                        should_run = True
                    else:
                        elapsed = (
                            utcnow() - cfg.last_cleanup_at.replace(tzinfo=datetime.timezone.utc)
                        ).total_seconds()
                        if elapsed >= interval_sec:
                            should_run = True

                    if should_run:
                        logger.info("Scheduled retention cleanup cycle triggered.")
                        execute_retention_cleanup(db, actor="system_scheduler")
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background retention worker loop: {e}", exc_info=True)

            # Check every hour
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break


retention_worker = BackgroundRetentionWorker()

