import datetime
import threading
from sqlalchemy.orm import Session
from iyal_quality_analyzer.inference_base.inference import Inference as ClassifierInference
from iyal_quality_analyzer.inference_base.inference_coll_to_stand import (
    Inference as StandardizerInference,
)
from server.models_db import ModelConfig
from iyal_quality_analyzer.utils.logger import setup_logging

logger = setup_logging("iyal.model_manager")


class ModelManager:
    """
    Manages the lifecycle and hot-reloading of Project IYAL's two models:
      1. 'classifier': Legacy vs. Romanized Tamil Classifier
         Default: 'sanujen/Tamil_Legacy_Roman_Classifier_V2' (or local cached 'sanujen/fyp_0')
      2. 'standardizer': Colloquial-to-Standard Tamil Standardizer
         Default: 'sanujen/mBART_Tamil_Colloquial_to_Standard'

    Admins can dynamically switch either model between 'default' (local venv/HF cache)
    and 'custom' (custom hosted URL or custom HuggingFace repo) via /admin.
    """

    DEFAULT_CLASSIFIER = "sanujen/Tamil_Legacy_Roman_Classifier_V2"
    DEFAULT_STANDARDIZER = "sanujen/mBART_Tamil_Colloquial_to_Standard"

    def __init__(self):
        self._lock = threading.Lock()
        self.classifier: ClassifierInference = None
        self.standardizer: StandardizerInference = None

    def initialize_from_db(self, db: Session, background_warmup: bool = True):
        """
        Seeds default model rows if missing and initializes both models.
        Uses non-blocking background warmup by default so the FastAPI server
        starts accepting HTTP requests immediately without hanging on startup.
        """
        with self._lock:
            clf_cfg = (
                db.query(ModelConfig)
                .filter(ModelConfig.model_key == "classifier")
                .first()
            )
            if not clf_cfg:
                clf_cfg = ModelConfig(
                    model_key="classifier",
                    mode="default",
                    default_model_name=self.DEFAULT_CLASSIFIER,
                    custom_url=None,
                    api_key=None,
                    updated_by="system_bootstrap",
                )
                db.add(clf_cfg)

            std_cfg = (
                db.query(ModelConfig)
                .filter(ModelConfig.model_key == "standardizer")
                .first()
            )
            if not std_cfg:
                std_cfg = ModelConfig(
                    model_key="standardizer",
                    mode="default",
                    default_model_name=self.DEFAULT_STANDARDIZER,
                    custom_url=None,
                    api_key=None,
                    updated_by="system_bootstrap",
                )
                db.add(std_cfg)

            db.commit()
            db.refresh(clf_cfg)
            db.refresh(std_cfg)

            self.classifier = ClassifierInference(
                model_name=clf_cfg.default_model_name,
                mode=clf_cfg.mode,
                custom_url=clf_cfg.custom_url,
                api_key=clf_cfg.api_key,
                defer_load=background_warmup,
            )

            self.standardizer = StandardizerInference(
                model_name=std_cfg.default_model_name,
                mode=std_cfg.mode,
                custom_url=std_cfg.custom_url,
                api_key=std_cfg.api_key,
                defer_load=background_warmup,
            )

            if background_warmup:
                def _warmup():
                    try:
                        logger.info("Background warmup: Initializing Classifier Model...")
                        self.classifier.ensure_loaded()
                        logger.info("Background warmup: Initializing Colloquial-to-Standard Model...")
                        self.standardizer.ensure_loaded()
                        logger.info("Background warmup: All models initialized and ready.")
                    except Exception as exc:
                        logger.error(f"Error during background model warmup: {exc}")

                threading.Thread(target=_warmup, daemon=True, name="iyal-model-warmup").start()

    def update_model_config(
        self,
        db: Session,
        model_key: str,
        mode: str,
        custom_url: str = None,
        api_key: str = None,
        updated_by: str = "admin",
    ) -> dict:
        """
        Updates the configuration for 'classifier' or 'standardizer', reloads the model,
        and persists the configuration in the database.
        """
        if model_key not in ("classifier", "standardizer"):
            raise ValueError(f"Unsupported model_key '{model_key}'. Must be 'classifier' or 'standardizer'.")
        if mode not in ("default", "custom"):
            raise ValueError("Mode must be 'default' or 'custom'.")
        if mode == "custom" and (not custom_url or not custom_url.strip()):
            raise ValueError("A valid custom_url is required when mode is set to 'custom'.")

        with self._lock:
            cfg = (
                db.query(ModelConfig)
                .filter(ModelConfig.model_key == model_key)
                .first()
            )
            if not cfg:
                raise ValueError(f"ModelConfig for '{model_key}' not found.")

            effective_api_key = api_key if api_key is not None else cfg.api_key

            if model_key == "classifier":
                new_instance = ClassifierInference(
                    model_name=cfg.default_model_name,
                    mode=mode,
                    custom_url=custom_url if mode == "custom" else None,
                    api_key=effective_api_key if mode == "custom" else None,
                )
                self.classifier = new_instance
            else:
                new_instance = StandardizerInference(
                    model_name=cfg.default_model_name,
                    mode=mode,
                    custom_url=custom_url if mode == "custom" else None,
                    api_key=effective_api_key if mode == "custom" else None,
                )
                self.standardizer = new_instance

            cfg.mode = mode
            cfg.custom_url = custom_url.strip() if (mode == "custom" and custom_url) else None
            if api_key is not None:
                cfg.api_key = api_key.strip() if api_key.strip() else None
            cfg.updated_by = updated_by
            cfg.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(cfg)

            logger.info(
                f"Model '{model_key}' updated by {updated_by}: mode={mode}, custom_url={cfg.custom_url}"
            )
            return self.get_model_status(db, model_key)

    def test_model(self, model_key: str, sample_input: str = None) -> dict:
        """Runs a diagnostic test inference on the specified model."""
        if model_key == "classifier":
            inp = sample_input or "tzf;fk;"
            output = self.classifier.inference(inp)
            return {
                "model_key": "classifier",
                "sample_input": inp,
                "sample_output": output,
                "info": self.classifier.get_info(),
            }
        elif model_key == "standardizer":
            inp = sample_input or "என்ன பண்றீங்க"
            output = self.standardizer.inference(inp)
            return {
                "model_key": "standardizer",
                "sample_input": inp,
                "sample_output": output,
                "info": self.standardizer.get_info(),
            }
        else:
            raise ValueError(f"Unknown model_key: {model_key}")

    def get_model_status(self, db: Session, model_key: str) -> dict:
        cfg = db.query(ModelConfig).filter(ModelConfig.model_key == model_key).first()
        instance = self.classifier if model_key == "classifier" else self.standardizer
        info = instance.get_info() if instance else {}
        if cfg:
            info["updated_by"] = cfg.updated_by
            info["updated_at"] = cfg.updated_at.isoformat() if cfg.updated_at else None
        return info

    def get_all_models_status(self, db: Session) -> dict:
        return {
            "classifier": self.get_model_status(db, "classifier"),
            "standardizer": self.get_model_status(db, "standardizer"),
        }


model_manager = ModelManager()
