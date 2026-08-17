import os
import requests
import yt_dlp
import urllib.parse
from django.core.cache import cache
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
        try:
            resultados_jamendo = buscar_musicas_jamendo(query, limite=5)
            resultados.extend(resultados_jamendo)
        except Exception as e:
            print(f"Erro Jamendo: {e}")

        try:
            resultados_sc = buscar_musicas_soundcloud(query, limite=5)
            resultados.extend(resultados_sc)
        except Exception as e:
            print(f"Erro SoundCloud: {e}")

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
    Lógica Suprema de Streaming: Prioriza Piped API para YouTube, depois Cobalt e yt-dlp.
    Retorna redirecionamentos puros que os navegadores suportam nativamente (Byte Ranges).
    """
    try:
        video_id = urllib.parse.unquote(video_id)

        chave_cache = f'musica_{video_id}'
        url_em_cache = cache.get(chave_cache)
        
        if url_em_cache:
            return redirect(url_em_cache)

        # 1. JAMENDO (Links Diretos)
        if video_id.isdigit():
            final_url = f"https://prod-1.storage.jamendo.com/download/track/{video_id}/mp31/"
            cache.set(chave_cache, final_url, timeout=86400) 
            return redirect(final_url)
            
        if 'jamendo.com' in video_id:
            cache.set(chave_cache, video_id, timeout=86400)
            return redirect(video_id)

        # 2. YOUTUBE via PIPED API (Rede anti-bloqueio ideal para HTML5 Audio)
        if not video_id.startswith('http'):
            try:
                # Consulta uma instância estável do Piped
                piped_url = f"https://pipedapi.kavin.rocks/streams/{video_id}"
                resp = requests.get(piped_url, timeout=10)
                
                if resp.status_code == 200:
                    dados = resp.json()
                    streams = dados.get('audioStreams', [])
                    if streams:
                        # Pega o stream m4a (perfeito para navegadores)
                        stream_ideal = next((s for s in streams if 'mp4' in s.get('mimeType', '')), streams[0])
                        audio_url = stream_ideal.get('url')
                        
                        if audio_url:
                            cache.set(chave_cache, audio_url, timeout=7200)
                            return redirect(audio_url)
            except Exception as e:
                print(f"Piped API falhou, caindo para plano B: {e}")

        # 3. PLANO B: Cobalt API Geral
        target_url = video_id if video_id.startswith('http') else f'https://www.youtube.com/watch?v={video_id}'
        try:
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            payload = {"url": target_url, "isAudioOnly": True}
            resposta = requests.post('https://api.cobalt.tools/api/json', headers=headers, json=payload, timeout=10)
            
            if resposta.status_code == 200:
                audio_url = resposta.json().get('url')
                if audio_url:
                    cache.set(chave_cache, audio_url, timeout=7200)
                    return redirect(audio_url)
        except Exception as e:
            print(f"Cobalt falhou: {e}")

        # 4. PLANO C: yt-dlp nativo
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt', 
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            audio_url = info.get('url') if 'url' in info else info['entries'][0].get('url')
            if audio_url:
                cache.set(chave_cache, audio_url, timeout=7200)
                return redirect(audio_url)

        return HttpResponse("Erro: Não foi possível extrair o link de áudio.", status=500)

    except Exception as e:
        print(f"Erro global no processamento: {e}")
        return HttpResponse("❌ Erro ao tentar processar o link.", status=500)


def detalhe_musica(request, video_id):
    """
    Retorna os dados da música selecionada + lista de recomendações/feats
    """
    titulo = request.GET.get('titulo', '')
    artista = request.GET.get('artista', '')
    
    feats_encontrados = extrair_artistas_e_feat(titulo)
    sugestoes = buscar_sugestoes_estilo(artista, titulo)
    
    return JsonResponse({
        'video_id': video_id,
        'fonte': 'youtube',
        'feats': feats_encontrados,
        'sugestoes': sugestoes
    })