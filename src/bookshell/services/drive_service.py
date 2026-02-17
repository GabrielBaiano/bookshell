from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

from bookshell.core.drive import get_drive_service
from bookshell.core.models import Book, BookStatus
from bookshell.core.database_manager import get_config

class DriveService:
    def __init__(self):
        self.creds = get_drive_service()
        self.service = build('drive', 'v3', credentials=self.creds) if self.creds else None
        self.root_folder_id = get_config("root_folder_id")

    def is_connected(self) -> bool:
        return self.service is not None

    def _get_subfolders(self) -> dict:
        """Returns a map of {folder_id: folder_name} for immediate subfolders."""
        if not self.service or not self.root_folder_id:
            return {}

        query = f"'{self.root_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = []
        page_token = None
        while True:
            response = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token
            ).execute()
            results.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        return {f['id']: f['name'] for f in results}

    def list_books(self) -> list[Book]:
        """Lists all books in the Bookshell folder."""
        if not self.is_connected() or not self.root_folder_id:
            return []

        folder_map = self._get_subfolders()
        
        # Files in root
        books = self._list_files_in_folder(self.root_folder_id)
        
        # Files in subfolders
        for folder_id, category_name in folder_map.items():
            sub_books = self._list_files_in_folder(folder_id)
            for b in sub_books:
                b.category = category_name
            books.extend(sub_books)
            
        return books

    def _list_files_in_folder(self, folder_id: str) -> list[Book]:
        query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        results = []
        page_token = None
        while True:
            response = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, size, description)",
                pageToken=page_token
            ).execute()
            results.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        books = []
        for f in results:
            status = BookStatus.NEW
            desc = f.get('description', '')
            if desc:
                if '[reading]' in desc: status = BookStatus.READING
                elif '[finished]' in desc: status = BookStatus.FINISHED
            
            books.append(Book(
                name=f['name'],
                size=int(f.get('size', 0)),
                drive_id=f['id'],
                status=status,
                description=desc
            ))
        return books

    def upload_book(self, local_path: str, category: str = None) -> str:
        if not self.is_connected():
            return None

        path = Path(local_path)
        if not path.exists():
            return None

        target_folder = self.root_folder_id
        if category:
            target_folder = self.get_or_create_subfolder(category)

        file_metadata = {
            'name': path.name,
            'parents': [target_folder]
        }
        
        mime_type = 'application/pdf' if path.suffix.lower() == '.pdf' else 'application/epub+zip'
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)
        
        file = self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        return file.get('id')

    def download_book(self, drive_id: str, local_path: str) -> bool:
        if not self.is_connected():
            return False

        try:
            request = self.service.files().get_media(fileId=drive_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()

            with open(local_path, 'wb') as f:
                f.write(fh.getbuffer())
            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False

    def get_or_create_subfolder(self, name: str) -> str:
        if not self.is_connected(): return None
        
        query = f"name = '{name}' and '{self.root_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        items = results.get('files', [])

        if not items:
            metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.root_folder_id]
            }
            file = self.service.files().create(body=metadata, fields='id').execute()
            return file.get('id')
        
        return items[0].get('id')

    def setup_root_folder(self, folder_name="Bookshell_Files") -> str:
        # Similar to get_or_create_folder in legacy code but designed for setup
        if not self.service: return None
        
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        items = results.get('files', [])

        if not items:
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'folderColorRgb': '#ff5252'
            }
            file = self.service.files().create(body=metadata, fields='id').execute()
            return file.get('id')
        
        return items[0].get('id')

    def update_description(self, drive_id: str, description: str):
        if not self.is_connected(): return
        self.service.files().update(fileId=drive_id, body={'description': description}).execute()

    def set_visibility(self, drive_id: str, public: bool) -> str:
        if not self.is_connected(): return None
        if public:
            try:
                self.service.permissions().create(
                    fileId=drive_id,
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
            except: pass
            return self.service.files().get(fileId=drive_id, fields='webViewLink').execute().get('webViewLink')
        else:
            # Revoke public access
            perms = self.service.permissions().list(fileId=drive_id).execute().get('permissions', [])
            for p in perms:
                if p.get('type') == 'anyone':
                    self.service.permissions().delete(fileId=drive_id, permissionId=p['id']).execute()
            return "private"

    def delete_book(self, drive_id: str) -> bool:
        if not self.is_connected(): return False
        try:
            self.service.files().update(fileId=drive_id, body={'trashed': True}).execute()
            return True
        except: return False
    
    def move_book(self, drive_id: str, new_category: str):
         # Get current parents? Or just remove all and add new?
         # "removeParents" needs exact parent ID.
         # For simplicity, we get current parents first.
         file = self.service.files().get(fileId=drive_id, fields='parents').execute()
         prev_parents = ",".join(file.get('parents', []))
         
         target_folder = self.get_or_create_subfolder(new_category)
         
         self.service.files().update(
             fileId=drive_id,
             addParents=target_folder,
             removeParents=prev_parents
         ).execute()
