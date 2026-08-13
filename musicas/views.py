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

def baixar_musica(request, video_id):
    """
    Faz o download do áudio em MP3 usando o FFmpeg embutido
    e entrega o arquivo com o nome do título real da música
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    media_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'downloads')
    os.makedirs(media_folder, exist_ok=True)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Define o nome temporário padrão para o download
    output_template = os.path.join(media_folder, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'ffmpeg_location': ffmpeg_exe,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            titulo = info.get('title', video_id)
            # Limpa caracteres especiais inválidos para nomes de arquivos no Windows
            titulo_limpo = "".join([c for c in titulo if c.isalpha() or c.isdigit() or c in ' -_']).strip()

        file_path = os.path.join(media_folder, f"{titulo}.mp3")
        
        # Caso o sistema renomeie na pasta:
        if not os.path.exists(file_path):
            # Procura o arquivo MP3 gerado mais recente na pasta downloads
            files = [os.path.join(media_folder, f) for f in os.listdir(media_folder) if f.endswith('.mp3')]
            file_path = max(files, key=os.path.getmtime)

        response = FileResponse(open(file_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{titulo_limpo}.mp3"'
        return response

    except Exception as e:
        raise Http404(f"Erro ao baixar áudio: {str(e)}")