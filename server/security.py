import collections
import datetime
import threading
import time
import uuid
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from server.config import settings
from server.models_db import AuditLog
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.security")


def record_audit_log(
    db: Session,
    event_type: str,
    actor: str,
    details: str,
    level: str = "INFO",
):
    """Writes an audit log entry to the database and application logger."""
    try:
        entry = AuditLog(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            level=level,
            event_type=event_type,
            actor=actor or "unknown",
            details=details,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write audit log: {e}")


class SecurityDefenseEngine:
    """
    In-Monolith Security Defense Engine providing:
      1. Sliding-Window Rate Limiting per IP across route tiers (general, inference, feedback)
      2. Automatic Temporary IP Ban on repeated rate-limit violations (DDoS mitigation)
      3. Brute-Force Login Lockout per IP and per account identifier
      4. Real-time security telemetry for the /admin dashboard
    """

    def __init__(self):
        self._lock = threading.Lock()
        # ip -> {tier -> deque of timestamps}
        self._ip_requests = collections.defaultdict(
            lambda: collections.defaultdict(collections.deque)
        )
        # ip -> violation count
        self._ip_violations = collections.defaultdict(int)
        # ip -> unban_epoch_timestamp
        self._banned_ips = {}
        # key (ip or username/email) -> {"failures": int, "locked_until": float, "last_attempt": float}
        self._login_attempts = collections.defaultdict(
            lambda: {"failures": 0, "locked_until": 0.0, "last_attempt": 0.0}
        )
        self.total_blocked_requests = 0
        self.total_rate_limited = 0
        self.total_brute_force_blocks = 0

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def is_ip_banned(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            unban_at = self._banned_ips.get(ip)
            if unban_at:
                if now < unban_at:
                    return True, int(unban_at - now)
                else:
                    del self._banned_ips[ip]
                    self._ip_violations[ip] = 0
        return False, 0

    def unban_ip(self, ip: str) -> bool:
        with self._lock:
            removed = ip in self._banned_ips
            self._banned_ips.pop(ip, None)
            self._ip_violations.pop(ip, None)
            self._login_attempts.pop(f"ip:{ip}", None)
            return removed

    def check_rate_limit(self, ip: str, tier: str, limit_per_min: int) -> tuple[bool, int]:
        """Returns (allowed: bool, retry_after_seconds: int)."""
        now = time.time()
        window = 60.0
        with self._lock:
            # 1. Check active IP ban
            unban_at = self._banned_ips.get(ip)
            if unban_at:
                if now < unban_at:
                    self.total_blocked_requests += 1
                    return False, int(unban_at - now)
                else:
                    del self._banned_ips[ip]
                    self._ip_violations[ip] = 0

            dq = self._ip_requests[ip][tier]
            while dq and (now - dq[0]) > window:
                dq.popleft()

            if len(dq) >= limit_per_min:
                self.total_rate_limited += 1
                self._ip_violations[ip] += 1
                retry_after = max(1, int(window - (now - dq[0])))

                if self._ip_violations[ip] >= settings.IP_BAN_VIOLATION_THRESHOLD:
                    ban_until = now + settings.IP_BAN_DURATION_SECONDS
                    self._banned_ips[ip] = ban_until
                    logger.warning(
                        f"SECURITY: Auto-banned IP {ip} for {settings.IP_BAN_DURATION_SECONDS}s due to repeated rate limit violations."
                    )
                    return False, settings.IP_BAN_DURATION_SECONDS

                return False, retry_after

            dq.append(now)
            return True, 0

    def check_login_allowed(self, ip: str, identifier: str):
        """Raises HTTP 429 if IP or account identifier is currently locked out from brute-force attempts."""
        now = time.time()
        keys = [f"ip:{ip}", f"acct:{identifier.strip().lower()}"]
        with self._lock:
            for k in keys:
                state = self._login_attempts[k]
                if state["locked_until"] > now:
                    remaining = int(state["locked_until"] - now)
                    self.total_brute_force_blocks += 1
                    logger.warning(
                        f"SECURITY: Blocked brute-force login attempt for {k} ({remaining}s lockout remaining)"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many failed login attempts. Account/IP locked for {remaining} seconds.",
                    )

    def record_login_failure(self, ip: str, identifier: str) -> int:
        """Records a failed login attempt and returns remaining attempts before lockout."""
        now = time.time()
        keys = [f"ip:{ip}", f"acct:{identifier.strip().lower()}"]
        with self._lock:
            max_failures = 0
            for k in keys:
                state = self._login_attempts[k]
                # Reset failure counter if last failure was longer ago than lockout window
                if state["last_attempt"] and (now - state["last_attempt"]) > settings.LOGIN_LOCKOUT_SECONDS:
                    state["failures"] = 0
                state["failures"] += 1
                state["last_attempt"] = now
                max_failures = max(max_failures, state["failures"])
                if state["failures"] >= settings.MAX_LOGIN_ATTEMPTS:
                    state["locked_until"] = now + settings.LOGIN_LOCKOUT_SECONDS
                    logger.warning(
                        f"SECURITY: Brute-force lockout triggered for {k} for {settings.LOGIN_LOCKOUT_SECONDS}s"
                    )
            return max(0, settings.MAX_LOGIN_ATTEMPTS - max_failures)

    def record_login_success(self, ip: str, identifier: str):
        with self._lock:
            self._login_attempts.pop(f"ip:{ip}", None)
            self._login_attempts.pop(f"acct:{identifier.strip().lower()}", None)

    def get_security_stats(self) -> dict:
        now = time.time()
        with self._lock:
            active_bans = [
                {"ip": ip, "seconds_remaining": int(until - now)}
                for ip, until in self._banned_ips.items()
                if until > now
            ]
            active_lockouts = [
                {
                    "target": k,
                    "failures": v["failures"],
                    "seconds_remaining": int(v["locked_until"] - now),
                }
                for k, v in self._login_attempts.items()
                if v["locked_until"] > now
            ]
            return {
                "total_rate_limited": self.total_rate_limited,
                "total_blocked_requests": self.total_blocked_requests,
                "total_brute_force_blocks": self.total_brute_force_blocks,
                "active_ip_bans": active_bans,
                "active_login_lockouts": active_lockouts,
                "tracked_ips": len(self._ip_requests),
                "limits": {
                    "general_per_min": settings.RATE_LIMIT_GENERAL_PER_MIN,
                    "inference_per_min": settings.RATE_LIMIT_INFERENCE_PER_MIN,
                    "feedback_per_min": settings.RATE_LIMIT_FEEDBACK_PER_MIN,
                    "max_login_attempts": settings.MAX_LOGIN_ATTEMPTS,
                    "login_lockout_seconds": settings.LOGIN_LOCKOUT_SECONDS,
                },
            }


security_engine = SecurityDefenseEngine()


class MonolithSecurityMiddleware(BaseHTTPMiddleware):
    """
    Unified security & observability middleware for the monolithic FastAPI server:
      - Assigns X-Request-ID correlation header
      - Enforces max request body size (prevents payload DoS)
      - Enforces tiered IP rate limiting & automatic DDoS IP ban
      - Injects security headers and logs request latency
    """

    INFERENCE_PATHS = {
        "/analyze/",
        "/analyze",
        "/api/v1/analyze",
        "/get_encoding/",
        "/get_encoding",
        "/api/v1/detect-encoding",
        "/colloquial_to_standard/",
        "/colloquial_to_standard",
        "/api/v1/colloquial-to-standard",
        "/legacy2unicode/",
        "/legacy2unicode",
        "/api/v1/legacy2unicode",
    }

    FEEDBACK_PATHS = {
        "/feedback/",
        "/feedback",
        "/api/v1/feedback",
    }

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        client_ip = security_engine.get_client_ip(request)
        path = request.url.path

        # 1. Payload size guard
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_UPLOAD_BYTES:
                    logger.warning(
                        f"[{req_id}] Blocked oversized payload ({content_length} bytes) from {client_ip} on {path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "detail": f"Request payload exceeds maximum allowed size of {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                        },
                    )
            except ValueError:
                pass

        # 2. Skip rate limiting for static assets (.css, .js, .ico, etc.)
        if not path.startswith("/static/"):
            if path in self.INFERENCE_PATHS:
                allowed, retry_after = security_engine.check_rate_limit(
                    client_ip, "inference", settings.RATE_LIMIT_INFERENCE_PER_MIN
                )
            elif path in self.FEEDBACK_PATHS and request.method == "POST":
                allowed, retry_after = security_engine.check_rate_limit(
                    client_ip, "feedback", settings.RATE_LIMIT_FEEDBACK_PER_MIN
                )
            else:
                allowed, retry_after = security_engine.check_rate_limit(
                    client_ip, "general", settings.RATE_LIMIT_GENERAL_PER_MIN
                )

            if not allowed:
                logger.warning(
                    f"[{req_id}] Rate limit exceeded for IP {client_ip} on {request.method} {path} (retry_after={retry_after}s)"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Request-ID": req_id,
                    },
                    content={
                        "detail": f"Rate limit exceeded. Please wait {retry_after} seconds before retrying."
                    },
                )

        # 3. Execute request & log observability metrics
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            logger.exception(
                f"[{req_id}] Unhandled exception on {request.method} {path} from {client_ip} ({elapsed_ms}ms): {exc}"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={"X-Request-ID": req_id},
                content={"detail": "Internal server error", "request_id": req_id},
            )

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if not path.startswith("/static/"):
            logger.info(
                f"[{req_id}] {client_ip} {request.method} {path} -> {response.status_code} ({elapsed_ms}ms)"
            )

        return response

