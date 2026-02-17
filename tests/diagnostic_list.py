from bookshell.services.drive_service import DriveService
from bookshell.core.database_manager import get_config

drive_service = DriveService()
service = drive_service.service
root_id = get_config("root_folder_id")
print(f"Root Folder ID: {root_id}")

if not service:
    print("Failed to connect to Drive.")
    exit(1)

# 1. List subfolders
query_folders = f"'{root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
folders = service.files().list(q=query_folders, fields="files(id, name)").execute().get('files', [])
print("Subfolders (Categories):")
for f in folders:
    print(f" - {f['name']} (ID: {f['id']})")

# 2. List all files
query_files = f"trashed = false and mimeType != 'application/vnd.google-apps.folder'"
files = service.files().list(q=query_files, fields="files(id, name, parents)").execute().get('files', [])
print("\nFiles on Drive:")
for f in files:
    print(f" - {f['name']} (Parents: {f.get('parents')})")
