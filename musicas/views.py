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
    Gera link de download via API do Cobalt (suporta YouTube e SoundCloud)
    ou redireciona direto se já for um link de áudio MP3 (Jamendo).
    """
    try:
        # 1. Se for Jamendo (ou URL direta de áudio/MP3)
        if video_id.startswith('http://') or video_id.startswith('https://'):
            if 'soundcloud.com' not in video_id:
                return redirect(video_id)
            target_url = video_id  # Link nativo do SoundCloud
        else:
            # 2. Se for ID simples do YouTube
            target_url = f'https://www.youtube.com/watch?v={video_id}'

        # Instâncias oficiais e ativas da API do Cobalt
        instancias_cobalt = [
            "https://api.cobalt.tools/",
            "https://cobalt-api.kwi.mobi/"
        ]

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": target_url,
            "downloadMode": "audio",
            "audioFormat": "mp3"
        }

        # Tenta a requisição nas instâncias
        for api_url in instancias_cobalt:
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "url" in data:
                        return redirect(data["url"])
            except Exception as req_err:
                print(f"Falha na instância {api_url}: {req_err}")
                continue

        return HttpResponse("Não foi possível gerar o link de download no momento. Tente novamente em instantes.", status=500)

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