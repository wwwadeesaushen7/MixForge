import {useEffect,useLayoutEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
export interface MenuItem {label:string;icon?:ReactNode;keys?:string;disabled?:boolean;danger?:boolean;separator?:boolean;onSelect:()=>void}
export function ContextMenu({x,y,items,onClose}:{x:number;y:number;items:MenuItem[];onClose:()=>void}){
 const ref=useRef<HTMLDivElement>(null);const previousFocus=useRef(document.activeElement);const [position,setPosition]=useState({left:x,top:y});
 useLayoutEffect(()=>{const rect=ref.current?.getBoundingClientRect();if(rect)setPosition({left:Math.max(8,Math.min(x,innerWidth-rect.width-8)),top:Math.max(8,Math.min(y,innerHeight-rect.height-8))});ref.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus()},[x,y]);
 useEffect(()=>{const previous=previousFocus.current;const outside=(e:PointerEvent)=>{if(!ref.current?.contains(e.target as Node))onClose()};const resize=()=>onClose();window.addEventListener('pointerdown',outside,true);window.addEventListener('resize',resize);return()=>{window.removeEventListener('pointerdown',outside,true);window.removeEventListener('resize',resize);if(previous instanceof HTMLElement&&document.activeElement===document.body)previous.focus()}},[onClose]);
 return createPortal(<div ref={ref} role="menu" aria-label="Timeline actions" className="timeline-context-menu" style={position} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget as Node))onClose()}} onContextMenu={e=>e.preventDefault()} onKeyDown={e=>{
  e.stopPropagation();if(e.key==='Escape'){e.preventDefault();onClose()}
  if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();const buttons=[...ref.current!.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];const index=buttons.indexOf(document.activeElement as HTMLButtonElement);const next=e.key==='Home'?0:e.key==='End'?buttons.length-1:(index+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length;buttons[next]?.focus()}
 }}>{items.map((item,index)=><div key={item.label}>{item.separator&&index>0&&<div role="separator" className="context-separator"/>}<button role="menuitem" disabled={item.disabled} className={item.danger?'danger':''} onClick={()=>{item.onSelect();onClose()}}>{item.icon}<span>{item.label}</span>{item.keys&&<kbd>{item.keys}</kbd>}</button></div>)}</div>,document.body);
}
