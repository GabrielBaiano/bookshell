import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Escopo: Acesso apenas aos arquivos que o Bookshell criar (Segurança máxima)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """
    Authenticates the user and returns Google Drive credentials.
    """
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: 'credentials.json' file not found in root!")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def sync_drive():
    """
    Synchronizes local books with Google Drive.
    """
    creds = get_drive_service()
    if creds:
        print("Drive connection established successfully!")
        # Future sync logic here
    else:
        print("Failed to sync with Google Drive.")

if __name__ == "__main__":
    sync_drive()
