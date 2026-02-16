from googleapiclient.discovery import build
try:
    from .drive import get_drive_service
except ImportError:
    from drive import get_drive_service

def get_drive_service_object():
    """Retorna o objeto de serviço do Google Drive pronto para uso."""
    creds = get_drive_service()
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(folder_name="Bookshell_Files"):
    """
    Verifica se a pasta já existe no Drive. Se não, cria uma nova.
    Retorna o ID da pasta.
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
        print(f"Pasta '{folder_name}' não encontrada. Criando...")
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'folderColorRgb': '#ff5252'  # Cor vermelha
        }
        file = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = file.get('id')
        print(f"Pasta criada com sucesso! ID: {folder_id}")
    else:
        folder_id = items[0].get('id')
        print(f"Pasta encontrada! Garantindo que a cor seja vermelha...")
        # Atualiza a cor mesmo que a pasta já exista
        service.files().update(
            fileId=folder_id,
            body={'folderColorRgb': '#ff5252'},
            fields='id'
        ).execute()
        print(f"Pasta ID: {folder_id} atualizada para vermelho.")

    return folder_id

if __name__ == "__main__":
    print("Iniciando verificação de pasta no Google Drive...")
    folder_id = get_or_create_folder()
    if folder_id:
        print(f"Tudo pronto para usar a pasta {folder_id}")
    else:
        print("Erro ao configurar a pasta no Drive.")
