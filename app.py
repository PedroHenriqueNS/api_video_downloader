from flask import Flask, jsonify, request, send_file, Response, abort
from flask_cors import CORS
import yt_dlp as yt
import urllib.parse
import os
import secrets
import string
from gevent.pywsgi import WSGIServer



app = Flask(__name__)
CORS(app)



def generate_code(length=30):
    characters = string.ascii_letters + string.digits  # Generate characters from ascii letters and digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def callback_infos(d):
    try: total_bytes = d["total_bytes"]
    except: total_bytes = d["total_bytes_estimate"]

    try:
        match d['status']:
            case 'error':
                print("Erro ao baixar")

                # print(f'oi {(d["fragment_index"]*100)/d["fragment_count"]}%')
                # print(humanize.naturalsize(total_bytes))
                # print(humanize.naturaltime(round(d["eta"])))
                # print(f'oi {humanize.naturalsize(format(d["speed"]), ".2f")}/s')

            case 'finished':
                print('finished')
    except:
        pass



@app.get("/download_video")
def download_video():
    """_summary_
    
        Router Args:
            link (str): URL of the video
    """
    downloaded_filename = None
    def my_hook(d):
        nonlocal downloaded_filename
        if d['status'] == 'finished':
            downloaded_filename = d['filename']
            print(f"Download finished, filename: {downloaded_filename}")
    
    yt_opts = {
        'outtmpl': f'{generate_code()}.%(ext)s',
        'progress_hooks': [my_hook],
        'overwrites': True,
        'format': 'best',
        'nopart': True,
    }
            
    with yt.YoutubeDL(yt_opts) as ydl:
        ydl.download([request.args['link']])
    
    return f'https://api-video-downloader.onrender.com/get_video?filename={urllib.parse.quote_plus(downloaded_filename)}'

@app.get('/get_video')
def get_video():
    full_path = request.args['filename']
    
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_file(full_path, mimetype='video/mp4')
    
    try:
        range_value = range_header.split('=')[1]
        byte1, byte2 = 0, None
        if '-' in range_value:
            byte1, byte2 = range_value.split('-')
        byte1 = int(byte1)
        if byte2:
            byte2 = int(byte2)
        else:
            byte2 = byte1 + 1024*1024  # 1MB chunk size
        length = byte2 - byte1 + 1
        
        with open(full_path, 'rb') as f:
            f.seek(byte1)
            chunk = f.read(length)
        
        response = Response(chunk, 206, mimetype='video/mp4', content_type='video/mp4', direct_passthrough=True)
        response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{os.path.getsize(full_path)}')
        return response
    except Exception as e:
        abort(416)  # Range Not Satisfiable
    


# app.run(debug=False, threaded=True)

# Production
http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()