import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Project IYAL — Tamil Input Text Normalizer"
    VERSION: str = "2.0.0"

    # Server
    HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    # Database (Defaults to zero-cost embedded SQLite in ./data/iyal.db; supports PostgreSQL via DATABASE_URL)
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.getenv('DATA_DIR', os.path.join(os.getcwd(), 'data')), 'iyal.db')}",
    )

    # Predefined Superadmin Credentials
    SUPERADMIN_EMAIL: str = os.getenv("SUPERADMIN_EMAIL", "superadmin@gmail.com")
    SUPERADMIN_USERNAME: str = os.getenv("SUPERADMIN_USERNAME", "superadmin")
    SUPERADMIN_PASSWORD: str = os.getenv("SUPERADMIN_PASSWORD", "IyalAdmin@2026")

    # Authentication & Google OAuth2
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "12"))
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")

    # ResearchGate Paper URL, GitHub Repository URL & HuggingFace Hub Token
    RESEARCHGATE_PAPER_URL: str = os.getenv(
        "RESEARCHGATE_PAPER_URL",
        "https://www.researchgate.net/publication/397403935_IYAL_Input_Text_Normalizer_for_Tamil_Language",
    )
    GITHUB_REPO_URL: str = os.getenv(
        "GITHUB_REPO_URL", "https://github.com/Sanujen/Project-IYAL"
    )
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # DDoS, Rate Limiting & Brute-Force Protection
    RATE_LIMIT_GENERAL_PER_MIN: int = int(os.getenv("RATE_LIMIT_GENERAL_PER_MIN", "120"))
    RATE_LIMIT_INFERENCE_PER_MIN: int = int(os.getenv("RATE_LIMIT_INFERENCE_PER_MIN", "30"))
    RATE_LIMIT_FEEDBACK_PER_MIN: int = int(os.getenv("RATE_LIMIT_FEEDBACK_PER_MIN", "10"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "900"))
    IP_BAN_VIOLATION_THRESHOLD: int = int(os.getenv("IP_BAN_VIOLATION_THRESHOLD", "10"))
    IP_BAN_DURATION_SECONDS: int = int(os.getenv("IP_BAN_DURATION_SECONDS", "600"))

    # Payload & Concurrency Guards
    MAX_INPUT_CHARS: int = int(os.getenv("MAX_INPUT_CHARS", "15000"))
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    MAX_CONCURRENT_INFERENCES: int = int(os.getenv("MAX_CONCURRENT_INFERENCES", "4"))

    def get_researchgate_url(self) -> str:
        load_dotenv(override=True)
        url = os.getenv("RESEARCHGATE_PAPER_URL", self.RESEARCHGATE_PAPER_URL).strip()
        return url or "https://www.researchgate.net/publication/397403935_IYAL_Input_Text_Normalizer_for_Tamil_Language"

    def get_github_url(self) -> str:
        load_dotenv(override=True)
        url = os.getenv("GITHUB_REPO_URL", self.GITHUB_REPO_URL).strip()
        return url or "https://github.com/Sanujen/Project-IYAL"


settings = Settings()
