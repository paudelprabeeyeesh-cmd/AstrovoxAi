import logging
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)


class UnicodeNormalizer:
    def __init__(self, form: str = "NFKC"):
        self.form = form
        logger.info("Unicode normalizer initialized with form %s", self.form)

    def normalize(self, text: str) -> str:
        return unicodedata.normalize(self.form, text)

    def is_safe(self, text: str) -> bool:
        try:
            text.encode("utf-8")
            return True
        except UnicodeEncodeError:
            return False
