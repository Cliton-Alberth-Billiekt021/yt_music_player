import os
import requests
import yt_dlp

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, Http404

from .jamendo import buscar_musicas_jamendo
from .soundcloud import buscar_musicas_soundcloud
from .recomendacoes import extrair_artistas_e_feat, buscar_sugestoes_estilo


def lista_musicas(request):
    """
    Busca unificada em 3 fontes: Jamendo, SoundCloud e YouTube.
    """
    query = request.GET.get('q', '').strip()
    resultados = []

    if query:
        # 1. Jamendo (MP3 Direto e Rápido)
        try:
            resultados_jamendo = buscar_musicas_jamendo(query, limite=5)
            resultados.extend(resultados_jamendo)
        except Exception as e:
            print(f"Erro Jamendo: {e}")

        # 2. SoundCloud (Remixes, Independentes e Beats)
        try:
            resultados_sc = buscar_musicas_soundcloud(query, limite=5)
            resultados.extend(resultados_sc)
        except Exception as e:
            print(f"Erro SoundCloud: {e}")

        # 3. YouTube (Catálogo Geral)
        ydl_opts = {
            'default_search': 'ytsearch5',
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
                        minutos = int(duracao_seg // 60) if duracao_seg else 0
                        segundos = int(duracao_seg % 60) if duracao_seg else 0
                        duracao_fmt = f"{minutos}:{segundos:02d}" if duracao_seg else "N/A"

                        resultados.append({
                            'id': item.get('id'),
                            'titulo': item.get('title'),
                            'artista': item.get('uploader', 'Artista Desconhecido'),
                            'duracao': duracao_fmt,
                            'capa': capa_url,
                            'fonte': 'youtube'
                        })
        except Exception as e:
            print(f"Erro YouTube: {e}")

    return render(request, 'musicas/lista.html', {
        'resultados': resultados,
        'query': query
    })


def baixar_musica(request, video_id):
    """
    Gera link de download redirecionando via API do Cobalt.
    """
    try:
        url_youtube = f'https://www.youtube.com/watch?v={video_id}'
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
        
        if response.status_code == 200 and "url" in data:
            return redirect(data["url"])
        else:
            fallback_url = "https://api.cobalt.tools/api/json"
            fb_response = requests.post(fallback_url, json=payload, headers=headers)
            fb_data = fb_response.json()
            if "url" in fb_data:
                return redirect(fb_data["url"])
            return HttpResponse("Erro ao gerar link de download pela API.", status=500)

    except Exception as e:
        return HttpResponse(f"Erro no processamento: {str(e)}", status=500)


def detalhe_musica(request, video_id):
    """
    Retorna os dados da música selecionada + lista de recomendações/feats
    """
    titulo = request.GET.get('titulo', '')
    artista = request.GET.get('artista', '')
    
    # 1. Identifica participações no título
    feats_encontrados = extrair_artistas_e_feat(titulo)
    
    # 2. Busca faixas do mesmo estilo
    sugestoes = buscar_sugestoes_estilo(artista, titulo)
    
    return JsonResponse({
        'video_id': video_id,
        'fonte': 'youtube',
        'feats': feats_encontrados,
        'sugestoes': sugestoes
    })