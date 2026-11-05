"""Portable launcher; keeps the backend visible and opens only after readiness."""
from pathlib import Path
import shutil,sys,threading,time,webbrowser,urllib.request,json,os
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
if os.name == "nt":
    os.environ["PATH"] = os.pathsep.join([str(ROOT),str(ROOT/"bin"),os.environ.get("PATH","")])
if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
    sys.exit('FFmpeg and FFprobe are missing. Put their executables beside launch-windows.bat, in bin, or on PATH. See README.md.')
if not (ROOT/'dist'/'index.html').exists(): sys.exit('Build the frontend first: npm ci && npm run build')
os.environ.setdefault('NUMBA_CACHE_DIR',str(ROOT/'data'/'numba-cache'))
url='http://127.0.0.1:8000'
def healthy():
    try:
        with urllib.request.urlopen(url+'/api/health',timeout=.5) as r: return json.load(r).get('engine')=='Python + FFmpeg'
    except Exception: return False
if healthy():
    webbrowser.open(url);sys.exit(0)
def open_ready():
    for _ in range(60):
        if healthy(): webbrowser.open(url);return
        time.sleep(.5)
threading.Thread(target=open_ready,daemon=True).start()
print('MixForge Studio — '+url+'\nKeep this window open. Press Ctrl+C to stop.')
import uvicorn
uvicorn.run('backend.app:app',host='127.0.0.1',port=8000)
