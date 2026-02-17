from typing import List, Dict, Tuple
from bookshell.core.models import Book, BookStatus
from bookshell.services.drive_service import DriveService
from bookshell.services.local_service import LocalService

class SyncService:
    def __init__(self):
        self.drive_service = DriveService()
        self.local_service = LocalService()

    def get_library(self) -> List[Book]:
        """
        Merges local and drive books into a unified list.
        """
        local_books = self.local_service.list_books()
        drive_books = self.drive_service.list_books()

        library: Dict[str, Book] = {}

        # 1. Add Local Books
        for b in local_books:
            library[b.name] = b

        # 2. Add or Update with Drive Books
        for b in drive_books:
            if b.name in library:
                existing = library[b.name]
                existing.drive_id = b.drive_id
                existing.status = b.status
                # If local category is missing, use drive category
                if not existing.category:
                    existing.category = b.category
            else:
                library[b.name] = b

        return sorted(library.values(), key=lambda x: x.name)

    def get_diff(self) -> Tuple[List[Book], List[Book]]:
        """
        Returns (to_upload, to_download).
        to_upload: Books present locally but not on Drive.
        to_download: Books present on Drive but not locally.
        """
        library = self.get_library()
        to_upload = [b for b in library if b.is_local_only]
        to_download = [b for b in library if b.is_drive_only]
        return to_upload, to_download

    def sync_pull(self, book_name: str = None, all: bool = False) -> List[str]:
        """
        Downloads books from Drive.
        Returns list of successfully downloaded book names.
        """
        library = self.get_library()
        if book_name:
            target = next((b for b in library if b.name == book_name), None)
            targets = [target] if target else []
        elif all:
            targets = [b for b in library if b.is_drive_only]
        else:
            return []

        success_list = []
        for book in targets:
            if not book.drive_id: continue
            
            # Determine target path
            if not self.local_service.local_path: continue
            
            category = book.category or "General"
            target_dir = self.local_service.local_path / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / book.name
            
            if self.drive_service.download_book(book.drive_id, str(target_path)):
                success_list.append(book.name)
        
        return success_list

    def sync_push(self, book_name: str = None, all: bool = False) -> List[str]:
        """
        Uploads books to Drive.
        Returns list of successfully uploaded book names.
        """
        library = self.get_library()
        
        if book_name:
             target = next((b for b in library if b.name == book_name), None)
             targets = [target] if target else []
        elif all:
             targets = [b for b in library if b.is_local_only]
        else:
             return []

        success_list = []
        for book in targets:
            if not book.local_path: continue
            
            category = book.category
            # Upload
            drive_id = self.drive_service.upload_book(book.local_path, category)
            if drive_id:
                success_list.append(book.name)

        return success_list
