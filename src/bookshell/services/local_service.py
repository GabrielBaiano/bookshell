from pathlib import Path
import shutil
import os
from bookshell.core.database_manager import get_config
from bookshell.core.models import Book

class LocalService:
    def __init__(self):
        self.local_path_str = get_config("local_path")
        self.local_path = Path(self.local_path_str) if self.local_path_str else None

    def list_books(self) -> list[Book]:
        if not self.local_path or not self.local_path.exists():
            return []

        books = []
        for ext in ['*.pdf', '*.epub']:
            for file_path in self.local_path.rglob(ext):
                category = None
                try:
                    relative = file_path.relative_to(self.local_path)
                    if len(relative.parts) > 1:
                        category = relative.parts[0]
                except ValueError:
                    pass

                books.append(Book(
                    name=file_path.name,
                    local_path=str(file_path),
                    size=file_path.stat().st_size,
                    category=category
                ))
        return sorted(books, key=lambda x: x.name)

    def resolve_category(self, path: Path) -> str:
        """Determines category based on local folder structure."""
        if not self.local_path: return None
        try:
            relative = path.relative_to(self.local_path)
            if len(relative.parts) > 1:
                return relative.parts[0]
        except ValueError:
            pass
        return None

    def create_category_folder(self, category: str):
        if not self.local_path: return
        (self.local_path / category).mkdir(parents=True, exist_ok=True)

    def move_book(self, book: Book, new_category: str) -> str:
        if not self.local_path: return None
        
        target_dir = self.local_path / new_category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        source = Path(book.local_path)
        destination = target_dir / source.name
        
        shutil.move(str(source), str(destination))
        return str(destination)

    def delete_book(self, book: Book) -> bool:
        if not book.local_path: return False
        try:
            os.remove(book.local_path)
            return True
        except: return False
