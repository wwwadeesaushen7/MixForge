import json, subprocess
from pathlib import Path
import numpy as np
from scipy.io import wavfile
import pytest
from backend.engine import render, probe, SR, fade_envelopes, plan_transitions, arrange
from backend.models import Clip, Project, AutoRequest

SID='a'*24
@pytest.fixture
def library(tmp_path):
    t=np.arange(SR*5)/SR
    y=np.zeros((len(t),2),np.float32)
    y[:,0]=.2*np.sin(2*np.pi*440*t); y[:,1]=.2*np.sin(2*np.pi*660*t)
    path=tmp_path/'source.wav'; wavfile.write(path,SR,y)
    return {SID:{'path':str(path),'duration':5,'bpm':120,'key_index':0,'status':'ready','energy':.1,'sections':[{'time':0,'energy':.1},{'time':1,'energy':.2}],'beats':list(np.arange(0,5,.5))}}

def clip(**kwargs): return Clip(id=kwargs.pop('id','c1'),source_id=SID,start=kwargs.pop('start',1),end=kwargs.pop('end',3),position=kwargs.pop('position',0),**kwargs)
def decode(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(SR),'-'])
    return np.frombuffer(raw,np.float32).reshape(-1,2)

def test_precise_trim_and_stereo(library,tmp_path):
    out=tmp_path/'trim.wav'; render(Project(clips=[clip()]),library,out,False)
    assert abs(probe(out)-2)<1/SR
    audio=decode(out); assert audio.shape==(2*SR,2)
    assert not np.allclose(audio[:,0],audio[:,1])

def test_position_silence_and_tempo(library,tmp_path):
    out=tmp_path/'time.wav'; render(Project(clips=[clip(position=1,tempo=1.25)]),library,out,False)
    assert abs(probe(out)-2.6)<.001
    audio=decode(out); assert np.max(np.abs(audio[:SR-10]))<.0001
    # Tempo changes time, while atempo preserves 440 Hz pitch.
    y=audio[SR+5000:SR+20000,0]
    freq=np.fft.rfftfreq(len(y),1/SR)[np.argmax(abs(np.fft.rfft(y)))]
    assert abs(freq-440)<5

def test_equal_power_envelopes():
    a=clip(start=0,end=3); b=clip(id='c2',start=0,end=3,position=2)
    from backend.models import Transition
    p=Project(clips=[a,b],transitions=[Transition(id='t',from_id=a.id,to_id=b.id,duration=1)])
    e1=fade_envelopes(a,p,SR*3)[SR*2:]; e2=fade_envelopes(b,p,SR*3)[:SR]
    assert np.max(np.abs(e1[1000:-1000]**2+e2[1000:-1000]**2-1))<1e-5
    assert e1[-1]<1e-5 and e2[0]==0

def test_mixing_limits_and_mp3(library,tmp_path):
    p=Project(clips=[clip(volume=12),clip(id='c2',volume=12)])
    for ext in ['wav','mp3']:
        out=tmp_path/f'mix.{ext}'; render(p,library,out,True)
        assert abs(probe(out)-2)<.06
        assert np.max(np.abs(decode(out)))<=1

def test_trim_bounds_rejected(library,tmp_path):
    with pytest.raises(ValueError): render(Project(clips=[clip(end=8)]),library,tmp_path/'bad.wav')

def test_auto_duration_and_source_bounds(library):
    for style in ['Smooth','Party','High Energy','Chill']:
        req=AutoRequest(source_ids=[SID],duration=18,style=style,seed=21,transition=1)
        p=arrange(req,library)
        assert p.duration==18
        assert abs(max(c.position+c.duration for c in p.clips)-18)<.03
        for c in p.clips:
            assert 0<=c.start<c.end<=5
            assert .94<=c.tempo<=1.06
        assert len(p.transitions)==len(p.clips)-1

def test_auto_reproducible_seed(library):
    req=AutoRequest(source_ids=[SID],duration=12,seed=42)
    a,b=arrange(req,library),arrange(req,library)
    assert [(c.start,c.end,c.position) for c in a.clips]==[(c.start,c.end,c.position) for c in b.clips]

def test_manual_transition_preserves_arrangement(library):
    p=Project(clips=[clip(start=0,end=4),clip(id='c2',start=1,end=5,position=3)])
    result,_=plan_transitions(p,library,'Bass Swap',3)
    assert [c.model_dump() for c in p.clips]==[c.model_dump() for c in result.clips]
    assert result.transitions[0].duration==1
    assert 'Limited' in result.transitions[0].note

def test_missing_overlap_is_explained(library):
    p=Project(clips=[clip(start=0,end=2),clip(id='c2',start=2,end=4,position=2)])
    result,messages=plan_transitions(p,library)
    assert not result.transitions and 'no overlap' in messages[0]
    assert result.clips[1].position==2

def test_effects_and_transition_export(library,tmp_path):
    p=Project(clips=[clip(start=0,end=4,echo=.3,reverb=.2,low=-5,high=4,automation=[(0,-12),(2,0)]),clip(id='c2',start=1,end=4,position=2)])
    p,_=plan_transitions(p,library,'Bass Swap',1)
    out=tmp_path/'effect.wav'; render(p,library,out)
    assert probe(out)==5
    audio=decode(out); assert np.isfinite(audio).all() and np.max(abs(audio))<1

def test_normalized_clip_gain_is_preserved(library,tmp_path):
    # Global LUFS balancing hides relative gain in a one-clip mix; compare two
    # consecutive sources inside a single render, where their gain must differ.
    p=Project(clips=[clip(start=0,end=2,volume=0),clip(id='quiet',start=0,end=2,position=2,volume=-6)])
    out=tmp_path/'gains.wav';render(p,library,out,True)
    audio=decode(out)
    loud=np.sqrt(np.mean(audio[SR//2:SR]**2));quiet=np.sqrt(np.mean(audio[SR*5//2:SR*3]**2))
    assert .4<quiet/loud<.65

def test_opt_in_manual_beat_matching(library):
    from copy import deepcopy
    other='b'*24; library[other]=deepcopy(library[SID]);library[other]['bpm']=124
    a=clip(start=0,end=4);b=Clip(id='b',source_id=other,start=0,end=4,position=3)
    p=Project(clips=[a,b]); result,_=plan_transitions(p,library,'DJ Beat Match',1,match_tempo=True)
    assert result.clips[1].tempo==120/124
    assert result.clips[1].position==3 and result.clips[1].start==0 and result.clips[1].end==4

def test_beat_aligned_automation_preserves_cuts(library):
    library[SID]['beat_confidence']=.9
    p=Project(clips=[clip(start=0,end=4),clip(id='b',start=.2,end=4,position=2.7)])
    result,_=plan_transitions(p,library,'DJ Beat Match',1)
    assert result.clips==p.clips
    t=result.transitions[0];assert abs(t.offset-.3)<.001


def test_track_solo_pan_gain_and_mute(library,tmp_path):
    from backend.models import TrackMix
    p=Project(clips=[clip(start=0,end=2,track=0,fade_in=0,fade_out=0),clip(id='other',start=0,end=2,track=1)],tracks=[TrackMix(track=0,solo=True,pan=-1,volume=-6)])
    out=tmp_path/'solo.wav';render(p,library,out,False)
    audio=decode(out)
    assert np.max(abs(audio[:,1]))<1e-6
    assert .065<np.sqrt(np.mean(audio[1000:-1000,0]**2))<.077
    p.tracks[0].muted=True
    render(p,library,out,False)
    assert np.max(abs(decode(out)))<1e-6


def test_solo_does_not_fade_toward_muted_clip(library,tmp_path):
    from backend.models import TrackMix,Transition
    a=clip(start=0,end=4,fade_out=0);b=clip(id='b',start=0,end=3,position=2,track=1)
    p=Project(clips=[a,b],tracks=[TrackMix(track=0,solo=True)],transitions=[Transition(id='t',from_id=a.id,to_id=b.id,duration=1)])
    out=tmp_path/'solo-transition.wav';render(p,library,out,False)
    audio=decode(out)
    assert np.sqrt(np.mean(audio[int(3.2*SR):int(3.5*SR)]**2))>.12


def test_range_preserves_automation_crossfades_and_effects(library,tmp_path):
    from backend.models import Transition
    a=clip(start=0,end=4,automation=[(0,-24),(4,0)],echo=.25)
    b=clip(id='b',start=0,end=3,position=2,reverb=.2)
    p=Project(clips=[a,b],transitions=[Transition(id='t',from_id=a.id,to_id=b.id,duration=1)])
    full=tmp_path/'full.wav';part=tmp_path/'part.wav'
    render(p,library,full,False);assert render(p,library,part,False,range_start=2,range_end=3.5)==1.5
    y=decode(part);expected=decode(full)[2*SR:round(3.5*SR)]
    assert len(y)==round(1.5*SR)
    assert np.max(abs(y[1000:-1000]-expected[1000:-1000]))<1e-5


def test_range_mp3_duration_and_validation(library,tmp_path):
    from backend.models import RenderRequest,TrackMix
    from pydantic import ValidationError
    p=Project(clips=[clip()]);out=tmp_path/'range.mp3'
    render(p,library,out,True,range_start=.5,range_end=1.5)
    assert abs(probe(out)-1)<.06
    with pytest.raises(ValidationError): RenderRequest(project=p,range_start=1,range_end=3)
    with pytest.raises(ValidationError): Project(tracks=[TrackMix(track=0),TrackMix(track=0)])
