import asyncio
import datetime
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Union
import psutil
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from iyal_quality_analyzer.quality_analyzer import (
    multi_sentence_quality_analyzer,
    get_encoding_fun,
    detect_legacy_encoding_details,
)
from iyal_quality_analyzer.utils.legacy_converter.legacy_converter import (
    convert_legacy_to_unicode,
    ALL_ENCODINGS,
)
from iyal_quality_analyzer.utils.english_word_check import (
    set_global_protected_words,
    get_global_protected_words,
)
from iyal_quality_analyzer.utils.logger import setup_logging, get_recent_logs

from server.config import settings
from server.database import Base, SessionLocal, engine, get_db
from server.models_db import AdminUser, AuditLog, Feedback, ModelConfig, ProtectedWord
from server.auth import (
    create_access_token,
    get_current_admin,
    hash_password,
    require_superadmin,
    seed_superadmin,
    verify_google_id_token,
    verify_password,
)
from server.security import (
    MonolithSecurityMiddleware,
    record_audit_log,
    security_engine,
)
from server.model_manager import model_manager
from server.file_parser import create_docx_bytes, extract_text_from_upload

logger = setup_logging("iyal.server")

STARTUP_TIME = time.time()
INFERENCE_SEMAPHORE = asyncio.Semaphore(settings.MAX_CONCURRENT_INFERENCES)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)


def _sync_protected_words(db: Session):
    words = [row.word for row in db.query(ProtectedWord).all()]
    set_global_protected_words(words)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Project IYAL Monolithic Server...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_superadmin(db)
        _sync_protected_words(db)
        model_manager.initialize_from_db(db)
        record_audit_log(
            db,
            event_type="server_startup",
            actor="system",
            details="Project IYAL monolithic server initialized successfully.",
            level="INFO",
        )
    finally:
        db.close()
    logger.info("Project IYAL Server is ready to accept requests.")
    yield
    logger.info("Shutting down Project IYAL Server...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Monolithic API & Web Application for normalizing Tamil, Romanized Tanglish, "
        "and Legacy Tamil Font encodings into Standard Tamil Unicode."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(MonolithSecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# =====================================================================
# Pydantic Schemas
# =====================================================================
class AnalyzeInputRequest(BaseModel):
    input_text: str = Field(..., min_length=1)
    encoding: Optional[str] = None
    need_translation: bool = False
    colloquial_to_standard: bool = False
    protected_words: Optional[List[str]] = None


class Legacy2UnicodeInputRequest(BaseModel):
    input_text: str = Field(..., min_length=1)
    encoding: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class InputRequest(BaseModel):
    input_text: str = Field(..., min_length=1)
    protected_words: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    created_at: Optional[str] = None
    category: str = "general"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    input_text: Optional[str] = None
    output: Optional[Union[dict, list, str]] = None
    feedback: str = Field(..., min_length=2, max_length=4000)


class ProtectedWordCreateRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=120)
    skip_translation: bool = True


class ExportDocxRequest(BaseModel):
    text: str


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Admin email or username")
    password: str = Field(..., min_length=1)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class AcceptInviteRequest(BaseModel):
    email: str
    invite_token: str
    new_password: str = Field(..., min_length=8)


class InviteAdminRequest(BaseModel):
    email: str = Field(..., description="Gmail address of the admin to invite")
    username: Optional[str] = None
    temporary_password: Optional[str] = None
    role: str = Field(default="admin", pattern="^(admin|superadmin)$")


class UpdateAdminUserRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    new_password: Optional[str] = None


class UpdateFeedbackStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(new|reviewed|resolved)$")
    admin_notes: Optional[str] = None


class UpdateModelConfigRequest(BaseModel):
    mode: str = Field(..., pattern="^(default|custom)$")
    custom_url: Optional[str] = None
    api_key: Optional[str] = None


class TestModelRequest(BaseModel):
    sample_input: Optional[str] = None


class UnbanIpRequest(BaseModel):
    ip: str


def _validate_input_length(text: str):
    if len(text) > settings.MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input text length ({len(text)} chars) exceeds maximum allowed limit ({settings.MAX_INPUT_CHARS} chars).",
        )


# =====================================================================
# Frontend HTML Routes (/ and /admin)
# =====================================================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_public_ui():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Project IYAL UI loading...</h1>")


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin/", response_class=HTMLResponse, include_in_schema=False)
async def serve_admin_ui():
    admin_path = os.path.join(STATIC_DIR, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return HTMLResponse("<h1>Project IYAL Admin Portal loading...</h1>")


# =====================================================================
# Public Normalization & Core Domain Pipeline Endpoints
# =====================================================================
@app.get("/api/v1/public-config")
def get_public_config():
    """Returns public UI configuration parameters (such as the ResearchGate paper link from .env)."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "researchgate_paper_url": settings.get_researchgate_url(),
    }


@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    uptime_s = round(time.time() - STARTUP_TIME, 1)
    models_status = model_manager.get_all_models_status(db)
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "uptime_seconds": uptime_s,
        "models": models_status,
        "protected_words_count": len(get_global_protected_words()),
        "researchgate_paper_url": settings.get_researchgate_url(),
    }


@app.get("/api/v1/encodings")
def list_supported_encodings():
    return {"encodings": ALL_ENCODINGS}


@app.post("/api/v1/detect-encoding")
@app.post("/get_encoding/")
async def detect_encoding_endpoint(request: InputRequest):
    """
    Detects whether any non-English word in the input paragraph uses a legacy Tamil font,
    and returns the auto-detected font name + live preview samples for UI confirmation.
    """
    _validate_input_length(request.input_text)
    async with INFERENCE_SEMAPHORE:
        try:
            details = await asyncio.to_thread(
                detect_legacy_encoding_details,
                model_manager.classifier,
                request.input_text,
                request.protected_words,
            )
            return details
        except Exception as e:
            logger.exception(f"Error detecting encoding: {e}")
            raise HTTPException(status_code=500, detail=f"Error detecting encoding: {e}")


@app.post("/api/v1/analyze")
@app.post("/analyze/")
async def analyze_input_endpoint(request: AnalyzeInputRequest):
    """
    Executes the full 11-step Tamil text normalization pipeline across the input paragraph.
    """
    _validate_input_length(request.input_text)
    t0 = time.perf_counter()
    async with INFERENCE_SEMAPHORE:
        try:
            output_text, sentence_results = await asyncio.to_thread(
                multi_sentence_quality_analyzer,
                model_manager.classifier,
                model_manager.standardizer,
                request.input_text,
                request.encoding,
                request.need_translation,
                request.colloquial_to_standard,
                request.protected_words,
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "output": output_text,
                "result": sentence_results,
                "encoding_used": request.encoding or "auto",
                "need_translation": request.need_translation,
                "colloquial_to_standard": request.colloquial_to_standard,
                "metrics": {
                    "latency_ms": elapsed_ms,
                    "sentences_count": len(sentence_results),
                    "words_count": sum(len(s.get("results", [])) for s in sentence_results),
                },
            }
        except Exception as e:
            logger.exception(f"Error in /analyze: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing input: {e}")


@app.post("/api/v1/legacy2unicode")
@app.post("/legacy2unicode/")
async def legacy2unicode_endpoint(request: Legacy2UnicodeInputRequest):
    """Converts legacy Tamil font-encoded text directly to Tamil Unicode."""
    _validate_input_length(request.input_text)
    try:
        output_text = await asyncio.to_thread(
            convert_legacy_to_unicode, request.input_text, request.encoding
        )
        return {"output": output_text, "encoding": request.encoding or "auto2utf8"}
    except Exception as e:
        logger.exception(f"Error in /legacy2unicode: {e}")
        raise HTTPException(status_code=500, detail=f"Error converting legacy text: {e}")


@app.post("/api/v1/colloquial-to-standard")
@app.post("/colloquial_to_standard/")
async def colloquial_to_standard_endpoint(request: InputRequest):
    """Converts colloquial Tamil text into standard formal Tamil using Model 2."""
    _validate_input_length(request.input_text)
    async with INFERENCE_SEMAPHORE:
        try:
            output_text = await asyncio.to_thread(
                model_manager.standardizer.inference, request.input_text
            )
            return {"standard_tamil": output_text}
        except Exception as e:
            logger.exception(f"Error in /colloquial_to_standard: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing input: {e}")


@app.post("/api/v1/upload-extract")
async def upload_extract_endpoint(file: UploadFile = File(...)):
    """Extracts text from uploaded .txt, .docx, or .pdf files."""
    text, message = await extract_text_from_upload(file)
    _validate_input_length(text)
    return {"text": text, "message": message, "filename": file.filename}


@app.post("/api/v1/export-docx")
async def export_docx_endpoint(request: ExportDocxRequest):
    """Generates a downloadable Word (.docx) document from normalized text."""
    buf = create_docx_bytes(request.text)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="iyal_normalized_output.docx"'},
    )


# =====================================================================
# Protected English Corpus Endpoints (Step 5 of Pipeline)
# =====================================================================
@app.get("/api/v1/protected-words")
def list_protected_words(db: Session = Depends(get_db)):
    rows = db.query(ProtectedWord).order_by(ProtectedWord.word.asc()).all()
    return {
        "words": [
            {
                "id": r.id,
                "word": r.word,
                "skip_translation": r.skip_translation,
                "added_by": r.added_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@app.post("/api/v1/protected-words")
def add_public_protected_word(
    req: ProtectedWordCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Allows users or admins to register custom English/proper-noun words not to transliterate."""
    clean_word = req.word.strip().lower()
    if not clean_word or " " in clean_word:
        raise HTTPException(
            status_code=400,
            detail="Please provide a single valid word without spaces.",
        )
    existing = db.query(ProtectedWord).filter(ProtectedWord.word == clean_word).first()
    if existing:
        return {"id": existing.id, "word": existing.word, "already_exists": True}

    entry = ProtectedWord(
        word=clean_word,
        skip_translation=req.skip_translation,
        added_by="ui_user",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    _sync_protected_words(db)
    return {"id": entry.id, "word": entry.word, "already_exists": False}


# =====================================================================
# Public Feedback Submission Endpoint
# =====================================================================
@app.post("/api/v1/feedback")
@app.post("/feedback/")
def submit_feedback_endpoint(
    req: FeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Stores user feedback in the database for review in /admin."""
    client_ip = security_engine.get_client_ip(request)
    output_payload = req.output if req.output is not None else {}
    if not isinstance(output_payload, (dict, list)):
        output_payload = {"output": str(output_payload)}

    fb = Feedback(
        created_at=datetime.datetime.now(datetime.timezone.utc),
        category=(req.category or "general").strip()[:64],
        rating=req.rating,
        input_text=req.input_text,
        output=output_payload,
        feedback=req.feedback.strip(),
        status="new",
        client_ip=client_ip,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    record_audit_log(
        db,
        event_type="feedback_submitted",
        actor=client_ip,
        details=f"Feedback #{fb.id} submitted under category '{fb.category}'",
        level="INFO",
    )
    return {"success": True, "id": fb.id, "message": "Thank you! Your feedback has been recorded."}


# =====================================================================
# Authentication Endpoints (/api/v1/auth/*)
# =====================================================================
@app.get("/api/v1/auth/config")
def get_auth_config():
    return {
        "google_oauth_enabled": bool(settings.GOOGLE_CLIENT_ID),
        "google_client_id": settings.GOOGLE_CLIENT_ID,
    }


@app.post("/api/v1/auth/login")
def admin_login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = security_engine.get_client_ip(request)
    identifier = req.identifier.strip().lower()

    # Check brute-force lockout before querying credentials
    security_engine.check_login_allowed(client_ip, identifier)

    user = (
        db.query(AdminUser)
        .filter((AdminUser.email == identifier) | (AdminUser.username == identifier))
        .first()
    )

    if not user or not verify_password(req.password, user.password_hash):
        remaining = security_engine.record_login_failure(client_ip, identifier)
        record_audit_log(
            db,
            event_type="auth_login_failed",
            actor=f"{identifier} ({client_ip})",
            details=f"Invalid credentials. Remaining attempts before lockout: {remaining}",
            level="SECURITY",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid username/email or password. ({remaining} attempt(s) remaining before temporary lockout).",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This admin account has been deactivated by the superadmin.",
        )

    security_engine.record_login_success(client_ip, identifier)
    user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    token = create_access_token(user)
    response.set_cookie(
        key="iyal_admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_HOURS * 3600,
    )
    record_audit_log(
        db,
        event_type="auth_login_success",
        actor=user.email,
        details=f"Admin '{user.username}' ({user.role}) logged in from {client_ip}",
        level="INFO",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
        },
    }


@app.post("/api/v1/auth/google")
def admin_google_login(
    req: GoogleLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticates an invited Gmail admin or superadmin using a Google OAuth2 ID Token.
    """
    client_ip = security_engine.get_client_ip(request)
    security_engine.check_login_allowed(client_ip, "google_oauth")

    info = verify_google_id_token(req.id_token)
    email = info["email"].strip().lower()

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not user:
        security_engine.record_login_failure(client_ip, email)
        record_audit_log(
            db,
            event_type="auth_google_uninvited",
            actor=f"{email} ({client_ip})",
            details="Uninvited Google account attempted /admin login.",
            level="SECURITY",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Gmail account '{email}' is not invited as an administrator. Ask the Superadmin to invite your Gmail first.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This admin account has been deactivated.",
        )

    security_engine.record_login_success(client_ip, email)
    user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    user.invite_token = None  # Clear invite token once signed in via Google
    db.commit()

    token = create_access_token(user)
    response.set_cookie(
        key="iyal_admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_HOURS * 3600,
    )
    record_audit_log(
        db,
        event_type="auth_google_login_success",
        actor=user.email,
        details=f"Admin '{user.email}' ({user.role}) signed in via Google OAuth from {client_ip}",
        level="INFO",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
        },
    }


@app.post("/api/v1/auth/accept-invite")
def accept_admin_invite(
    req: AcceptInviteRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Allows an invited Gmail admin to activate their password using their one-time invite token."""
    client_ip = security_engine.get_client_ip(request)
    email = req.email.strip().lower()
    security_engine.check_login_allowed(client_ip, email)

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if (
        not user
        or not user.invite_token
        or not secrets.compare_digest(user.invite_token, req.invite_token.strip())
    ):
        security_engine.record_login_failure(client_ip, email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or invitation token.",
        )

    user.password_hash = hash_password(req.new_password)
    user.invite_token = None
    user.is_active = True
    user.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    token = create_access_token(user)
    response.set_cookie(
        key="iyal_admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_HOURS * 3600,
    )
    record_audit_log(
        db,
        event_type="auth_invite_accepted",
        actor=user.email,
        details=f"Invited admin '{user.email}' activated account from {client_ip}",
        level="INFO",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
        },
    }


@app.post("/api/v1/auth/logout")
def admin_logout(response: Response):
    response.delete_cookie("iyal_admin_token")
    return {"success": True}


@app.get("/api/v1/auth/me")
def get_me(current_user: AdminUser = Depends(get_current_admin)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


# =====================================================================
# Admin Feedback Management Endpoints (Admin & Superadmin)
# =====================================================================
@app.get("/api/v1/admin/feedback")
def admin_list_feedback(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Feedback)
    if status_filter and status_filter != "all":
        q = q.filter(Feedback.status == status_filter)
    if category and category != "all":
        q = q.filter(Feedback.category == category)

    total = db.query(Feedback).count()
    new_count = db.query(Feedback).filter(Feedback.status == "new").count()
    resolved_count = db.query(Feedback).filter(Feedback.status == "resolved").count()
    items = q.order_by(desc(Feedback.created_at)).limit(min(limit, 500)).all()

    return {
        "summary": {
            "total": total,
            "new": new_count,
            "resolved": resolved_count,
        },
        "items": [
            {
                "id": f.id,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "category": f.category,
                "rating": f.rating,
                "input_text": f.input_text,
                "output": f.output,
                "feedback": f.feedback,
                "status": f.status,
                "admin_notes": f.admin_notes,
                "client_ip": f.client_ip,
            }
            for f in items
        ],
    }


@app.patch("/api/v1/admin/feedback/{feedback_id}")
def admin_update_feedback(
    feedback_id: int,
    req: UpdateFeedbackStatusRequest,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback entry not found.")
    fb.status = req.status
    if req.admin_notes is not None:
        fb.admin_notes = req.admin_notes
    db.commit()
    record_audit_log(
        db,
        event_type="feedback_updated",
        actor=current_user.email,
        details=f"Feedback #{feedback_id} marked as '{req.status}'",
        level="INFO",
    )
    return {"success": True, "id": fb.id, "status": fb.status, "admin_notes": fb.admin_notes}


@app.delete("/api/v1/admin/feedback/{feedback_id}")
def admin_delete_feedback(
    feedback_id: int,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback entry not found.")
    db.delete(fb)
    db.commit()
    record_audit_log(
        db,
        event_type="feedback_deleted",
        actor=current_user.email,
        details=f"Deleted Feedback #{feedback_id}",
        level="WARNING",
    )
    return {"success": True}


# =====================================================================
# Admin Dynamic Dual-Model Management Endpoints (Admin & Superadmin)
# =====================================================================
@app.get("/api/v1/admin/models")
def admin_get_models(
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return model_manager.get_all_models_status(db)


@app.put("/api/v1/admin/models/{model_key}")
async def admin_update_model(
    model_key: str,
    req: UpdateModelConfigRequest,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Allows an Admin or Superadmin to switch 'classifier' or 'standardizer' between
    'default' (local model in venv) and 'custom' (custom hosted model URL or HF repo).
    """
    try:
        updated_status = await asyncio.to_thread(
            model_manager.update_model_config,
            db,
            model_key,
            req.mode,
            req.custom_url,
            req.api_key,
            current_user.email,
        )
        record_audit_log(
            db,
            event_type="model_config_updated",
            actor=current_user.email,
            details=f"Updated model '{model_key}' to mode='{req.mode}', custom_url='{req.custom_url}'",
            level="INFO",
        )
        return updated_status
    except Exception as e:
        logger.error(f"Failed to update model '{model_key}': {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/admin/models/{model_key}/test")
async def admin_test_model(
    model_key: str,
    req: TestModelRequest,
    current_user: AdminUser = Depends(get_current_admin),
):
    try:
        result = await asyncio.to_thread(
            model_manager.test_model, model_key, req.sample_input
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =====================================================================
# Admin Protected Corpus Management
# =====================================================================
@app.delete("/api/v1/admin/protected-words/{word_id}")
def admin_delete_protected_word(
    word_id: int,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    row = db.query(ProtectedWord).filter(ProtectedWord.id == word_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Protected word not found.")
    word_val = row.word
    db.delete(row)
    db.commit()
    _sync_protected_words(db)
    record_audit_log(
        db,
        event_type="protected_word_deleted",
        actor=current_user.email,
        details=f"Removed protected corpus word '{word_val}'",
    )
    return {"success": True}


# =====================================================================
# Superadmin-Only User Management Endpoints (Invite by Gmail, Manage Admins)
# =====================================================================
@app.get("/api/v1/admin/users")
def superadmin_list_users(
    current_user: AdminUser = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    users = db.query(AdminUser).order_by(AdminUser.id.asc()).all()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "has_pending_invite": bool(u.invite_token),
                "invite_token": u.invite_token,
                "invited_by": u.invited_by,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ]
    }


@app.post("/api/v1/admin/users/invite")
def superadmin_invite_admin(
    req: InviteAdminRequest,
    current_user: AdminUser = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """
    Allows the Superadmin to invite a new Admin by their Gmail (or institutional email) address.
    Generates both an invitation token and an optional temporary password so the invited admin
    can log in via Google OAuth2 OR via Email + Password / Invite Setup immediately.
    """
    email = req.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code=400, detail="Please enter a valid Gmail or email address."
        )

    username = (
        req.username.strip().lower()
        if req.username and req.username.strip()
        else email.split("@")[0] + "_" + secrets.token_hex(2)
    )

    if db.query(AdminUser).filter(AdminUser.email == email).first():
        raise HTTPException(
            status_code=400, detail=f"User with email '{email}' already exists."
        )
    if db.query(AdminUser).filter(AdminUser.username == username).first():
        username = f"{username}_{secrets.token_hex(2)}"

    temp_password = (
        req.temporary_password.strip()
        if req.temporary_password and req.temporary_password.strip()
        else f"Iyal@{secrets.token_hex(4)}"
    )
    invite_token = secrets.token_urlsafe(16)

    new_admin = AdminUser(
        email=email,
        username=username,
        password_hash=hash_password(temp_password),
        role=req.role if req.role in ("admin", "superadmin") else "admin",
        is_active=True,
        invite_token=invite_token,
        invited_by=current_user.email,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    record_audit_log(
        db,
        event_type="admin_invited",
        actor=current_user.email,
        details=f"Superadmin invited '{email}' with role '{new_admin.role}'",
        level="INFO",
    )

    return {
        "success": True,
        "user": {
            "id": new_admin.id,
            "email": new_admin.email,
            "username": new_admin.username,
            "role": new_admin.role,
            "invite_token": invite_token,
            "temporary_password": temp_password,
            "invited_by": new_admin.invited_by,
        },
        "message": (
            f"Admin '{email}' invited! They can sign in via Google OAuth with {email}, "
            f"use temporary password '{temp_password}', or activate with invite token '{invite_token}'."
        ),
    }


@app.patch("/api/v1/admin/users/{user_id}")
def superadmin_update_user(
    user_id: int,
    req: UpdateAdminUserRequest,
    current_user: AdminUser = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    if target.id == current_user.id and req.is_active is False:
        raise HTTPException(
            status_code=400, detail="You cannot deactivate your own superadmin account."
        )
    if target.id == current_user.id and req.role and req.role != "superadmin":
        raise HTTPException(
            status_code=400, detail="You cannot demote your own superadmin account."
        )

    if req.is_active is not None:
        target.is_active = req.is_active
    if req.role in ("admin", "superadmin"):
        target.role = req.role
    if req.new_password and len(req.new_password.strip()) >= 6:
        target.password_hash = hash_password(req.new_password.strip())
        target.invite_token = None

    db.commit()
    record_audit_log(
        db,
        event_type="admin_user_updated",
        actor=current_user.email,
        details=f"Updated admin user '{target.email}' (active={target.is_active}, role={target.role})",
        level="INFO",
    )
    return {"success": True}


@app.delete("/api/v1/admin/users/{user_id}")
def superadmin_delete_user(
    user_id: int,
    current_user: AdminUser = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Admin user not found.")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own superadmin account."
        )
    email = target.email
    db.delete(target)
    db.commit()
    record_audit_log(
        db,
        event_type="admin_user_deleted",
        actor=current_user.email,
        details=f"Deleted admin user '{email}'",
        level="WARNING",
    )
    return {"success": True}


# =====================================================================
# Observability, Audit Logs & Security Telemetry (/api/v1/admin/observability)
# =====================================================================
@app.get("/api/v1/admin/observability")
def admin_observability_dashboard(
    log_level: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    proc = psutil.Process(os.getpid())
    mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
    cpu_pct = psutil.cpu_percent(interval=None)
    uptime_s = round(time.time() - STARTUP_TIME, 1)

    audit_entries = (
        db.query(AuditLog).order_by(desc(AuditLog.timestamp)).limit(100).all()
    )

    return {
        "system": {
            "uptime_seconds": uptime_s,
            "process_memory_mb": mem_mb,
            "cpu_percent": cpu_pct,
            "pid": os.getpid(),
            "database_engine": "SQLite (WAL Mode)" if "sqlite" in settings.DATABASE_URL else "PostgreSQL",
        },
        "security": security_engine.get_security_stats(),
        "models": model_manager.get_all_models_status(db),
        "audit_logs": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "level": a.level,
                "event_type": a.event_type,
                "actor": a.actor,
                "details": a.details,
            }
            for a in audit_entries
        ],
        "app_logs": get_recent_logs(limit=120, level=log_level),
    }


@app.post("/api/v1/admin/security/unban-ip")
def admin_unban_ip(
    req: UnbanIpRequest,
    current_user: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    removed = security_engine.unban_ip(req.ip.strip())
    record_audit_log(
        db,
        event_type="security_ip_unbanned",
        actor=current_user.email,
        details=f"Cleared IP ban/lockout state for {req.ip}",
        level="INFO",
    )
    return {"success": True, "was_banned": removed}
