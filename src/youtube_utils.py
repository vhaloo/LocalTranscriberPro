import os
import yt_dlp
import logging

def download_youtube_audio(url, output_dir, progress_callback=None):
    """
    Downloads audio from a YouTube URL using yt-dlp.
    Returns the path to the downloaded audio file.
    """
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    if progress_callback:
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    p = d.get('_percent_str', '0%').replace('%','')
                    progress_callback(float(p))
                except: pass
            elif d['status'] == 'finished':
                progress_callback(100.0)
        
        ydl_opts['progress_hooks'] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            final_filename = os.path.splitext(filename)[0] + ".mp3"
            return final_filename
    except Exception as e:
        logging.error(f"YouTube Download Error: {e}")
        raise e
