import platform
from typing import List, Optional
from bookshell.readers.base import BaseReader
from bookshell.readers.foliate import FoliateReader
from bookshell.core.database_manager import get_config, save_config

class ReaderManager:
    def __init__(self):
        # Register available readers here
        self.available_readers: List[BaseReader] = [
            FoliateReader()
        ]

    def get_preferred_reader(self) -> Optional[BaseReader]:
        """Retrieve the configured reader from DB or pick the first installed one."""
        reader_name = get_config("preferred_reader")
        if reader_name:
            for r in self.available_readers:
                if r.name == reader_name:
                    return r
        
        # Default: pick first installed reader
        for r in self.available_readers:
            if r.is_installed():
                return r
        
        return None

    def set_preferred_reader(self, name: str):
        save_config("preferred_reader", name)

    def list_installed_readers(self) -> List[BaseReader]:
        return [r for r in self.available_readers if r.is_installed()]

    def list_available_readers(self) -> List[BaseReader]:
        # Filter by OS if necessary
        os_name = platform.system().lower()
        if os_name == "linux":
            return self.available_readers
        return [] # Foliate is Linux-only for now

    def open_with_reader(self, book_path: str, reader: Optional[BaseReader] = None) -> bool:
        if not reader:
            reader = self.get_preferred_reader()
        
        if reader:
            return reader.open_book(book_path)
        
        # Fallback to system default if no reader is configured/installed
        try:
            os_name = platform.system().lower()
            if os_name == "windows":
                os.startfile(book_path)
            elif os_name == "darwin":
                import subprocess
                subprocess.run(["open", book_path])
            else:
                import subprocess
                subprocess.run(["xdg-open", book_path])
            return True
        except:
            return False
