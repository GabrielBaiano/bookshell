from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
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

def move_file(file_id, current_parents, new_parent_id):
    """
    Moves a file from one folder to another on Google Drive.
    """
    service = get_drive_service_object()
    if not service:
        return None
    
    # Retrieve the existing parents to remove
    previous_parents = ",".join(current_parents) if isinstance(current_parents, list) else current_parents
    
    # Move the file by adding the new parent and removing the old ones
    file = service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
    
    return file.get('parents')

def update_description(file_id, description):
    """
    Updates the description of a file on Google Drive.
    """
    service = get_drive_service_object()
    if not service:
        return None

    service.files().update(
        fileId=file_id,
        body={'description': description}
    ).execute()

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

def list_drive_files():
    """
    Lists all files in the Bookshell folder on Google Drive recursively.
    The name of the immediate subfolder is used as the category.
    """
    try:
        from .database_manager import get_config
    except ImportError:
        from database_manager import get_config
        
    folder_id = get_config("root_folder_id")
    
    if not folder_id:
        return []

    service = get_drive_service_object()
    if not service:
        return []

    # Helper for paginated list
    def list_all(query):
        items = []
        page_token = None
        while True:
            response = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, parents, description)",
                pageToken=page_token
            ).execute()
            items.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return items

    # 1. Get all immediate subfolders to use as categories
    query_folders = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    # Note: Using list_all for folders too, though fields need to match if we reuse helper. 
    # Let's adjust helper or just perform loop for folders separately if fields differ.
    
    folders = []
    page_token = None
    while True:
        response = service.files().list(
            q=query_folders,
            fields="nextPageToken, files(id, name)",
            pageToken=page_token
        ).execute()
        folders.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        if not page_token:
            break
            
    folder_map = {f['id']: f['name'] for f in folders}
    
    # 2. Get files in the root folder
    query_root = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
    files_root = list_all(query_root)

    # 3. Get files in each subfolder (Category)
    files_sub = []
    for sub_id, sub_name in folder_map.items():
        query_sub = f"'{sub_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        items = list_all(query_sub)
        for item in items:
            item['category'] = sub_name
        files_sub.extend(items)

    return files_root + files_sub

def get_or_create_subfolder(parent_id, subfolder_name):
    """
    Creates or finds a subfolder inside a parent folder on Google Drive.
    """
    service = get_drive_service_object()
    if not service:
        return None

    query = f"name = '{subfolder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields='files(id, name)').execute()
    items = results.get('files', [])

    if not items:
        file_metadata = {
            'name': subfolder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')
    
    return items[0].get('id')

def upload_book(file_path, category=None):
    """
    Uploads a file to the Bookshell folder on Google Drive, optionally in a category subfolder.
    """
    try:
        from .database_manager import get_config
    except ImportError:
        from database_manager import get_config
        
    folder_id = get_config("root_folder_id")
    if not folder_id:
        print("Error: Root folder ID not found in configuration.")
        return None

    service = get_drive_service_object()
    if not service:
        return None

    path = Path(file_path)
    if not path.exists():
        print(f"Error: File '{file_path}' not found.")
        return None

    # Determine target folder (root or category subfolder)
    target_folder_id = folder_id
    if category:
        target_folder_id = get_or_create_subfolder(folder_id, category)

    file_metadata = {
        'name': path.name,
        'parents': [target_folder_id]
    }
    
    # Determine mime type based on extension
    mime_type = 'application/pdf' if path.suffix.lower() == '.pdf' else 'application/epub+zip'
    
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)
    
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    return file.get('id')

def download_book(file_id, local_path):
    """
    Downloads a file from Google Drive to the specified local path.
    """
    try:
        from googleapiclient.http import MediaIoBaseDownload
        import io
    except ImportError:
        return False

    service = get_drive_service_object()
    if not service:
        return False

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        # You could report progress here if needed

    # Write to file
    with open(local_path, 'wb') as f:
        f.write(fh.getbuffer())
        
    return True

if __name__ == "__main__":
    print("Starting folder verification on Google Drive...")
    folder_id = get_or_create_folder()
    if folder_id:
        print(f"All set to use folder {folder_id}")
    else:
        print("Error configuring folder on Drive.")
