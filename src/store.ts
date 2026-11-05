import {useState,useRef,useEffect} from 'react';
import {Project,emptyProject} from './types';
export function useProject(){
 const [project,setState]=useState<Project>(()=>{try{const p=JSON.parse(localStorage.getItem('mixforge-session')||'null');return p?.version===1&&Array.isArray(p.clips)?p:emptyProject}catch{return emptyProject}});
 const ref=useRef(project); const undoStack=useRef<Project[]>([]);const redoStack=useRef<Project[]>([]);const [,refresh]=useState(0);
 const update=(next:Project,record=true)=>{if(record){undoStack.current.push(ref.current);undoStack.current=undoStack.current.slice(-60);redoStack.current=[]}ref.current=next;setState(next)};
 const record=(before:Project)=>{undoStack.current.push(before);undoStack.current=undoStack.current.slice(-60);redoStack.current=[];refresh(n=>n+1)};
 const undo=()=>{const prev=undoStack.current.pop();if(prev){redoStack.current.push(ref.current);ref.current=prev;setState(prev)}};
 const redo=()=>{const next=redoStack.current.pop();if(next){undoStack.current.push(ref.current);ref.current=next;setState(next)}};
 useEffect(()=>{const timer=setTimeout(()=>{try{localStorage.setItem('mixforge-session',JSON.stringify(project))}catch{window.dispatchEvent(new Event('mixforge-storage-error'))}},300);return()=>clearTimeout(timer)},[project]);
 return {project,update,undo,redo,record,ref,canUndo:undoStack.current.length>0,canRedo:redoStack.current.length>0};
}
