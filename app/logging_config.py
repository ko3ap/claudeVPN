import logging


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Silence noisy third-party loggers unless something goes wrong.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
