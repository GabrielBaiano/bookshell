import os
from pathlib import Path
from .database_manager import get_config

def list_local_files():
    """
    Scans the configured local Bookshell folder for PDF and EPUB files.
    """
    local_path_str = get_config("local_path")
    if not local_path_str:
        return []
    
    local_path = Path(local_path_str)
    if not local_path.exists():
        return []

    books = []
    # Supporting PDF and EPUB
    for ext in ['*.pdf', '*.epub']:
        for file_path in local_path.glob(ext):
            books.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
            
    return sorted(books, key=lambda x: x["name"])
