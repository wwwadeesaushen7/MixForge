import {describe,it,expect} from 'vitest';
import {shortcutAction} from './shortcuts';
const key=(value:string,extra:Record<string,unknown>={})=>shortcutAction({key:value,code:value===' '?'Space':'Key'+value.toUpperCase(),...extra});
describe('workstation keyboard shortcuts',()=>{
 it('maps transport and clip editing',()=>{expect(key(' ')).toBe('play');expect(key('s')).toBe('split');expect(key('b')).toBe('tool-blade');expect(key('h')).toBe('tool-hand');expect(key('v')).toBe('tool-select');expect(key('v',{ctrlKey:true})).toBe('paste');expect(key('a',{ctrlKey:true})).toBe('select-all');expect(key('s',{ctrlKey:true})).toBe('save');expect(key('d',{ctrlKey:true})).toBe('duplicate');expect(key('Delete')).toBe('delete')});
 it('keeps modifier commands distinct',()=>{expect(key('t')).toBe('transition');expect(key('T',{shiftKey:true})).toBe('transition-all');expect(key('z',{metaKey:true,shiftKey:true})).toBe('redo');expect(key('f',{ctrlKey:true})).toBeNull();expect(key('ArrowLeft',{shiftKey:true})).toBe('nudge-back')});
 it('maps shifted digit codes independently of punctuation',()=>{expect(key('!',{code:'Digit1',shiftKey:true})).toBe('insert-1');expect(key('8',{code:'Digit8'})).toBe('pad-8');expect(key('/',{code:'Slash',shiftKey:true})).toBe('help')});
 it('ignores composing input, Alt combinations, and repeat one-shots',()=>{expect(key('s',{isComposing:true})).toBeNull();expect(key('ArrowLeft',{altKey:true})).toBeNull();expect(key('s',{repeat:true})).toBeNull();expect(key('ArrowLeft',{repeat:true})).toBe('seek-back')});
});
