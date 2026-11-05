import {describe,it,expect} from 'vitest';
import {newClip,clipDuration,projectDuration,emptyProject,formatTime,type Source} from './types';
const source:Source={id:'a'.repeat(24),name:'song.wav',duration:100,status:'ready'};
describe('timeline timing',()=>{
 it('uses source time divided by pitch-preserving speed',()=>{const c={...newClip(source),start:10,end:40,tempo:1.25};expect(clipDuration(c)).toBe(24);expect(projectDuration({...emptyProject,clips:[{...c,position:5}]})).toBe(29)});
 it('keeps a requested auto-remix duration',()=>{expect(projectDuration({...emptyProject,duration:120,clips:[newClip(source)]})).toBe(120)});
 it('allows independent clips from the same source',()=>{const a=newClip(source),b=newClip(source);expect(a.id).not.toBe(b.id);expect(a.source_id).toBe(b.source_id);expect(a.end).toBe(32)});
 it('never creates a section past the source end',()=>{expect(newClip({...source,duration:4}).end).toBe(4)});
 it('formats seeking time with centiseconds',()=>{expect(formatTime(65.25,true)).toBe('01:05.25');expect(formatTime(0)).toBe('00:00')});
});
