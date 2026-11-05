from typing import Literal
from pydantic import BaseModel, Field, model_validator
import math

class Clip(BaseModel):
    id: str = Field(max_length=80)
    source_id: str = Field(pattern=r'^[a-f0-9]{24}$')
    start: float = Field(ge=0, le=1800)
    end: float = Field(gt=0, le=1800)
    position: float = Field(ge=0, le=1800)
    track: int = Field(default=0, ge=0, le=7)
    volume: float = Field(default=0, ge=-60, le=12)
    tempo: float = Field(default=1, ge=.75, le=1.25)
    low: float = Field(default=0, ge=-12, le=12)
    mid: float = Field(default=0, ge=-12, le=12)
    high: float = Field(default=0, ge=-12, le=12)
    fade_in: float = Field(default=.02, ge=0, le=30)
    fade_out: float = Field(default=.04, ge=0, le=30)
    echo: float = Field(default=0, ge=0, le=.7)
    reverb: float = Field(default=0, ge=0, le=.7)
    muted: bool = False
    role: Literal['music','sfx'] = 'music'
    automation: list[tuple[float,float]] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def valid(self):
        if self.end <= self.start: raise ValueError('Clip end must be after start')
        if self.position + self.duration > 1800: raise ValueError('Timeline exceeds 30 minutes')
        for t, gain in self.automation:
            if not math.isfinite(t) or not math.isfinite(gain) or t < 0 or abs(gain)>60: raise ValueError('Invalid automation point')
        return self

    @property
    def duration(self): return (self.end-self.start)/self.tempo

class Transition(BaseModel):
    id: str
    from_id: str
    to_id: str
    style: Literal['Smart','Smooth','DJ Beat Match','Echo/Reverb','Bass Swap'] = 'Smart'
    duration: float = Field(default=4, ge=.01, le=30)
    offset: float = Field(default=0, ge=0, le=30)
    enabled: bool = True
    note: str = ''
    sound_source_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{24}$')
    sound_volume: float = Field(default=-12, ge=-48, le=6)
    sound_offset: float = Field(default=0, ge=-30, le=30)

class TrackMix(BaseModel):
    track: int = Field(ge=0, le=7)
    name: str = Field(default='', max_length=40)
    volume: float = Field(default=0, ge=-60, le=12)
    pan: float = Field(default=0, ge=-1, le=1)
    muted: bool = False
    solo: bool = False

class LoopRange(BaseModel):
    start: float = Field(default=0, ge=0, le=1800)
    end: float = Field(default=8, gt=0, le=1800)
    enabled: bool = False

    @model_validator(mode='after')
    def valid(self):
        if self.end-self.start < .05: raise ValueError('Loop end must be at least 0.05 seconds after its start')
        return self

class Project(BaseModel):
    version: int = 1
    name: str = Field(default='Untitled session', max_length=120)
    clips: list[Clip] = Field(default_factory=list, max_length=128)
    transitions: list[Transition] = Field(default_factory=list, max_length=128)
    source_ids: list[str] = Field(default_factory=list, max_length=64)
    bpm: float = Field(default=120, ge=40, le=240)
    duration: float | None = Field(default=None, gt=0, le=1800)
    auto_transitions: bool = True
    tracks: list[TrackMix] = Field(default_factory=list, max_length=8)
    loop: LoopRange | None = None

    @model_validator(mode='after')
    def unique_clips(self):
        track_ids=[t.track for t in self.tracks]
        if len(track_ids)!=len(set(track_ids)): raise ValueError('Each mixer track needs a unique number')
        ids=[c.id for c in self.clips]
        if len(ids)!=len(set(ids)): raise ValueError('Each clip needs a unique identifier')
        for t in self.transitions:
            if t.from_id not in ids or t.to_id not in ids or t.from_id==t.to_id: raise ValueError('Transition references an invalid clip pair')
        return self

class RenderRequest(BaseModel):
    project: Project
    format: Literal['wav','mp3'] = 'wav'
    normalize: bool = True
    range_start: float = Field(default=0, ge=0, le=1800)
    range_end: float | None = Field(default=None, gt=0, le=1800)

    @model_validator(mode='after')
    def valid_range(self):
        total=self.project.duration or max((c.position+c.duration for c in self.project.clips),default=0)
        end=total if self.range_end is None else self.range_end
        if self.project.clips and (end>total+.00001 or end-self.range_start<.05):
            raise ValueError('Choose an audio range of at least 0.05 seconds inside the remix')
        return self

class AutoRequest(BaseModel):
    source_ids: list[str] = Field(min_length=1, max_length=64)
    duration: float = Field(default=120, ge=8, le=1800)
    style: Literal['Smooth','Party','High Energy','Chill'] = 'Smooth'
    transition: float = Field(default=4, ge=.1, le=20)
    target_bpm: float | None = Field(default=None, ge=50, le=200)
    keep_order: bool = False
    seed: int | None = None

class TransitionRequest(BaseModel):
    project: Project
    from_id: str | None = None
    to_id: str | None = None
    style: Literal['Smart','Smooth','DJ Beat Match','Echo/Reverb','Bass Swap'] = 'Smart'
    duration: float | None = Field(default=None, ge=.1, le=30)
    match_tempo: bool = False

class MyinstantsImportRequest(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
