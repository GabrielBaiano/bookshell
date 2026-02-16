from bookshell.core.drive_logic import list_drive_files
from bookshell.core.database_manager import get_config

print(f"DEBUG: root_folder_id = {get_config('root_folder_id')}")
files = list_drive_files()
print(f"DEBUG: Found {len(files)} files on Drive.")
for f in files:
    print(f" - {f['name']} | Category: {f.get('category')}")
