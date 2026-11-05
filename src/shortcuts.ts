export type ShortcutAction = 'loop'|'copy'|'cut'|'paste'|'select-all'|'tool-select'|'tool-blade'|'tool-hand'|'play'|'split'|'duplicate'|'delete'|'mute'|'snap'|'undo'|'redo'|'save'|'open'|'export'|'fit'|'zoom-in'|'zoom-out'|'seek-back'|'seek-forward'|'nudge-back'|'nudge-forward'|'start'|'end'|'previous'|'next'|'transition'|'transition-all'|'help'|'escape'|`pad-${number}`|`insert-${number}`;
export interface KeyInput {key:string;code:string;ctrlKey?:boolean;metaKey?:boolean;shiftKey?:boolean;altKey?:boolean;repeat?:boolean;isComposing?:boolean}
export function shortcutAction(e:KeyInput):ShortcutAction|null {
 if(e.altKey||e.isComposing)return null;
 const key=e.key.toLowerCase();let action:ShortcutAction|null=null;
 if(e.ctrlKey||e.metaKey){const commands:Record<string,ShortcutAction>={a:'select-all',c:'copy',x:'cut',v:'paste',s:'save',o:'open',e:'export',d:'duplicate',y:'redo',z:e.shiftKey?'redo':'undo'};action=commands[key]||null;}
 else if(e.shiftKey&&e.code==='Slash')action='help';
 else if(/^Digit[1-8]$/.test(e.code))action=`${e.shiftKey?'insert':'pad'}-${e.code.slice(-1)}` as ShortcutAction;
 else {const keys:Record<string,ShortcutAction>={l:'loop',v:'tool-select',b:'tool-blade',h:'tool-hand',' ':'play',s:'split',m:'mute',g:'snap',f:'fit',t:e.shiftKey?'transition-all':'transition',delete:'delete',backspace:'delete',home:'start',end:'end',arrowleft:e.shiftKey?'nudge-back':'seek-back',arrowright:e.shiftKey?'nudge-forward':'seek-forward','=':'zoom-in','+':'zoom-in','-':'zoom-out','_':'zoom-out','[':'previous',']':'next','?':'help',escape:'escape'};action=keys[key]||null;}
 if(e.repeat&&action&&!['seek-back','seek-forward','nudge-back','nudge-forward','zoom-in','zoom-out'].includes(action))return null;
 return action;
}
export const SHORTCUTS=[
 ['L','Toggle saved loop range'],['V / B / H','Select / Cut / Hand tool'],['Ctrl + A','Select all timeline clips'],['Ctrl + C / X / V','Copy / cut / paste timeline clips'],['Space','Play / pause'],['S','Split selected clip at playhead'],['Ctrl + D','Duplicate selected clip'],['Delete','Remove selected clip'],['M','Mute / unmute selected clip'],['G','Toggle beat snapping'],['← / →','Seek one beat'],['Shift + ← / →','Move selected clip by a quarter beat'],['Home / End','Go to start / end'],['[ / ]','Select previous / next clip'],['+ / −','Zoom in / out'],['F','Fit the timeline'],['T / Shift + T','Auto Transition selected pair / all'],['Ctrl + Z / Ctrl + Y','Undo / redo'],['Ctrl + S / Ctrl + O','Save / open project'],['Ctrl + E','Open export'],['1–8','Audition sound pad (Sound FX tab)'],['Shift + 1–8','Place sound pad at playhead (Sound FX tab)'],['Esc','Stop sound pads / deselect'],['?','Show this guide'],
];
