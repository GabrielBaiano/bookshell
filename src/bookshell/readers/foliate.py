import os
import subprocess
import json
import hashlib
from pathlib import Path
from typing import Optional
from bookshell.readers.base import BaseReader

class FoliateReader(BaseReader):
    """
    Foliate Reader implementation for Linux.
    
    To add a new reader:
    1. Create a new class inheriting from BaseReader.
    2. Implement all abstract methods.
    3. Register the reader in reader_manager.py.
    """

    @property
    def name(self) -> str:
        return "Foliate"

    @property
    def install_command(self) -> str:
        # Prefer flatpak if available, otherwise suggest apt
        return "flatpak install flathub com.github.johnfactotum.Foliate -y || sudo apt install foliate -y"

    def is_installed(self) -> bool:
        try:
            subprocess.run(["which", "foliate"], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            # Check flatpak
            try:
                result = subprocess.run(["flatpak", "info", "com.github.johnfactotum.Foliate"], capture_output=True)
                return result.returncode == 0
            except:
                return False

    def open_book(self, book_path: str) -> bool:
        try:
            # Try running as flatpak first, then direct
            try:
                subprocess.Popen(["flatpak", "run", "com.github.johnfactotum.Foliate", book_path])
            except:
                subprocess.Popen(["foliate", book_path])
            return True
        except Exception as e:
            print(f"Error opening Foliate: {e}")
            return False

    def _get_data_dir(self) -> Path:
        # Standard location
        std_path = Path.home() / ".local/share/com.github.johnfactotum.Foliate"
        if std_path.exists():
            return std_path
        
        # Flatpak location
        flatpak_path = Path.home() / ".var/app/com.github.johnfactotum.Foliate/data/com.github.johnfactotum.Foliate"
        return flatpak_path

    def _get_book_hash(self, book_path: str) -> str:
        """Foliate uses MD5 hash of the file if no internal ID is found."""
        hash_md5 = hashlib.md5()
        with open(book_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_progress(self, book_path: str) -> int:
        """
        Foliate stores progress in JSON files.
        This is a simplified attempt to extract a percentage.
        """
        data_dir = self._get_data_dir()
        if not data_dir.exists():
            return 0

        book_hash = self._get_book_hash(book_path)
        # Foliate uses 'foliate:' prefix for hashes
        json_file = data_dir / f"foliate-{book_hash}.json"
        
        if not json_file.exists():
            # Try without prefix or different naming convention if any
            json_file = data_dir / f"{book_hash}.json"
            if not json_file.exists():
                return 0

        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Foliate doesn't store a simple % but we can try to estimate
                # or just use the progress stored in Bookshell if preferred.
                # For now, let's return what's in 'progress' if it exists (hypothetical)
                return data.get("progress", 0) 
        except:
            return 0

    def set_progress(self, book_path: str, progress: int) -> bool:
        """
        Foliate might not support setting progress via external JSON easily 
        without matching its CFI exactly, so we just return False for now.
        Bookshell will track its own progress and sync it.
        """
        return False
