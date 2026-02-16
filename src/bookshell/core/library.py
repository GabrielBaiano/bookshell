import os
from pathlib import Path
from .database_manager import get_config

def list_local_files():
    """
    Scans the configured local Bookshell folder for PDF and EPUB files recursively.
    Subfolders are treated as categories.
    """
    local_path_str = get_config("local_path")
    if not local_path_str:
        return []
    
    local_path = Path(local_path_str)
    if not local_path.exists():
        return []

    books = []
    # Supporting PDF and EPUB recursively
    for ext in ['*.pdf', '*.epub']:
        for file_path in local_path.rglob(ext):
            # Category is the immediate subfolder inside the root path
            category = None
            try:
                relative = file_path.relative_to(local_path)
                if len(relative.parts) > 1:
                    category = relative.parts[0]
            except ValueError:
                pass

            books.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "category": category
            })
            
    return sorted(books, key=lambda x: x["name"])
