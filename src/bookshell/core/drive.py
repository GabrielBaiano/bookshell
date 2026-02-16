import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Escopo: Acesso apenas aos arquivos que o Bookshell criar (Segurança máxima)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """
    Autentica o usuário e retorna as credenciais do Google Drive.
    """
    creds = None
    # O token.json guarda as permissões de acesso já concedidas
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não houver credenciais válidas, pede o login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Erro: Arquivo 'credentials.json' não encontrado na raiz!")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para a próxima vez
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def sync_drive():
    """
    Sincroniza os livros locais com o Google Drive.
    """
    creds = get_drive_service()
    if creds:
        print("Conexão com o Drive estabelecida com sucesso!")
        # Lógica de sincronização futura aqui
    else:
        print("Falha ao sincronizar com o Google Drive.")

if __name__ == "__main__":
    sync_drive()
