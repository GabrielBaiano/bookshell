from googleapiclient.discovery import build
try:
    from .drive import get_drive_service
except ImportError:
    from drive import get_drive_service

def get_drive_service_object():
    """Returns the Google Drive service object ready for use."""
    creds = get_drive_service()
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(folder_name="Bookshell_Files"):
    """
    Checks if the folder already exists on Drive. If not, creates a new one.
    Returns the folder ID.
    """
    service = get_drive_service_object()
    if not service:
        return None

    # Procura pela pasta
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(
        q=query, 
        spaces='drive', 
        fields='nextPageToken, files(id, name)'
    ).execute()
    
    items = results.get('files', [])

    if not items:
        print(f"Folder '{folder_name}' not found. Creating...")
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'folderColorRgb': '#ff5252'  # Cor vermelha
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = file.get('id')
        print(f"Folder created successfully! ID: {folder_id}")
    else:
        folder_id = items[0].get('id')
        # Ensure the color is red even if the folder already exists
        service.files().update(
            fileId=folder_id,
            body={'folderColorRgb': '#ff5252'},
            fields='id'
        ).execute()

    return folder_id

if __name__ == "__main__":
    print("Starting folder verification on Google Drive...")
    folder_id = get_or_create_folder()
    if folder_id:
        print(f"All set to use folder {folder_id}")
    else:
        print("Error configuring folder on Drive.")
