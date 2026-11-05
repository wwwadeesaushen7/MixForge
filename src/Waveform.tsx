import {useEffect,useRef,memo} from 'react';
import WaveSurfer from 'wavesurfer.js';
import {Source,Clip} from './types';
export function Waveform({source,clip,onSeek}:{source:Source;clip?:Clip;onSeek?:(t:number)=>void}){
 const el=useRef<HTMLDivElement>(null);const seekRef=useRef(onSeek);seekRef.current=onSeek;
 useEffect(()=>{if(!el.current||!source.peaks?.length)return;
 const ws=WaveSurfer.create({container:el.current,height:66,waveColor:'#c5d09b',progressColor:'#ebae6d',cursorColor:'#f6b56e',barWidth:2,barGap:1,normalize:true,peaks:[source.peaks],duration:source.duration,interact:true});
 ws.on('interaction',t=>seekRef.current?.(t));return()=>ws.destroy();},[source.id,source.peaks]);
 return <div className="source-wave"><div ref={el}/>{clip&&<div className="source-selection" style={{left:clip.start/source.duration*100+'%',width:(clip.end-clip.start)/source.duration*100+'%'}}/>}</div>
}
function ClipWaveView({source,clip}:{source?:Source;clip:Clip}){
 const points=source?.peaks||[];const start=Math.floor(clip.start/(source?.duration||1)*points.length),end=Math.ceil(clip.end/(source?.duration||1)*points.length);
 const cut=points.slice(start,end),bins=Math.min(160,cut.length);
 return <svg viewBox="0 0 500 55" preserveAspectRatio="none" className="clip-wave" aria-hidden="true">{Array.from({length:bins},(_,i)=>{const v=Math.max(.025,...cut.slice(Math.floor(i*cut.length/bins),Math.ceil((i+1)*cut.length/bins)));return <line key={i} x1={i/Math.max(1,bins-1)*500} x2={i/Math.max(1,bins-1)*500} y1={27.5-v*25} y2={27.5+v*25} stroke="currentColor" strokeWidth="1.5"/>})}</svg>
}

export const ClipWave=memo(ClipWaveView,(a,b)=>a.source?.peaks===b.source?.peaks&&a.source?.duration===b.source?.duration&&a.clip.start===b.clip.start&&a.clip.end===b.clip.end);
