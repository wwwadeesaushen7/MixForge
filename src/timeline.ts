import {Clip,Project,Source,Transition,clipDuration} from './types';
export const MIN_ZOOM=.15,MAX_ZOOM=160;
export const clamp=(n:number,min:number,max:number)=>Math.max(min,Math.min(max,n));
export function wheelPixels(delta:number,mode:number,page=500){return delta*(mode===1?16:mode===2?page:1)}
export function wheelZoom(zoom:number,delta:number){return clamp(zoom*Math.exp(-clamp(delta,-400,400)*.003),MIN_ZOOM,MAX_ZOOM)}
export function anchoredScroll(scroll:number,oldZoom:number,newZoom:number,screenX:number){return Math.max(0,(scroll+screenX)/oldZoom*newZoom-screenX)}
export function rulerStep(zoom:number){return [.1,.25,.5,1,2,5,10,15,30,60,120,300,600,1200].find(n=>n*zoom>=68)||1200}
export interface Rect {left:number;top:number;right:number;bottom:number}
export function intersects(a:Rect,b:Rect){return a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top}
export function selectionBounds(clips:Clip[]){return {start:Math.min(...clips.map(c=>c.position)),end:Math.max(...clips.map(c=>c.position+clipDuration(c))),firstTrack:Math.min(...clips.map(c=>c.track)),lastTrack:Math.max(...clips.map(c=>c.track))}}
export function snapDelta(clips:Clip[],moving:Clip[],delta:number,zoom:number,bpm:number,playhead:number,enabled:boolean){
 if(!enabled||!moving.length)return {delta,guide:null as number|null};
 const excluded=new Set(moving.map(c=>c.id));const targets=[0,playhead,...clips.filter(c=>!excluded.has(c.id)).flatMap(c=>[c.position,c.position+clipDuration(c)])];
 let distance=9/zoom,best=delta,guide:number|null=null;
 for(const c of moving)for(const edge of [c.position,c.position+clipDuration(c)])for(const target of targets){const d=target-(edge+delta);if(Math.abs(d)<distance){distance=Math.abs(d);best=delta+d;guide=target}}
 if(guide!==null)return {delta:best,guide};
 const grid=60/bpm/4;const start=moving[0].position;const snapped=Math.round((start+delta)/grid)*grid;
 return {delta:snapped-start,guide:snapped};
}
export function moveClips(project:Project,ids:string[],delta:number,trackDelta=0):Project {
 const selected=project.clips.filter(c=>ids.includes(c.id));if(!selected.length)return project;
 const bounds=selectionBounds(selected);
 const dx=clamp(delta,-bounds.start,1800-bounds.end),dy=clamp(trackDelta,-bounds.firstTrack,7-bounds.lastTrack);
 return {...project,duration:null,clips:project.clips.map(c=>ids.includes(c.id)?{...c,position:c.position+dx,track:c.track+dy}:c)};
}
function automationAt(points:[number,number][],time:number){
 const sorted=[...points].sort((a,b)=>a[0]-b[0]);if(!sorted.length)return 0;
 if(time<=sorted[0][0])return sorted[0][1];
 for(let i=1;i<sorted.length;i++)if(time<=sorted[i][0]){const [t0,g0]=sorted[i-1],[t1,g1]=sorted[i];return g0+(g1-g0)*(time-t0)/Math.max(.000001,t1-t0)}
 return sorted.at(-1)![1];
}
export function trimClip(project:Project,id:string,edge:'left'|'right',delta:number,sourceDuration:number):Project {
 return {...project,duration:null,clips:project.clips.map(c=>{
  if(c.id!==id)return c;const duration=clipDuration(c);
  if(edge==='left'){
   const shift=clamp(delta,Math.max(-c.start/c.tempo,-c.position),duration-.05);
   const automation=c.automation.length?[[0,automationAt(c.automation,shift)] as [number,number],...c.automation.filter(([t])=>t>shift).map(([t,g])=>[t-shift,g] as [number,number])]:[];
   return {...c,start:Math.max(0,c.start+shift*c.tempo),position:Math.max(0,c.position+shift),automation};
  }
  return {...c,end:clamp(c.end+delta*c.tempo,c.start+.05*c.tempo,Math.min(sourceDuration,c.start+(1800-c.position)*c.tempo))};
 })};
}
export function deleteClips(project:Project,ids:string[]):Project {const removed=new Set(ids);return {...project,duration:null,clips:project.clips.filter(c=>!removed.has(c.id)),transitions:project.transitions.filter(t=>!removed.has(t.from_id)&&!removed.has(t.to_id))}}
export function splitClips(project:Project,ids:string[],time:number){
 const newIds:string[]=[];const outgoing=new Map<string,string>();
 const clips=project.clips.flatMap(c=>{
  const local=time-c.position;if(!ids.includes(c.id)||local<.05||local>clipDuration(c)-.05)return [c];
  const cut=c.start+local*c.tempo;const rightId=crypto.randomUUID().slice(0,12);newIds.push(rightId);outgoing.set(c.id,rightId);
  const value=automationAt(c.automation,local);
  const leftAuto=c.automation.length?[...c.automation.filter(([t])=>t<local),[local,value] as [number,number]]:[];
  const rightAuto=c.automation.length?[[0,value] as [number,number],...c.automation.filter(([t])=>t>local).map(([t,g])=>[t-local,g] as [number,number])]:[];
  return [{...c,end:cut,fade_out:.01,automation:leftAuto},{...c,id:rightId,start:cut,position:time,fade_in:.01,automation:rightAuto}];
 });
 if(!newIds.length)return {project,ids:[] as string[]};
 if(clips.length>128)throw Error('Splitting would exceed the 128-clip limit.');
 return {project:{...project,clips,transitions:project.transitions.map(t=>outgoing.has(t.from_id)?{...t,from_id:outgoing.get(t.from_id)!}:t)},ids:newIds};
}
export interface ClipClipboard {clips:Clip[];transitions:Transition[]}
export function copyClips(project:Project,ids:string[]):ClipClipboard {const clips=project.clips.filter(c=>ids.includes(c.id));return structuredClone({clips,transitions:project.transitions.filter(t=>ids.includes(t.from_id)&&ids.includes(t.to_id))})}
export function pasteClips(project:Project,clipboard:ClipClipboard,at:number,track?:number){
 if(!clipboard.clips.length)return {project,ids:[] as string[]};
 if(project.clips.length+clipboard.clips.length>128)throw Error('This would exceed the 128-clip limit.');
 const bounds=selectionBounds(clipboard.clips),start=clamp(at,0,1800-(bounds.end-bounds.start));
 const dy=track===undefined?0:clamp(track-bounds.firstTrack,-bounds.firstTrack,7-bounds.lastTrack);
 const map=new Map(clipboard.clips.map(c=>[c.id,crypto.randomUUID().slice(0,12)]));
 const clips=clipboard.clips.map(c=>({...structuredClone(c),id:map.get(c.id)!,position:start+c.position-bounds.start,track:c.track+dy}));
 const transitions=clipboard.transitions.map(t=>({...structuredClone(t),id:crypto.randomUUID().slice(0,12),from_id:map.get(t.from_id)!,to_id:map.get(t.to_id)!}));
 return {project:{...project,duration:null,clips:[...project.clips,...clips],transitions:[...project.transitions,...transitions],source_ids:[...new Set([...project.source_ids,...clips.map(c=>c.source_id),...transitions.flatMap(t=>t.sound_source_id?[t.sound_source_id]:[])])]},ids:clips.map(c=>c.id)};
}
export function patchSelection(project:Project,ids:string[],patch:Partial<Clip>){
 const clips=project.clips.map(c=>ids.includes(c.id)?{...c,...patch}:c);
 if(clips.some(c=>c.end<=c.start||c.position+clipDuration(c)>1800))throw Error('This edit would put a clip outside the timeline limits.');
 return {...project,duration:null,clips};
}
