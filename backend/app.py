from pathlib import Path
import os, json, hashlib, uuid, threading, shutil, time, traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, HTTPException, Request, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .models import Project, RenderRequest, AutoRequest, TransitionRequest, MyinstantsImportRequest
from .engine import analyze, render, arrange, plan_transitions, probe

ROOT=Path(__file__).resolve().parent.parent
DATA=Path(os.getenv('MIXFORGE_DATA',str(ROOT/'data')))
for folder in ['sources','analysis','renders','projects','temp']: (DATA/folder).mkdir(parents=True,exist_ok=True)
executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='audio')
jobs={}; lock=threading.Lock()
def load_library(data):
    import re
    result={}
    for p in (data/'analysis').glob('*.json'):
        try:
            s=json.loads(p.read_text(encoding='utf-8')); sid=s['id']
            if not re.fullmatch(r'[a-f0-9]{24}',sid): continue
            local=data/'sources'/sid
            path=local if local.is_file() else Path(s.get('path',''))
            if path.is_file():
                s['path']=str(path.resolve())
                if s.get('status')=='analyzing': s.update(status='error',error='Analysis was interrupted. Re-import this file to retry.')
                result[sid]=s
        except (ValueError,KeyError,OSError,TypeError): continue
    return result
library=load_library(DATA)

def public(s): return {k:v for k,v in s.items() if k!='path'}
def persist_source(s):
    target=DATA/'analysis'/f"{s['id']}.json"
    tmp=target.with_suffix('.tmp'); tmp.write_text(json.dumps(s),encoding='utf-8'); tmp.replace(target)

def submit(kind, fn):
    with lock:
        if sum(j['status'] in ['queued','running'] for j in jobs.values())>=32: raise HTTPException(429,'Audio queue is full. Wait for a job to finish.')
        jid=uuid.uuid4().hex; jobs[jid]={'id':jid,'kind':kind,'status':'queued','progress':0,'message':'Queued','created':time.time()}
    def update(n,m):
        with lock: jobs[jid].update(progress=round(n,3),message=m)
    def work():
        jobs[jid]['status']='running'
        try:
            result=fn(update)
            with lock: jobs[jid].update(status='done',progress=1,message='Complete',result=result)
        except Exception as e:
            with lock: jobs[jid].update(status='error',message=str(e)[:1000])
    executor.submit(work)
    # Bound retained status metadata; output files remain accessible.
    with lock:
        done=[j for j in jobs.values() if j['status'] in ['done','error']]
        for j in sorted(done,key=lambda x:x['created'])[:-100]: jobs.pop(j['id'],None)
    return {'job_id':jid}

app=FastAPI(title='MixForge Studio',version='1.3.0')

@app.middleware('http')
async def local_security(request:Request,call_next):
    # Same-origin local workstation. No permissive CORS or arbitrary filesystem paths.
    origin=request.headers.get('origin')
    if origin and origin not in [str(request.base_url).rstrip('/'),'http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000']:
        return JSONResponse({'detail':'Use the locally served MixForge workstation.'},status_code=403)
    return await call_next(request)

@app.get('/api/health')
def health(): return {'status':'ok','ffmpeg':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),'sample_rate':44100,'engine':'Python + FFmpeg','version':'1.3.0'}

@app.get('/api/sources')
def sources(): return [public(s) for s in list(library.values())]

@app.post('/api/upload')
async def upload(file:UploadFile,kind:str=Query(default='music',pattern='^(music|sfx)$')):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): raise HTTPException(503,'Install FFmpeg and add it to PATH, then restart MixForge.')
    tmp=DATA/'temp'/uuid.uuid4().hex
    digest=hashlib.sha256(); size=0
    try:
        with tmp.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>500*1024*1024: raise HTTPException(413,'Maximum source size is 500 MB.')
                digest.update(chunk); out.write(chunk)
        sid=digest.hexdigest()[:24]
        if sid in library and library[sid].get('status')=='ready' and (kind=='sfx' or library[sid].get('kind')!='sfx'):
            if kind=='sfx':
                if library[sid]['duration']>60: raise ValueError('Use a sound effect no longer than 60 seconds.')
                library[sid]['kind']='sfx'; persist_source(library[sid])
            return {'source':public(library[sid]),'cached':True}
        duration=probe(tmp)
        if kind=='sfx' and duration>60: raise ValueError('Use a sound effect no longer than 60 seconds.')
        target=DATA/'sources'/sid; tmp.replace(target)
        s={'id':sid,'name':Path(file.filename or 'Audio').name,'duration':duration,'path':str(target),'status':'analyzing','size':size,'kind':kind}
        library[sid]=s
        def process(update):
            try:
                from .effects import analyze_effect
                data=analyze_effect(target,update) if kind=='sfx' else analyze(target,update); s.update(data,status='ready'); persist_source(s); return public(s)
            except Exception as e:
                s.update(status='error',error=str(e)); persist_source(s); raise
        result=submit('analysis',process)
        return {**result,'source':public(s)}
    except ValueError as e: raise HTTPException(400,str(e))
    finally:
        tmp.unlink(missing_ok=True); await file.close()

@app.post('/api/effects/builtin/{slug}')
def builtin_effect(slug:str):
    from .effects import register_builtin
    try: return public(register_builtin(slug,ROOT,DATA,library,persist_source))
    except ValueError as e: raise HTTPException(400,str(e))

@app.get('/api/effects/myinstants/search')
def search_myinstants(q:str=Query(min_length=1,max_length=80),page:int=Query(default=1,ge=1,le=100)):
    from .myinstants import search
    try: return search(q,page)
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/effects/myinstants/import')
def import_myinstants(req:MyinstantsImportRequest):
    from .myinstants import validate_url
    try: validate_url(req.url)
    except ValueError as e: raise HTTPException(400,str(e))
    def process(update):
        from .myinstants import resolve,fetch_bytes,MAX_AUDIO
        from .effects import analyze_effect
        update(.1,'Looking up Myinstants sound')
        remote=resolve(req.url); audio=fetch_bytes(remote['url'],MAX_AUDIO,True)
        sid=hashlib.sha256(audio).hexdigest()[:24]
        if sid in library and library[sid].get('status')=='ready':
            if library[sid]['duration']>60: raise ValueError('Use a sound effect no longer than 60 seconds.')
            library[sid].update(kind='sfx',origin='myinstants',origin_url=remote['page_url']);persist_source(library[sid]);return public(library[sid])
        tmp=DATA/'temp'/uuid.uuid4().hex
        try:
            tmp.write_bytes(audio); analysis=analyze_effect(tmp,update)
            target=DATA/'sources'/sid; tmp.replace(target)
            entry={'id':sid,'name':remote['name'],'path':str(target),'status':'ready','kind':'sfx','size':len(audio),'origin':'myinstants','origin_url':remote['page_url'],**analysis}
            library[sid]=entry;persist_source(entry);return public(entry)
        finally: tmp.unlink(missing_ok=True)
    return submit('sound import',process)

@app.get('/api/jobs/{jid}')
def job(jid:str):
    if jid not in jobs: raise HTTPException(404,'Job not found; the server may have restarted.')
    return jobs[jid]

@app.get('/api/sources/{sid}/audio')
def source_audio(sid:str):
    if sid not in library: raise HTTPException(404,'Source not found')
    return FileResponse(library[sid]['path'],media_type='application/octet-stream',filename=library[sid]['name'])

@app.post('/api/render')
def render_api(req:RenderRequest):
    if not req.project.clips: raise HTTPException(400,'Add clips to your timeline first.')
    snapshot={sid:dict(s) for sid,s in library.copy().items()}
    def process(update):
        # Render cache includes all edit parameters; originals are content-addressed.
        key=hashlib.sha256((req.model_dump_json()+'engine-v4').encode()).hexdigest()[:24]
        target=DATA/'renders'/f'{key}.{req.format}'
        if target.exists():
            try: return {'url':f'/api/renders/{target.name}','duration':probe(target),'cached':True}
            except ValueError: target.unlink(missing_ok=True)
        staging=target.with_name(key+'.partial.'+req.format)
        try:
            duration=render(req.project,snapshot,staging,req.normalize,update,req.range_start,req.range_end)
            staging.replace(target)
        finally: staging.unlink(missing_ok=True)
        return {'url':f'/api/renders/{target.name}','duration':duration}
    return submit('render',process)

@app.get('/api/renders/{name}')
def rendered(name:str,download:bool=False):
    import re
    if not re.fullmatch(r'[a-f0-9]{24}\.(wav|mp3)',name): raise HTTPException(404)
    path=DATA/'renders'/name
    if not path.exists(): raise HTTPException(404,'Render not found')
    return FileResponse(path,media_type='audio/mpeg' if name.endswith('mp3') else 'audio/wav',filename=f'MixForge-remix.{name.split(".")[-1]}' if download else None)

@app.post('/api/arrange')
def auto_api(req:AutoRequest):
    try: return arrange(req,library)
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/transitions')
def transition_api(req:TransitionRequest):
    try:
        p,m=plan_transitions(req.project,library,req.style,req.duration,req.from_id,req.to_id,req.match_tempo)
        return {'project':p,'messages':m}
    except (ValueError,KeyError) as e: raise HTTPException(400,str(e))

@app.post('/api/validate')
def validate_project(p:Project): return p

@app.post('/api/projects')
def save_project(p:Project):
    pid=uuid.uuid4().hex[:24]
    target=DATA/'projects'/f'{pid}.json'
    temporary=target.with_suffix('.tmp'); temporary.write_text(p.model_dump_json(indent=2),encoding='utf-8'); temporary.replace(target)
    return {'id':pid,'name':p.name}

@app.get('/api/projects')
def projects():
    result=[]
    for f in sorted((DATA/'projects').glob('*.json'),key=lambda f:f.stat().st_mtime,reverse=True):
        try: result.append({'id':f.stem,'name':json.loads(f.read_text(encoding='utf-8')).get('name','Untitled'),'modified':f.stat().st_mtime})
        except ValueError: pass
    return result

@app.get('/api/projects/{pid}')
def open_project(pid:str):
    import re
    if not re.fullmatch('[a-f0-9]{24}',pid): raise HTTPException(404)
    f=DATA/'projects'/f'{pid}.json'
    if not f.exists(): raise HTTPException(404,'Project not found')
    try: return Project.model_validate_json(f.read_text(encoding='utf-8'))
    except ValueError: raise HTTPException(400,'This saved project is damaged. Open a backup project JSON.')

@app.post('/api/demo')
def demo():
    def process(update):
        from .demo import create_demo
        return create_demo(DATA,library,persist_source,update).model_dump()
    return submit('demo',process)

if (ROOT/'dist').exists(): app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')

if __name__=='__main__':
    import uvicorn
    uvicorn.run('backend.app:app',host='127.0.0.1',port=8000)
