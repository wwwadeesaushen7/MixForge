"""Disk-backed, 44.1 kHz stereo audio rendering. Originals are always read-only."""
from pathlib import Path
import json, subprocess, uuid, tempfile, math, random
import numpy as np
from scipy import signal
from .models import Clip, Project, Transition, AutoRequest

SR = 44100
ANALYSIS_SR = 11025

def run(args):
    p = subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads','2','-filter_threads','2',*map(str,args)], capture_output=True, timeout=900)
    if p.returncode: raise ValueError('Audio processing failed: '+p.stderr.decode(errors='replace')[-700:])

def probe(path):
    p = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(path)], capture_output=True, timeout=30)
    try:
        info=json.loads(p.stdout)
        duration=float(info['format']['duration'])
        if not any(s['codec_type']=='audio' for s in info['streams']): raise ValueError()
        if not .1 <= duration <= 1800: raise ValueError()
        return duration
    except Exception: raise ValueError('Unsupported or damaged audio. Use a valid audio file up to 30 minutes.')

def analyze(path, progress=lambda x,m:None):
    import librosa
    duration=probe(path)
    progress(.12,'Decoding analysis audio')
    with tempfile.TemporaryDirectory() as tmp:
        raw=Path(tmp)/'mono.f32'
        run(['-i',path,'-vn','-ac',1,'-ar',ANALYSIS_SR,'-f','f32le',raw])
        y=np.fromfile(raw,dtype=np.float32)
    progress(.3,'Finding beats and musical sections')
    hop=256
    onset=librosa.onset.onset_strength(y=y,sr=ANALYSIS_SR,hop_length=hop)
    tempo, frames=librosa.beat.beat_track(onset_envelope=onset,sr=ANALYSIS_SR,hop_length=hop,trim=False)
    beats=librosa.frames_to_time(frames,sr=ANALYSIS_SR,hop_length=hop).tolist()
    bpm=float(np.asarray(tempo).ravel()[0]) if len(beats)>3 else None
    if bpm and not 45<=bpm<=220: bpm=None
    confidence=0.
    if bpm and len(beats)>7 and len(onset):
        valid_frames=np.asarray(frames)[np.asarray(frames)<len(onset)]
        prominence=float(np.mean(onset[valid_frames])/(np.mean(onset)+1e-8)) if len(valid_frames) else 0
        intervals=np.diff(beats)
        regularity=max(0.,1.-4*float(np.std(intervals)/(np.mean(intervals)+1e-8)))
        confidence=float(np.clip((prominence-1)/2,0,1)*regularity)
    progress(.62,'Estimating key and energy')
    # Key is approximate: classical pitch-class profiles, with a confidence score.
    chroma=librosa.feature.chroma_stft(y=y,sr=ANALYSIS_SR,hop_length=1024,n_fft=2048).mean(axis=1)
    major=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
    minor=np.array([6.33,2.68,3.52,5.38,2.6,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
    scores=[float(np.corrcoef(chroma,np.roll(profile,k))[0,1]) if np.std(chroma)>1e-8 else 0 for profile in (major,minor) for k in range(12)]
    key_idx=int(np.argmax(scores)); names=['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B']
    key=names[key_idx%12]+(' minor' if key_idx>=12 else ' major') if max(scores)>.2 else 'Uncertain'
    rms=librosa.feature.rms(y=y,frame_length=2048,hop_length=hop)[0]
    sections=[]
    # Phrase grid is an estimate, never claimed as detected downbeats.
    points=beats[::16] if bpm and confidence>.4 and len(beats)>16 else list(np.arange(0,duration,4))
    for t in points:
        ix=int(t*ANALYSIS_SR/hop); stop=min(len(rms),ix+int(8*ANALYSIS_SR/hop))
        sections.append({'time':round(t,4),'energy':float(np.mean(rms[ix:stop])) if stop>ix else 0})
    # 1600 peak bins stay tiny; browser never decodes the full song for its waveform.
    chunks=np.array_split(y,1600)
    peaks=[round(float(np.max(np.abs(c))),5) if len(c) else 0 for c in chunks]
    peak=max(peaks) or 1; peaks=[v/peak for v in peaks]
    progress(.95,'Caching analysis')
    return {'duration':duration,'bpm':round(bpm,2) if bpm else None,'beats':beats,'beat_confidence':confidence,'key':key,'key_confidence':round(max(scores),3),'key_index':key_idx,'energy':float(np.sqrt(np.mean(y*y))),'onset_strength':[float(v) for v in onset[::max(1,len(onset)//600)]],'sections':sections,'peaks':peaks}

def plan_transitions(project, library, style='Smart', duration=None, from_id=None, to_id=None, match_tempo=False):
    p=project.model_copy(deep=True)
    clips=sorted((c for c in p.clips if c.role!='sfx'),key=lambda c:(c.position,c.track))
    pairs=[(a,b) for a,b in zip(clips,clips[1:]) if (not from_id or a.id==from_id) and (not to_id or b.id==to_id)]
    if from_id and not pairs: raise ValueError('Choose two adjacent clips in timeline order.')
    messages=[]
    for a,b in pairs:
        available=min(a.position+a.duration,b.position+b.duration)-max(a.position,b.position)
        if available<=.015:
            # No extra source audio is consumed and no arrangement is moved.
            a.fade_out=max(a.fade_out,.03); b.fade_in=max(b.fade_in,.03)
            p.transitions=[t for t in p.transitions if (t.from_id,t.to_id)!=(a.id,b.id)]
            messages.append(f'{a.id} → {b.id}: no overlap; applied short boundary fades. Overlap these clips for a crossfade.')
            continue
        aa=library[a.source_id]; bb=library[b.source_id]
        tempo_note=''
        if match_tempo and aa.get('bpm') and bb.get('bpm'):
            proposed=aa['bpm']*a.tempo/bb['bpm']
            if .94 <= proposed/b.tempo <= 1.06 and .75 <= proposed <= 1.25 and b.position+(b.end-b.start)/proposed<=1800:
                b.tempo=proposed
                tempo_note=f' Incoming clip tempo set to {proposed*100:.1f}% with pitch preserved.'
            else: tempo_note=' BPM difference exceeds the modest tempo range; existing clip tempo retained.'
            available=min(a.position+a.duration,b.position+b.duration)-max(a.position,b.position)
        bpm=(bb.get('bpm') or aa.get('bpm') or 120)*b.tempo
        chosen=style
        if style=='Smart':
            key_gap=abs((aa.get('key_index',0)%12)-(bb.get('key_index',0)%12))
            energy_ratio=max(aa.get('energy',.1),bb.get('energy',.1))/max(.001,min(aa.get('energy',.1),bb.get('energy',.1)))
            chosen='Smooth' if energy_ratio>2.5 else 'Bass Swap' if key_gap>3 else ('DJ Beat Match' if aa.get('bpm') and bb.get('bpm') and abs(aa['bpm']-bb['bpm'])<8 else 'Smooth')
        desired=duration or (8*60/bpm if chosen=='DJ Beat Match' else 4)
        offset=0.
        if chosen=='DJ Beat Match' and bb.get('beat_confidence',0)>.5:
            beats=bb.get('beats',[])
            phrase=beats[::16]
            def candidates(points):
                return [b.position+(beat-b.start)/b.tempo-max(a.position,b.position) for beat in points if 0 <= b.position+(beat-b.start)/b.tempo-max(a.position,b.position) <= min(available*.25,2)]
            options=candidates(phrase) or candidates(beats)
            if options: offset=min(options)
        length=min(desired,max(.01,available-offset),a.duration/2,b.duration/2)
        note=f'{length:.2f}s equal-power crossfade. Sections and timeline positions preserved.'
        if length<desired-.01: note+=' Limited to existing overlap.'
        if offset: note+=f' Fade begins {offset:.2f}s into the overlap on an estimated incoming beat.'
        note+=tempo_note
        if chosen=='DJ Beat Match' and not match_tempo:
            # Manual clip speed is deliberately untouched; user can change tempo explicitly.
            note+=' Existing cut points retained; use clip tempo controls for beat matching.'
        previous=next((t for t in p.transitions if (t.from_id,t.to_id)==(a.id,b.id)),None)
        sound_settings={k:getattr(previous,k) for k in ('sound_source_id','sound_volume','sound_offset')} if previous else {}
        t=Transition(id=uuid.uuid4().hex[:12],from_id=a.id,to_id=b.id,style=chosen,duration=length,offset=offset,note=note,**sound_settings)
        p.transitions=[old for old in p.transitions if (old.from_id,old.to_id)!=(a.id,b.id)]+[t]
    return p,messages

def arrange(req:AutoRequest, library):
    rng=random.Random(req.seed if req.seed is not None else uuid.uuid4().int)
    ids=list(req.source_ids)
    for sid in ids:
        if sid in library and library[sid].get('kind')=='sfx': raise ValueError('Choose music sources for Auto Remix. Add sound effects in the manual timeline.')
        if sid not in library or library[sid].get('status')!='ready': raise ValueError('Wait for every selected song to finish analysis.')
    if not req.keep_order:
        rng.shuffle(ids)
        if req.style in ['High Energy','Party']: ids.sort(key=lambda s: library[s]['energy']+rng.uniform(-.025,.025),reverse=req.style=='High Energy')
        elif req.style=='Chill': ids.sort(key=lambda s:library[s]['energy']+rng.uniform(-.02,.02))
    valid=[library[s]['bpm'] for s in ids if library[s].get('bpm')]
    target=req.target_bpm or (float(np.median(valid)) if valid else 120)
    p=Project(name=f'{req.style} remix',source_ids=ids,bpm=target,duration=req.duration)
    position=0.; index=0
    while position<req.duration-.02 and index<128:
        sid=ids[index%len(ids)]; s=library[sid]
        tempo=float(np.clip(target/(s.get('bpm') or target),.94,1.06))
        wanted=32*60/target if req.style in ['Party','High Energy'] else 64*60/target
        wanted=min(wanted,s['duration']/tempo,req.duration-position)
        if wanted<.03: break
        candidates=[sec for sec in s.get('sections',[]) if sec['time']+wanted*tempo<=s['duration']]
        if candidates:
            candidates.sort(key=lambda a:a['energy'],reverse=req.style!='Chill')
            start=rng.choice(candidates[:max(1,len(candidates)//2)])['time']
        else: start=0
        end=min(s['duration'],start+wanted*tempo)
        c=Clip(id=uuid.uuid4().hex[:12],source_id=sid,start=start,end=end,position=position,track=index%3,tempo=tempo)
        p.clips.append(c)
        finish=position+c.duration
        if finish>=req.duration-.02: break
        overlap=min(req.transition,c.duration*.25,(s['duration']/tempo)*.2)
        # Beat-quantized overlap, with estimated phrase-aligned source starts.
        beat=60/target
        overlap=max(.05,round(overlap/beat)*beat)
        position=finish-min(overlap,c.duration*.4); index+=1
    if not p.clips or p.clips[-1].position+p.clips[-1].duration < req.duration-.05:
        raise ValueError('This duration needs more than 128 clips. Use longer sources or a shorter remix.')
    p,_=plan_transitions(p,library,'Smart',req.transition)
    return p

def fade_envelopes(clip, project, n):
    env=np.ones(n,dtype=np.float32)
    by_id={c.id:c for c in project.clips}
    def usable(t):
        a,b=by_id.get(t.from_id),by_id.get(t.to_id)
        return a and b and min(a.position+a.duration,b.position+b.duration)-max(a.position,b.position)>t.offset
    active = [t for t in project.transitions if project.auto_transitions and t.enabled and usable(t)]
    fade_in = 0 if any(t.to_id==clip.id for t in active) else clip.fade_in
    fade_out = 0 if any(t.from_id==clip.id for t in active) else clip.fade_out
    for duration,start,fadein in [(fade_in,0,True),(fade_out,max(0,n-round(fade_out*SR)),False)]:
        count=min(n,round(duration*SR))
        if count:
            curve=np.sin(np.linspace(0,math.pi/2,count,dtype=np.float32)) if fadein else np.cos(np.linspace(0,math.pi/2,count,dtype=np.float32))
            if fadein: env[:count]*=curve
            else: env[-count:]*=curve
    if project.auto_transitions:
        by_id={c.id:c for c in project.clips}
        for t in project.transitions:
            if not t.enabled or clip.id not in [t.from_id,t.to_id]: continue
            a,b=by_id.get(t.from_id),by_id.get(t.to_id)
            if not a or not b: continue
            overlap_end=min(a.position+a.duration,b.position+b.duration)
            overlap_start=max(a.position,b.position)
            overlap_start+=t.offset
            dur=min(t.duration,overlap_end-overlap_start)
            if dur<=0: continue
            # Anchor at incoming start and extend the outgoing fade to its end.
            begin=max(0,round((overlap_start-clip.position)*SR))
            finish=min(n,begin+round(dur*SR))
            if finish<=begin: continue
            if clip.id==a.id:
                env[begin:finish]*=np.cos(np.linspace(0,math.pi/2,finish-begin)); env[finish:]=0
            else:
                env[:begin]=0; env[begin:finish]*=np.sin(np.linspace(0,math.pi/2,finish-begin))
    if clip.automation:
        points=sorted(clip.automation)
        env*=np.power(10,np.interp(np.arange(n)/SR,[x[0] for x in points],[x[1] for x in points])/20).astype(np.float32)
    return env

def transition_sound_clips(project:Project, library):
    """Overlay attached one-shots without moving or extending the music timeline."""
    if not project.auto_transitions: return []
    clips=[]; by_id={c.id:c for c in project.clips}
    total=project.duration or max((c.position+c.duration for c in project.clips),default=0)
    for t in project.transitions:
        if not t.enabled or not t.sound_source_id: continue
        if t.sound_source_id not in library: raise ValueError('Transition sound is missing. Re-import the sound effect.')
        a,b=by_id.get(t.from_id),by_id.get(t.to_id)
        if not a or not b: continue
        start=max(a.position,b.position)+t.offset
        overlap=min(a.position+a.duration,b.position+b.duration)-start
        if overlap<=0: continue
        at=start+t.sound_offset; source_start=max(0,-at); at=max(0,at)
        end=min(library[t.sound_source_id]['duration'],source_start+max(0,total-at))
        if end-source_start<.01: continue
        clips.append(Clip(id='sound-'+uuid.uuid5(uuid.NAMESPACE_URL,t.id).hex[:16],source_id=t.sound_source_id,start=source_start,end=end,position=at,track=7,volume=t.sound_volume,role='sfx',fade_in=.005,fade_out=.04))
    return clips

def render(project:Project, library, destination:Path, normalize=True, progress=lambda x,m:None, range_start=0, range_end=None):
    if not project.clips: raise ValueError('Add at least one clip before rendering.')
    mixer={t.track:t for t in project.tracks}
    solo=any(t.solo for t in project.tracks)
    def audible(c):
        track=mixer.get(c.track)
        return not c.muted and not (track and track.muted) and (not solo or bool(track and track.solo))
    audible_ids={c.id for c in project.clips if audible(c)}
    effective=project.model_copy(update={'transitions':[t for t in project.transitions if t.from_id in audible_ids and t.to_id in audible_ids]})
    render_clips=[c for c in project.clips+transition_sound_clips(effective,library) if audible(c)]
    for c in render_clips:
        if c.source_id not in library: raise ValueError('Source file missing. Re-import the original file.')
        if c.end>library[c.source_id]['duration']+.025: raise ValueError('Clip extends beyond source audio.')
    total=project.duration or max(c.position+c.duration for c in project.clips)
    end=total if range_end is None else range_end
    if not 0<=range_start<end<=total or end-range_start<.05: raise ValueError('Audio range is outside the remix')
    output_duration=end-range_start
    count=round(total*SR)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmpdir:
        tmp=Path(tmpdir)
        mix=np.memmap(tmp/'mix.f32',dtype='float32',mode='w+',shape=(count,2)); mix[:]=0
        for i,c in enumerate(render_clips):
            progress(.04+.72*i/len(render_clips),f'Rendering clip {i+1} of {len(render_clips)}')
            if c.position>=end or c.position+c.duration<=range_start: continue
            filters=[f'atempo={c.tempo}',f'bass=g={c.low}',f'equalizer=f=1000:t=q:w=1:g={c.mid}',f'treble=g={c.high}']
            if c.echo: filters.append(f'aecho=0.8:0.9:230|460:{c.echo*.5}|{c.echo*.25}')
            if c.reverb: filters.append(f'aecho=0.8:0.9:37|59|83:{c.reverb*.5}|{c.reverb*.35}|{c.reverb*.2}')
            by_id={item.id:item for item in project.clips}
            def has_overlap(t):
                a,b=by_id[t.from_id],by_id[t.to_id]
                return min(a.position+a.duration,b.position+b.duration)>max(a.position,b.position)+t.offset
            active=[t for t in effective.transitions if t.enabled and project.auto_transitions and c.id in [t.from_id,t.to_id] and has_overlap(t)]
            if any(t.style=='Echo/Reverb' and t.from_id==c.id for t in active): filters.append('aecho=0.8:0.9:180|360:0.22|0.1')
            raw=tmp/'clip.f32'
            run(['-ss',c.start,'-t',c.end-c.start,'-i',library[c.source_id]['path'],'-vn','-af',','.join(filters),'-ac',2,'-ar',SR,'-f','f32le',raw])
            audio=np.fromfile(raw,dtype=np.float32).reshape(-1,2)[:round(c.duration*SR)]
            if not len(audio): continue
            # Bounded per-clip loudness matching; user gain is preserved relative to matching.
            rms=float(np.sqrt(np.mean(np.square(audio,dtype=np.float64))))
            if normalize and c.role!='sfx' and rms>1e-7: audio*=float(np.clip(.1/rms,10**(-9/20),10**(9/20)))
            track=mixer.get(c.track)
            audio*=10**((c.volume+(track.volume if track else 0))/20)
            # Stereo balance preserves both channels at center.
            pan=track.pan if track else 0
            audio[:,0]*=math.cos(max(0,pan)*math.pi/2)
            audio[:,1]*=math.cos(max(0,-pan)*math.pi/2)
            env=fade_envelopes(c,effective,len(audio))
            if any(t.style=='Bass Swap' for t in active):
                # A low-band exchange driven by the real transition amplitude envelope.
                low=signal.sosfilt(signal.butter(2,220,fs=SR,output='sos'),audio,axis=0).astype(np.float32)
                audio=audio-low*(1-env[:,None])
            audio*=env[:,None]
            offset=round(c.position*SR); stop=min(count,offset+len(audio))
            if stop>offset: mix[offset:stop]+=audio[:stop-offset]
        mix.flush(); del mix
        progress(.84,'Normalizing loudness and limiting peaks')
        filters='loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.8913:level=false:latency=true' if normalize else 'alimiter=limit=0.8913:level=false:latency=true'
        encoding=['-c:a','libmp3lame','-b:a','320k'] if destination.suffix=='.mp3' else ['-c:a','pcm_s24le']
        run(['-f','f32le','-ar',SR,'-ac',2,'-ss',range_start,'-t',output_duration,'-i',tmp/'mix.f32','-af',filters,'-ar',SR,'-ac',2,'-t',output_duration,*encoding,destination])
    progress(1,'Ready to play')
    return output_duration
