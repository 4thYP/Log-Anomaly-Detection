from abc import ABC, abstractmethod
from typing import Dict


class BaseParser(ABC):
    """
    Abstract base class for all log parsers
    """

    @abstractmethod
    def parse(self, message: str) -> Dict:
        pass
