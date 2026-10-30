import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from server.database import Base


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="admin")  # "superadmin" or "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    invite_token = Column(String(128), nullable=True, index=True)
    invited_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    last_login_at = Column(DateTime, nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    category = Column(String(64), nullable=False, default="general")
    rating = Column(Integer, nullable=True)
    input_text = Column(Text, nullable=True)
    output = Column(JSON, nullable=False)
    feedback = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="new")  # "new", "reviewed", "resolved"
    admin_notes = Column(Text, nullable=True)
    client_ip = Column(String(64), nullable=True)


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_key = Column(String(64), unique=True, index=True, nullable=False)  # "classifier" | "standardizer"
    mode = Column(String(32), nullable=False, default="default")  # "default" | "custom"
    default_model_name = Column(String(255), nullable=False)
    custom_url = Column(String(512), nullable=True)
    api_key = Column(String(512), nullable=True)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow)


class ProtectedWord(Base):
    __tablename__ = "protected_words"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    word = Column(String(128), unique=True, index=True, nullable=False)
    skip_translation = Column(Boolean, nullable=False, default=True)
    added_by = Column(String(255), nullable=False, default="system")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=utcnow, index=True)
    level = Column(String(20), nullable=False, default="INFO")
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(255), nullable=False, default="system")
    details = Column(Text, nullable=False)

