"""Small, original one-shot sounds. No downloaded third-party audio is bundled."""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy import signal
from scipy.io import wavfile
from .engine import SR,ANALYSIS_SR,probe,run

PRESETS=[
    ('whoosh-up','Whoosh up','Transition',1.8),
    ('whoosh-down','Whoosh down','Transition',1.8),
    ('impact','Deep impact','Impact',1.4),
    ('riser','Tension riser','Transition',4.0),
    ('sub-drop','Sub drop','Bass',2.2),
    ('air-horn','DJ air horn','DJ',1.6),
    ('vinyl-stop','Vinyl stop','DJ',1.2),
    ('shimmer','Shimmer','Accent',2.5),
]

def peaks(y,bins=1600):
    mono=np.mean(y,axis=1) if y.ndim==2 else y
    chunks=np.array_split(mono,bins)
    result=[float(np.max(np.abs(c))) if len(c) else 0 for c in chunks]
    top=max(result) or 1
    return [round(v/top,5) for v in result]

def synthesize(slug,duration):
    rng=np.random.default_rng(int(hashlib.sha256(slug.encode()).hexdigest()[:8],16))
    t=np.arange(round(SR*duration),dtype=np.float64)/SR
    u=t/duration; noise=rng.standard_normal(len(t))
    airy=signal.sosfilt(signal.butter(2,[350,10000],btype='bandpass',fs=SR,output='sos'),noise)
    if slug.startswith('whoosh'):
        envelope=np.sin(np.pi*u)**1.5
        sweep=signal.chirp(t,f0=180,f1=6000,t1=duration,method='logarithmic')
        y=(airy*.35+sweep*.08)*envelope
        if slug=='whoosh-down': y=y[::-1].copy()
    elif slug=='impact':
        phase=2*np.pi*(38*t+3*(1-np.exp(-t*22)))
        y=.7*np.sin(phase)*np.exp(-t*5)+.2*airy*np.exp(-t*19)
    elif slug=='riser':
        y=(.3*airy+.18*signal.chirp(t,f0=90,f1=3400,t1=duration,method='logarithmic'))*u**1.7
        y*=.6+.4*np.sin(2*np.pi*(3*t+3*t*t))**2
    elif slug=='sub-drop':
        y=np.sin(2*np.pi*(31*t+28*(1-np.exp(-t*3))))*np.exp(-t*2.4)
    elif slug=='air-horn':
        gate=(np.sin(np.pi*np.clip((t%0.55)/.38,0,1))**.25)*(t%0.55<.38)
        y=(np.sin(2*np.pi*220*t)+.5*np.sin(2*np.pi*330*t)+.25*np.sin(2*np.pi*440*t))*gate
        y=np.tanh(y*1.2)*.5
    elif slug=='vinyl-stop':
        phase=2*np.pi*(230*t-95*t*t/duration)
        y=(np.sin(phase)+.3*np.sin(2*phase))*(1-u)**.8
    elif slug=='shimmer':
        y=sum(np.sin(2*np.pi*f*t)*np.exp(-t*(1.7+i*.15)) for i,f in enumerate([880,1108.73,1318.51,1760]))*.2
    else: raise ValueError('Unknown built-in sound')
    y*=np.minimum(1,t/.008)*np.minimum(1,(duration-t)/.04)
    y=y/(np.max(np.abs(y)) or 1)*.75
    stereo=np.stack([y,np.roll(y,19)*.98],axis=1)
    return np.round(stereo*32767).astype(np.int16)

def build_assets(folder:Path):
    folder.mkdir(parents=True,exist_ok=True); catalog=[]
    for index,(slug,name,category,duration) in enumerate(PRESETS):
        path=folder/(slug+'.wav'); y=synthesize(slug,duration); wavfile.write(path,SR,y)
        sid=hashlib.sha256(path.read_bytes()).hexdigest()[:24]
        normalized=y.astype(np.float32)/32768
        catalog.append({'id':sid,'slug':slug,'name':name+'.wav','duration':len(y)/SR,'status':'ready','kind':'sfx','builtin':True,'category':category,'hotkey':index+1,'asset_url':'/effects/'+slug+'.wav','energy':float(np.sqrt(np.mean(normalized**2))),'peaks':peaks(normalized),'size':path.stat().st_size})
    (folder/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
    return catalog

def register_builtin(slug,root,data,library,persist):
    import shutil
    folder=root/'public'/'effects'; manifest=folder/'catalog.json'
    catalog=json.loads(manifest.read_text()) if manifest.exists() else build_assets(folder)
    descriptor=next((s for s in catalog if s['slug']==slug),None)
    if not descriptor: raise ValueError('Unknown built-in sound effect')
    sid=descriptor['id']
    if sid not in library or not Path(library[sid]['path']).exists():
        path=data/'sources'/sid
        shutil.copyfile(folder/(slug+'.wav'),path)
        entry={**descriptor,'path':str(path)}; library[sid]=entry; persist(entry)
    return library[sid]

def analyze_effect(path,progress=lambda n,m:None):
    import tempfile
    duration=probe(path)
    if duration>60: raise ValueError('Use a sound effect no longer than 60 seconds.')
    progress(.2,'Preparing sound effect')
    with tempfile.TemporaryDirectory() as tmp:
        raw=Path(tmp)/'mono.f32'
        run(['-i',path,'-vn','-ac',1,'-ar',ANALYSIS_SR,'-f','f32le',raw])
        y=np.fromfile(raw,np.float32)
    progress(.95,'Caching sound waveform')
    return {'duration':duration,'kind':'sfx','peaks':peaks(y),'energy':float(np.sqrt(np.mean(y*y))),'bpm':None,'key':None,'beats':[],'sections':[]}

if __name__=='__main__':
    build_assets(Path(__file__).resolve().parent.parent/'public'/'effects')
