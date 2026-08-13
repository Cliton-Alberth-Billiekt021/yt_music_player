import requests

JAMENDO_CLIENT_ID = '56b4922f'  # Client ID de teste do Jamendo

def buscar_musicas_jamendo(termo_busca, limite=10):
    """
    Busca faixas no Jamendo e retorna links de download direto em MP3.
    """
    url = "https://api.jamendo.com/v3.0/tracks/"
    
    params = {
        'client_id': JAMENDO_CLIENT_ID,
        'format': 'json',
        'search': termo_busca,
        'limit': limite,
        'include': 'musicinfo',
        'audioformat': 'mp32' # MP3 de alta qualidade
    }
    
    resultados = []
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for track in data.get('results', []):
                resultados.append({
                    'id': track['id'],
                    'titulo': track['name'],
                    'artista': track['artist_name'],
                    'capa': track['image'] or track['album_image'],
                    'duracao': f"{track['duration'] // 60}:{track['duration'] % 60:02d}",
                    'download_url': track['audio'], # Link direto para download do MP3!
                    'fonte': 'jamendo'
                })
    except Exception as e:
        print(f"Erro ao buscar no Jamendo: {e}")
        
    return resultados