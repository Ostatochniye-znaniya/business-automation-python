import logging


def configure_logging(level: str) -> None:
    logging.getLogger().setLevel(level.upper())
    logging.basicConfig(
        level=level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
