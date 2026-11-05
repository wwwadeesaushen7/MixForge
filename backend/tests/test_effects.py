import hashlib,json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import wavfile
from backend.effects import build_assets,analyze_effect,register_builtin
from backend.models import Clip,Project,Transition
from backend.engine import render,plan_transitions,transition_sound_clips,SR,run,probe
from backend import myinstants

A='a'*24;B='b'*24;FX='c'*24

def effect_library(tmp_path):
    silence=np.zeros((SR*5,2),np.float32);path=tmp_path/'music.wav';wavfile.write(path,SR,silence)
    t=np.arange(SR//2)/SR;sound=tmp_path/'hit.wav';wavfile.write(sound,SR,np.stack([.2*np.sin(2*np.pi*440*t)]*2,axis=1).astype(np.float32))
    library={A:{'path':str(path),'duration':5,'energy':.1,'bpm':120,'key_index':0},B:{'path':str(path),'duration':5,'energy':.1,'bpm':120,'key_index':0},FX:{'path':str(sound),'duration':.5,'kind':'sfx'}}
    a=Clip(id='a',source_id=A,start=0,end=4,position=0)
    b=Clip(id='b',source_id=B,start=0,end=3,position=3)
    p=Project(clips=[a,b],transitions=[Transition(id='join',from_id='a',to_id='b',duration=1,sound_source_id=FX,sound_offset=-.5,sound_volume=-6)])
    return library,p

def test_original_effect_assets_are_real_and_deterministic(tmp_path):
    first=build_assets(tmp_path);second=build_assets(tmp_path)
    assert len(first)==8 and [s['id'] for s in first]==[s['id'] for s in second]
    for s in first:
        file=tmp_path/(s['slug']+'.wav');sr,y=wavfile.read(file)
        assert sr==SR and y.ndim==2 and y.shape[1]==2
        assert np.max(abs(y.astype(np.float32)))>1000
        assert s['id']==hashlib.sha256(file.read_bytes()).hexdigest()[:24]
        assert len(s['peaks'])==1600 and abs(probe(file)-s['duration'])<.001

def test_sound_effect_analysis_does_not_invent_bpm(tmp_path):
    library,_=effect_library(tmp_path);data=analyze_effect(Path(library[FX]['path']))
    assert data['kind']=='sfx' and data['bpm'] is None and data['key'] is None
    assert data['energy']>0 and len(data['peaks'])==1600

def test_transition_sound_is_mixed_at_requested_offset_in_wav_and_mp3(tmp_path):
    library,p=effect_library(tmp_path)
    assert transition_sound_clips(p,library)[0].position==2.5
    for extension in ['wav','mp3']:
        out=tmp_path/('mix.'+extension);raw=tmp_path/'decoded.f32';render(p,library,out,False)
        run(['-i',out,'-f','f32le','-ar',SR,'-ac',2,raw])
        y=np.fromfile(raw,np.float32).reshape(-1,2)
        assert np.max(abs(y[:int(2.4*SR)]))<1e-4
        assert np.sqrt(np.mean(y[int(2.6*SR):int(2.8*SR)]**2))>.04
        assert np.max(abs(y[int(3.2*SR):]))<1e-4
        assert abs(probe(out)-6)<.06

def test_sound_regeneration_and_bypass_preserve_manual_music(tmp_path):
    library,p=effect_library(tmp_path)
    fx=Clip(id='fx',source_id=FX,start=0,end=.5,position=2,role='sfx',track=3)
    p.clips.append(fx)
    changed,_=plan_transitions(p,library,'Smooth',1)
    assert len(changed.transitions)==1 and changed.transitions[0].to_id=='b'
    assert changed.transitions[0].sound_source_id==FX and changed.transitions[0].sound_volume==-6
    assert changed.clips==p.clips
    changed.auto_transitions=False;assert transition_sound_clips(changed,library)==[]
    changed.auto_transitions=True;changed.transitions[0].enabled=False;assert transition_sound_clips(changed,library)==[]

def test_missing_transition_sound_fails_clearly(tmp_path):
    library,p=effect_library(tmp_path);del library[FX]
    with pytest.raises(ValueError,match='Transition sound is missing'):render(p,library,tmp_path/'bad.wav')

@pytest.mark.parametrize('url',['http://www.myinstants.com/media/sounds/x.mp3','https://127.0.0.1/media/sounds/x.mp3','https://myinstants.com.evil.test/media/sounds/x.mp3','https://www.myinstants.com@evil.test/media/sounds/x.mp3','https://www.myinstants.com:8080/media/sounds/x.mp3','https://www.myinstants.com/media/sounds/%2e%2e/x.mp3'])
def test_myinstants_only_fetches_allowed_public_host(url):
    with pytest.raises(ValueError):myinstants.validate_url(url,True)

def test_official_myinstants_api_mapping_and_cached_search(monkeypatch):
    calls=[];myinstants._cache.clear();myinstants._calls.clear()
    def fake(url,limit,asset=False):
        calls.append(url)
        return json.dumps({'count':1,'next':None,'results':[{'name':'Whoosh','slug':'whoosh-123','sound':'https://www.myinstants.com/media/sounds/whoosh.mp3'}]}).encode()
    monkeypatch.setattr(myinstants,'fetch_bytes',fake)
    result=myinstants.search('whoosh');assert result['results'][0]['name']=='Whoosh'
    myinstants.search('whoosh');assert len(calls)==1
    assert '/api/v1/instants/?name=whoosh&page=1' in calls[0]
    monkeypatch.setattr(myinstants,'api_json',lambda path:{'name':'Whoosh','sound':'https://www.myinstants.com/media/sounds/whoosh.mp3'})
    resolved=myinstants.resolve('https://www.myinstants.com/en/instant/whoosh-123/')
    assert resolved['url'].endswith('/whoosh.mp3') and resolved['name']=='Whoosh.mp3'
