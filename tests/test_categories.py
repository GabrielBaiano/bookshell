from bookshell.services.drive_service import DriveService
from bookshell.core.database_manager import get_config

print(f"DEBUG: root_folder_id = {get_config('root_folder_id')}")
service = DriveService()
files = service.list_books()
print(f"DEBUG: Found {len(files)} files on Drive.")
for f in files:
    print(f" - {f.name} | Category: {f.category}")
