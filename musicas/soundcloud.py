import yt_dlp

def buscar_musicas_soundcloud(termo_busca, limite=5):
    """
    Busca faixas diretamente no SoundCloud usando yt_dlp.
    """
    url_busca = f"scsearch{limite}:{termo_busca}"
    
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'skip_download': True,
    }
    
    resultados = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_busca, download=False)
            entries = info.get('entries', [])
            
            for item in entries:
                if item:
                    thumbnails = item.get('thumbnails', [])
                    capa_url = thumbnails[-1]['url'] if thumbnails else ''
                    
                    duracao_seg = item.get('duration', 0)
                    minutos = int(duracao_seg // 60) if duracao_seg else 0
                    segundos = int(duracao_seg % 60) if duracao_seg else 0
                    duracao_fmt = f"{minutos}:{segundos:02d}" if duracao_seg else "N/A"

                    resultados.append({
                        'id': item.get('url') or item.get('webpage_url'), # URL direta do SoundCloud
                        'titulo': item.get('title'),
                        'artista': item.get('uploader', 'SoundCloud Artist'),
                        'duracao': duracao_fmt,
                        'capa': capa_url,
                        'fonte': 'soundcloud'
                    })
    except Exception as e:
        print(f"Erro ao buscar no SoundCloud: {e}")
        
    return resultados