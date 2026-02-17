from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from bookshell.core.models import Book

class BaseReader(ABC):
    """Base class for all ebook readers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name of the reader."""
        pass

    @property
    @abstractmethod
    def install_command(self) -> str:
        """The command to install the reader."""
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if the reader is installed."""
        pass

    @abstractmethod
    def open_book(self, book_path: str) -> bool:
        """Open a book with this reader."""
        pass

    @abstractmethod
    def get_progress(self, book_path: str) -> int:
        """
        Retrieve reading progress (0-100) from the reader's local data.
        If not supported or not found, return 0.
        """
        pass

    @abstractmethod
    def set_progress(self, book_path: str, progress: int) -> bool:
        """
        Set reading progress (0-100) in the reader's local data.
        Returns True if successful.
        """
        pass
