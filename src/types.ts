export interface Source {id:string;name:string;duration:number;status:'analyzing'|'ready'|'error';bpm?:number;key?:string;key_confidence?:number;energy?:number;peaks?:number[];beats?:number[];error?:string;demo?:boolean;size?:number;kind?:'music'|'sfx';builtin?:boolean;origin?:string;origin_url?:string;category?:string}
export interface Clip {id:string;source_id:string;start:number;end:number;position:number;track:number;volume:number;tempo:number;low:number;mid:number;high:number;fade_in:number;fade_out:number;echo:number;reverb:number;muted:boolean;automation:[number,number][];role?:'music'|'sfx'}
export interface Transition {id:string;from_id:string;to_id:string;style:string;duration:number;offset?:number;enabled:boolean;note:string;sound_source_id?:string|null;sound_volume?:number;sound_offset?:number}
export interface TrackMix {track:number;name:string;volume:number;pan:number;muted:boolean;solo:boolean}
export interface LoopRange {start:number;end:number;enabled:boolean}
export const defaultTrack=(track:number):TrackMix=>({track,name:`Audio ${track+1}`,volume:0,pan:0,muted:false,solo:false});
export interface Project {tracks?:TrackMix[];loop?:LoopRange|null;version:number;name:string;clips:Clip[];transitions:Transition[];source_ids:string[];bpm:number;duration:number|null;auto_transitions:boolean}
export const emptyProject:Project={version:1,name:'Untitled session',clips:[],transitions:[],source_ids:[],bpm:120,duration:null,auto_transitions:true};
export const clipDuration=(c:Clip)=>(c.end-c.start)/c.tempo;
export const projectDuration=(p:Project)=>p.duration||Math.max(0,...p.clips.map(c=>c.position+clipDuration(c)));
export function newClip(source:Source,position=0,track=0):Clip{return {id:crypto.randomUUID().slice(0,12),source_id:source.id,start:0,end:Math.min(source.duration,source.kind==='sfx'?60:32),position,track,volume:source.kind==='sfx'?-12:0,tempo:1,low:0,mid:0,high:0,fade_in:.02,fade_out:.04,echo:0,reverb:0,muted:false,automation:[],role:source.kind==='sfx'?'sfx':'music'}}
export function formatTime(s:number,decimals=false){if(!Number.isFinite(s))s=0;return `${Math.floor(s/60).toString().padStart(2,'0')}:${Math.floor(s%60).toString().padStart(2,'0')}${decimals?'.'+Math.floor((s%1)*100).toString().padStart(2,'0'):''}`}
