import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Routes stdlib logging records (Flask, Werkzeug, gunicorn, SQLAlchemy)
    through loguru so the whole app logs through a single sink."""

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(app):
    level = app.config.get("LOG_LEVEL", "INFO")

    logger.remove()
    logger.add(sys.stderr, level=level, backtrace=False, diagnose=app.debug)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("werkzeug", "gunicorn.error", "gunicorn.access", "sqlalchemy"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.propagate = False

    app.logger.handlers = [InterceptHandler()]
    app.logger.propagate = False
