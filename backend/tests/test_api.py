import json,time,hashlib
import numpy as np
import pytest
from scipy.io import wavfile
from fastapi.testclient import TestClient
from backend import app as module
from backend.models import Project,Clip

@pytest.fixture
def client(tmp_path,monkeypatch):
    for folder in ['sources','analysis','renders','projects','temp']: (tmp_path/folder).mkdir()
    monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setattr(module,'library',{})
    with TestClient(module.app) as c: yield c

def wait(client,jid):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        j=client.get('/api/jobs/'+jid).json()
        if j['status']=='error': pytest.fail(j['message'])
        if j['status']=='done': return j['result']
        time.sleep(.05)
    pytest.fail('Job exceeded 90 seconds')

def test_corrupt_file_safe(client):
    r=client.post('/api/upload',files={'file':('bad.mp3',b'not audio','audio/mpeg')})
    assert r.status_code==400 and 'Unsupported' in r.json()['detail']

def test_real_upload_analysis_render_project_roundtrip(client,tmp_path):
    sr=22050;t=np.arange(sr*5)/sr;y=.1*np.sin(2*np.pi*440*t)
    for pos in np.arange(0,5,.5):
        i=int(pos*sr);n=min(1500,len(y)-i);u=np.arange(n)/sr;y[i:i+n]+=.3*np.sin(2*np.pi*60*u)*np.exp(-u*30)
    path=tmp_path/'input.wav';wavfile.write(path,sr,y.astype(np.float32));original=path.read_bytes()
    r=client.post('/api/upload',files={'file':('input.wav',original,'audio/wav')});assert r.status_code==200
    data=wait(client,r.json()['job_id']);assert data['status']=='ready'
    assert len(data['peaks'])==1600 and len(data['onset_strength'])>0 and data['key']
    assert data['duration']==5
    sid=data['id'];assert sid==hashlib.sha256(original).hexdigest()[:24]
    cached=client.post('/api/upload',files={'file':('renamed.wav',original,'audio/wav')}).json();assert cached['cached']
    p=Project(name='Roundtrip',source_ids=[sid],clips=[Clip(id='clip1',source_id=sid,start=1,end=4,position=.5)])
    pid=client.post('/api/projects',json=p.model_dump()).json()['id'];assert client.get('/api/projects/'+pid).json()==p.model_dump()
    r=client.post('/api/render',json={'project':p.model_dump(),'format':'wav'});assert r.status_code==200
    output=wait(client,r.json()['job_id']);assert abs(output['duration']-3.5)<.001
    audio=client.get(output['url']);assert audio.status_code==200 and audio.content[:4]==b'RIFF'
    assert path.read_bytes()==original
    invalid=client.post('/api/render',json={'project':{**p.model_dump(),'clips':[{**p.clips[0].model_dump(),'end':.1}]}});assert invalid.status_code==422
    assert client.get('/api/projects/../../etc/passwd').status_code!=200

def test_cross_origin_write_rejected(client):
    assert client.post('/api/projects',json=Project().model_dump(),headers={'origin':'https://untrusted.example'}).status_code==403

def test_missing_source_render_fails_as_job(client):
    p=Project(clips=[Clip(id='missing',source_id='f'*24,start=0,end=1,position=0)])
    r=client.post('/api/render',json={'project':p.model_dump()});jid=r.json()['job_id']
    for _ in range(100):
        j=client.get('/api/jobs/'+jid).json()
        if j['status']=='error': break
        time.sleep(.01)
    assert j['status']=='error' and 'Source file missing' in j['message']

def test_builtin_effect_is_ready_and_sound_fields_persist(client):
    s=client.post('/api/effects/builtin/whoosh-up',json={}).json()
    assert s['kind']=='sfx' and s['builtin'] and s['status']=='ready'
    assert client.get('/api/sources/'+s['id']+'/audio').content[:4]==b'RIFF'
    assert client.post('/api/effects/builtin/not-a-sound',json={}).status_code==400
    from backend.models import Transition
    a=Clip(id='a',source_id=s['id'],start=0,end=1,position=0)
    b=Clip(id='b',source_id=s['id'],start=0,end=1,position=.5)
    p=Project(source_ids=[s['id']],clips=[a,b],transitions=[Transition(id='t',from_id='a',to_id='b',duration=.5,sound_source_id=s['id'],sound_volume=-9,sound_offset=-.2)])
    saved=client.post('/api/projects',json=p.model_dump()).json()
    assert client.get('/api/projects/'+saved['id']).json()==p.model_dump()

def test_upload_sound_effect_skips_music_analysis(client,tmp_path):
    sr=22050;y=(.2*np.sin(2*np.pi*500*np.arange(sr)/sr)).astype(np.float32)
    path=tmp_path/'fx.wav';wavfile.write(path,sr,y)
    r=client.post('/api/upload?kind=sfx',files={'file':('fx.wav',path.read_bytes(),'audio/wav')});assert r.status_code==200
    source=wait(client,r.json()['job_id'])
    assert source['kind']=='sfx' and source['bpm'] is None and len(source['peaks'])==1600

def test_myinstants_import_uses_real_downloaded_audio_with_attribution(client,tmp_path,monkeypatch):
    from backend import myinstants
    from backend.engine import run
    sr=22050;path=tmp_path/'source.wav';mp3=tmp_path/'effect.mp3'
    wavfile.write(path,sr,(.2*np.sin(2*np.pi*500*np.arange(sr)/sr)).astype(np.float32))
    run(['-i',path,'-c:a','libmp3lame',mp3]);audio=mp3.read_bytes()
    monkeypatch.setattr(myinstants,'fetch_bytes',lambda url,limit,asset=False:audio)
    r=client.post('/api/effects/myinstants/import',json={'url':'https://www.myinstants.com/media/sounds/test.mp3'})
    source=wait(client,r.json()['job_id'])
    assert source['origin']=='myinstants' and source['kind']=='sfx'
    assert source['origin_url'].startswith('https://www.myinstants.com/')
    assert client.get('/api/sources/'+source['id']+'/audio').content==audio
    assert client.post('/api/effects/myinstants/import',json={'url':'https://example.com/test.mp3'}).status_code==400


def test_library_reopens_after_drive_move(tmp_path):
    (tmp_path/'sources').mkdir();(tmp_path/'analysis').mkdir()
    sid='d'*24;(tmp_path/'sources'/sid).write_bytes(b'cached-original')
    (tmp_path/'analysis'/f'{sid}.json').write_text(json.dumps({'id':sid,'path':'Z:\\old-folder\\data\\sources\\'+sid,'status':'ready','duration':1}))
    (tmp_path/'analysis'/'bad.json').write_text('{damaged')
    loaded=module.load_library(tmp_path)
    assert loaded[sid]['path']==str((tmp_path/'sources'/sid).resolve())
    assert loaded[sid]['status']=='ready'


def test_mixer_and_loop_survive_project_roundtrip(client):
    from backend.models import TrackMix,LoopRange
    p=Project(name='Advanced session',tracks=[TrackMix(track=2,volume=-3,pan=.4,solo=True)],loop=LoopRange(start=1,end=4,enabled=True))
    saved=client.post('/api/projects',json=p.model_dump())
    reopened=client.get('/api/projects/'+saved.json()['id'])
    assert reopened.json()==p.model_dump()
