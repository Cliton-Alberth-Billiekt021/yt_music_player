import os
from django.shortcuts import render
from django.http import FileResponse, Http404
import yt_dlp
import imageio_ffmpeg  # Importa o caminho do FFmpeg instalado

def lista_musicas(request):
    query = request.GET.get('q', '').strip()
    resultados = []

    if query:
        ydl_opts = {
            'default_search': 'ytsearch10',
            'extract_flat': 'in_playlist',
            'quiet': True,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                entries = info.get('entries', [])
                
                for item in entries:
                    if item:
                        thumbnails = item.get('thumbnails', [])
                        capa_url = thumbnails[-1]['url'] if thumbnails else ''
                        
                        duracao_seg = item.get('duration', 0)
                        minutos = int(duracao_seg // 60)
                        segundos = int(duracao_seg % 60)
                        duracao_fmt = f"{minutos}:{segundos:02d}" if duracao_seg else "N/A"

                        resultados.append({
                            'id': item.get('id'),
                            'titulo': item.get('title'),
                            'artista': item.get('uploader', 'Artista Desconhecido'),
                            'duracao': duracao_fmt,
                            'capa': capa_url,
                        })
        except Exception as e:
            print(f"Erro na busca: {e}")

    return render(request, 'musicas/lista.html', {
        'resultados': resultados,
        'query': query
    })

import os
import yt_dlp
from django.shortcuts import redirect
from django.http import HttpResponse

def baixar_musica(request, video_id):
    try:
        url_youtube = f'https://www.youtube.com/watch?v={video_id}'
        
        # Caminho para o arquivo de cookies
        cookie_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.txt')

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': cookie_path if os.path.exists(cookie_path) else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_youtube, download=False)
            url_stream = info.get('url')
            
            if url_stream:
                return redirect(url_stream)
            else:
                return HttpResponse("Não foi possível gerar o link de áudio.", status=500)
                
    except Exception as e:
        return HttpResponse(f"Erro ao processar áudio: {str(e)}", status=500)