import os
import requests
import yt_dlp
import urllib.parse
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, Http404, StreamingHttpResponse

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


# 🧠 NOVA FUNÇÃO: Cria a ponte de streaming entre o servidor e o usuário
def transmitir_audio(url):
    try:
        req = requests.get(url, stream=True, timeout=10)
        return StreamingHttpResponse(
            req.iter_content(chunk_size=8192), 
            content_type=req.headers.get('content-type', 'audio/mpeg')
        )
    except Exception as e:
        return HttpResponse(f"Erro no stream: {e}", status=500)


def baixar_musica(request, video_id):
    """
    Verifica o cache. Se não encontrar, extrai e transmite o áudio como ponte (Proxy).
    """
    try:
        video_id = urllib.parse.unquote(video_id)

        # Procura na memória se já extraímos essa música recentemente
        chave_cache = f'musica_{video_id}'
        url_em_cache = cache.get(chave_cache)
        
        if url_em_cache:
            print(f"🔥 CACHE HIT: Transmitindo música {video_id} da memória!")
            return transmitir_audio(url_em_cache) # 👈 AGORA TRANSMITE O ÁUDIO

        # 1. FIX JAMENDO
        if video_id.isdigit():
            final_url = f"https://prod-1.storage.jamendo.com/download/track/{video_id}/mp31/"
            cache.set(chave_cache, final_url, timeout=60*60*24) # Salva Jamendo por 24 horas
            return redirect(final_url)
            
        if (video_id.startswith('http://') or video_id.startswith('https://')) and 'jamendo.com' in video_id:
            cache.set(chave_cache, video_id, timeout=60*60*24)
            return redirect(video_id)

        # 2. Monta a URL
        if video_id.startswith('http://') or video_id.startswith('https://'):
            target_url = video_id
        else:
            target_url = f'https://www.youtube.com/watch?v={video_id}'

        # 🚀 PLANO A: Cobalt API
        try:
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            payload = {"url": target_url, "isAudioOnly": True}
            resposta = requests.post('https://api.cobalt.tools/api/json', headers=headers, json=payload, timeout=10)
            
            if resposta.status_code == 200:
                dados = resposta.json()
                audio_url = dados.get('url')
                if audio_url:
                    # Salva a URL extraída na memória por 2 horas
                    cache.set(chave_cache, audio_url, timeout=7200)
                    return transmitir_audio(audio_url) # 👈 AGORA TRANSMITE O ÁUDIO
        except Exception as e_cobalt:
            print(f"Cobalt falhou, pulando para yt_dlp: {e_cobalt}")

        # 🛠️ PLANO B: yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt', # Mantido para autenticação se necessário
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            audio_url = info.get('url')
            if audio_url:
                # Salva a URL extraída na memória por 2 horas
                cache.set(chave_cache, audio_url, timeout=7200)
                return transmitir_audio(audio_url) # 👈 AGORA TRANSMITE O ÁUDIO

        return HttpResponse("Não foi possível extrair o link de áudio dessa faixa.", status=500)

    except Exception as e:
        print(f"Erro no download: {e}")
        if 'soundcloud' in str(video_id).lower():
            return HttpResponse("Erro: O SoundCloud bloqueou o acesso a esta música. Tente buscar uma versão alternativa.", status=403)
        return HttpResponse(f"Erro ao processar download: {str(e)}", status=500)


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