"""Original synthesized demo stems, analyzed by exactly the same path as uploads."""
import hashlib
import numpy as np
from scipy.io import wavfile
from .engine import analyze, SR, plan_transitions
from .models import Project, Clip

def create_demo(data,library,persist,progress):
    descriptions=[('Midnight Drive',120,[57,60,64,67]),('Neon Skyline',124,[60,64,67,71]),('After Hours',118,[53,57,60,64])]
    source_ids=[]
    for k,(name,bpm,notes) in enumerate(descriptions):
        sid=hashlib.sha256(('mixforge-original-demo-v1-'+name).encode()).hexdigest()[:24]; source_ids.append(sid)
        if sid in library and library[sid].get('status')=='ready': continue
        progress(k/3,f'Creating original demo: {name}')
        duration=48; t=np.arange(SR*duration,dtype=np.float32)/SR
        audio=np.zeros(len(t),np.float32); beat=60/bpm
        # Evolving pad, arpeggio, bass, kick, clap, and hats.
        for j,note in enumerate(notes):
            freq=440*2**((note-69)/12)
            audio+=.025*np.sin(2*np.pi*freq*t)*(0.6+.4*np.sin(2*np.pi*.12*t+j))
        rng=np.random.default_rng(k)
        for i,pos in enumerate(np.arange(0,duration,beat/2)):
            offset=int(pos*SR); length=min(int(.24*SR),len(t)-offset); u=np.arange(length)/SR
            if i%2==0:
                kick=.32*np.sin(2*np.pi*(49*u+2*(1-np.exp(-u*40))))*np.exp(-u*23)
                audio[offset:offset+length]+=kick
            if i%4==2: audio[offset:offset+length]+=.075*rng.standard_normal(length)*np.exp(-u*35)
            hat=.025*rng.standard_normal(length)*np.exp(-u*90)
            audio[offset:offset+length]+=hat
            freq=440*2**((notes[(i//2)%4]+12-69)/12)
            audio[offset:offset+length]+=.045*np.sin(2*np.pi*freq*u)*np.exp(-u*12)
        audio*=np.minimum(1,t/1.5)*np.minimum(1,(duration-t)/1.5)
        stereo=np.stack([audio,np.roll(audio,37)*.98],axis=1)
        path=data/'sources'/sid; wavfile.write(path,SR,stereo)
        s={'id':sid,'name':name+'.wav','path':str(path),'status':'ready','size':path.stat().st_size,'demo':True}
        s.update(analyze(path,lambda v,m:progress((k+v)/3,m))); library[sid]=s; persist(s)
    p=Project(name='Late night sessions',source_ids=source_ids,bpm=120)
    for i,sid in enumerate(source_ids):
        p.clips.append(Clip(id=f'demo-{i}',source_id=sid,start=4,end=36,position=i*25,track=i,volume=-1 if i==1 else 0))
    p,_=plan_transitions(p,library,'Smart',6)
    return p
