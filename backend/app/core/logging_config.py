import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if settings.CLOUDWATCH_LOG_GROUP:
        cloudwatch_handler = _build_cloudwatch_handler(settings.CLOUDWATCH_LOG_GROUP)
        if cloudwatch_handler is not None:
            cloudwatch_handler.setFormatter(formatter)
            root.addHandler(cloudwatch_handler)


def _build_cloudwatch_handler(log_group: str) -> logging.Handler | None:
    try:
        import boto3
        import watchtower
    except ImportError:
        logger.warning(
            "CLOUDWATCH_LOG_GROUP is set but watchtower/boto3 aren't installed; "
            "skipping CloudWatch log streaming."
        )
        return None

    try:
        boto3_client = boto3.client("logs", region_name=settings.AWS_REGION)
        return watchtower.CloudWatchLogHandler(
            log_group_name=log_group,
            log_stream_name=settings.CLOUDWATCH_LOG_STREAM
            or f"{settings.PROJECT_NAME}-{settings.ENVIRONMENT}",
            boto3_client=boto3_client,
            create_log_group=True,
        )
    except Exception:
        logger.warning(
            "Failed to initialize CloudWatch log handler; continuing without it.",
            exc_info=True,
        )
        return None
