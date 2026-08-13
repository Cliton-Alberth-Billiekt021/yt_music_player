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

import requests
from django.shortcuts import redirect
from django.http import HttpResponse

def baixar_musica(request, video_id):
    try:
        url_youtube = f'https://www.youtube.com/watch?v={video_id}'
        
        # Endpoint de API publica do Cobalt (servico robusto para download)
        api_url = "https://co.wuk.sh/api/json"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url_youtube,
            "downloadMode": "audio",
            "audioFormat": "mp3"
        }
        
        response = requests.post(api_url, json=payload, headers=headers)
        data = response.json()
        
        # Obtem a URL do arquivo de audio gerado pela API
        if response.status_code == 200 and "url" in data:
            return redirect(data["url"])
        else:
            # Fallback caso a API principal esteja ocupada
            fallback_url = f"https://api.cobalt.tools/api/json"
            fb_response = requests.post(fallback_url, json=payload, headers=headers)
            fb_data = fb_response.json()
            if "url" in fb_data:
                return redirect(fb_data["url"])
            return HttpResponse("Erro ao gerar link de download pela API.", status=500)

    except Exception as e:
        return HttpResponse(f"Erro no processamento: {str(e)}", status=500)