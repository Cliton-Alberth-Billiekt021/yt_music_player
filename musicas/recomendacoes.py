import re
import requests

def extrair_artistas_e_feat(titulo):
    """
    Identifica participações (feats) no título da música.
    Exemplo: "Artista A feat. Artista B - Musica"
    """
    padrao = r'(?i)(?:feat\.?|ft\.?|participação|part\.|with)\s+([\w\s&]+)'
    feats = re.findall(padrao, titulo)
    
    # Limpa nomes de artistas encontrados
    artistas_relacionados = [f.strip() for f in feats]
    return artistas_relacionados

def buscar_sugestoes_estilo(nome_artista, titulo_musica):
    """
    Busca músicas semelhantes e do mesmo estilo usando a API pública do Deezer.
    """
    sugestoes = []
    try:
        # Busca a faixa principal para pegar o ID do gênero/estilo
        url_busca = f"https://api.deezer.com/search?q={nome_artista} {titulo_musica}&limit=1"
        res = requests.get(url_busca, timeout=5).json()
        
        if res.get('data'):
            artist_id = res['data'][0]['artist']['id']
            
            # Busca faixas relacionadas/populares do mesmo artista e parceiros
            url_relacionadas = f"https://api.deezer.com/artist/{artist_id}/related?limit=3"
            res_rel = requests.get(url_relacionadas, timeout=5).json()
            
            for artista in res_rel.get('data', []):
                # Pega a música mais popular de cada artista recomendado
                top_tracks = requests.get(f"https://api.deezer.com/artist/{artista['id']}/top?limit=1", timeout=5).json()
                if top_tracks.get('data'):
                    track = top_tracks['data'][0]
                    sugestoes.append({
                        'titulo': track['title'],
                        'artista': track['artist']['name'],
                        'capa': track['album']['cover_medium'],
                        'termo_busca': f"{track['artist']['name']} {track['title']}"
                    })
    except Exception as e:
        print(f"Erro ao buscar recomendações: {e}")
        
    return sugestoes