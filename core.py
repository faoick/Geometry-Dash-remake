"""Independent level reader and fixed-step simulation. No original game code.

This is an experimental compatibility engine, not an exact GD implementation.
Units are GD editor units (one block = 30), y points up, simulation is 240 Hz.
"""
from __future__ import annotations

import base64
import bisect
import math
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

HZ = 240
SOLIDS = set(range(1, 8)) | {40, 83}
SPIKES = {8, 39, 103}
HAZARDS = SPIKES | {9, 52, 53, 54}
PORTALS = {10, 11, 12, 13}
TRIGGERS = set(range(22, 29)) | {29, 30, 31, 32, 33, 34, 62, 65}
DECOR = set(range(15, 22)) | {41, 110}
SUPPORTED = SOLIDS | HAZARDS | PORTALS | TRIGGERS | DECOR | {35, 36, 67, 142}
NAMES = ['Stereo Madness', 'Back On Track', 'Polargeist', 'Dry Out', 'Base After Base',
         "Can't Let Go", 'Jumper', 'Time Machine', 'Cycles', 'xStep', 'Clutterfunk',
         'Theory of Everything', 'Electroman Adventures', 'Clubstep', 'Electrodynamix',
         'Hexagon Force', 'Blast Processing', 'Theory of Everything 2',
         'Geometrical Dominator', 'Deadlocked', 'Fingerdash', 'Dash']
SONGS = ['StereoMadness', 'BackOnTrack', 'Polargeist', 'DryOut', 'BaseAfterBase',
         'CantLetGo', 'Jumper', 'TimeMachine', 'Cycles', 'xStep', 'Clutterfunk',
         'TheoryOfEverything', 'Electroman', 'Clubstep', 'Electrodynamix',
         'HexagonForce', 'BlastProcessing', 'TheoryOfEverything2',
         'GeometricalDominator', 'Deadlocked', 'Fingerdash', 'Dash']


def pairs(s: str) -> dict[str, str]:
    parts = s.split(',')
    if len(parts) % 2:
        raise ValueError('Нечётное число полей объекта уровня')
    return dict(zip(parts[::2], parts[1::2]))


def decode_level(text: str) -> str:
    text = text.strip().strip('\x00')
    if ';' in text and ',' in text:
        return text
    for prefix in ('', 'H4sIAAAAAAAAA'):
        try:
            encoded = prefix + text
            packed = base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True)
            unpacker = zlib.decompressobj(47)
            data = unpacker.decompress(packed, 32 * 1024 * 1024)
            if not unpacker.eof:
                raise ValueError('Уровень повреждён или превышает 32 МБ')
            result = data.decode('utf-8').rstrip('\x00')
            if ';' in result and ',' in result:
                return result
        except (ValueError, zlib.error, UnicodeError):
            pass
    raise ValueError('Не удалось декодировать уровень: ожидается GD level string')


@dataclass
class Object:
    uid: int
    props: dict[str, str]
    id: int = field(init=False)
    x: float = field(init=False)
    y: float = field(init=False)
    angle: float = field(init=False)
    scale: float = field(init=False)

    def __post_init__(self):
        self.id = int(self.props['1'])
        self.x = float(self.props.get('2', 0))
        self.y = float(self.props.get('3', 0))
        self.angle = float(self.props.get('6', 0))
        self.scale = float(self.props.get('32', 1))
        if not all(math.isfinite(v) for v in (self.x, self.y, self.angle, self.scale)) or not 0 < self.scale <= 100:
            raise ValueError('Недопустимые координаты или масштаб объекта')

    def bounds(self):
        w, h = 30., 30.
        if self.id == 40: h = 6
        if self.id == 39: w, h = 8, 10
        if self.id == 103: w, h = 6, 18
        if self.id == 8: w, h = 6, 24
        if self.id == 9: w, h = 30, 6
        if self.id in PORTALS: w, h = 30, 90
        if self.id in {35, 67}: w, h = 30, 8
        if self.id == 36: w, h = 36, 36
        if self.id in {52, 53, 54}:
            w = h = {52: 64, 53: 44, 54: 24}[self.id]
        a = math.radians(self.angle)
        rw = (abs(w * math.cos(a)) + abs(h * math.sin(a))) * self.scale
        rh = (abs(w * math.sin(a)) + abs(h * math.cos(a))) * self.scale
        return self.x-rw/2, self.y-rh/2, self.x+rw/2, self.y+rh/2


@dataclass
class Level:
    name: str
    settings: dict[str, str]
    objects: list[Object]
    source: Path | None = None

    def __post_init__(self):
        self.objects.sort(key=lambda o: (o.x, o.uid))
        self.xs = [o.x for o in self.objects]
        self.length = max((o.x for o in self.objects), default=1000) + 240
        self.counts = Counter(o.id for o in self.objects)
        self.unsupported = sorted(set(self.counts) - SUPPORTED)

    @classmethod
    def from_string(cls, text, name='Imported level', source=None):
        pieces = decode_level(text).split(';')
        return cls(name, pairs(pieces[0]), [Object(i, pairs(s)) for i, s in enumerate(pieces[1:]) if s], source)

    @classmethod
    def load(cls, path, name=None):
        path = Path(path)
        # Some bundled levels have a C-string terminator followed by 0xCD padding.
        raw = path.read_bytes().split(b'\x00', 1)[0].decode('utf-8-sig')
        return cls.from_string(raw, name or path.stem, path)

    def nearby(self, x0, x1):
        return self.objects[bisect.bisect_left(self.xs, x0):bisect.bisect_right(self.xs, x1)]


@dataclass
class Physics:
    # Initial calibration values. See COMPATIBILITY.md for provenance/limitations.
    dx: float = 1.29825
    cube_gravity: float = 0.239549756
    cube_jump: float = 11.180032
    fall_cap: float = 15.0
    position_scale: float = 0.225


@dataclass
class Player:
    x: float = 0
    y: float = 15
    vy: float = 0
    angle: float = 0
    mode: str = 'cube'
    gravity: int = 1
    grounded: bool = True
    dead: bool = False


def overlaps(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


class World:
    def __init__(self, level: Level, physics=None):
        self.level = level
        self.physics = physics or Physics()
        self.reset()

    def reset(self):
        mode = 'ship' if self.level.settings.get('kA2') == '1' else 'cube'
        self.player = Player(mode=mode)
        self.ticks = 0
        self.done = False
        self.used = set()
        self.coins = 0
        self.noclip = False
        self.death_object = None
        self.ship_floor = 0
        self.ship_ceiling = 300
        self.color = self.start_color('kS29', (40, 62, 255))
        self.ground_color = self.start_color('kS30', (0, 19, 200))
        self.color_transitions = {}
        self.was_held = False

    def start_color(self, key, default):
        raw = self.level.settings.get(key, '').split('_')
        p = dict(zip(raw[::2], raw[1::2]))
        return tuple(int(p.get(str(i), default[i-1])) for i in range(1, 4))

    def kill(self, obj=None):
        if not self.noclip:
            self.player.dead = True
            self.death_object = obj.id if obj else 'boundary'

    def step(self, held: bool):
        p, cfg = self.player, self.physics
        if p.dead or self.done: return
        previous = (p.x, p.y)
        p.x += cfg.dx
        pressed = held and not self.was_held
        self.was_held = held
        if p.mode == 'cube':
            if held and p.grounded:
                p.vy = cfg.cube_jump * p.gravity
                p.grounded = False
            p.vy -= cfg.cube_gravity * p.gravity
            p.vy = max(-cfg.fall_cap, min(cfg.fall_cap, p.vy))
        else:
            v = p.vy * p.gravity
            threshold = 1.9163980484 * p.gravity
            accel = (0.108 if v <= threshold else 0.086) if held else (-0.103 if v > threshold else -0.069)
            p.vy = max(-6.4, min(8., v + accel)) * p.gravity
        p.y += p.vy * cfg.position_scale
        p.grounded = False
        radius = 15 if p.mode == 'cube' else 12
        if p.y < radius + (self.ship_floor if p.mode == 'ship' else 0):
            p.y = radius + (self.ship_floor if p.mode == 'ship' else 0)
            p.vy = 0
            p.grounded = p.gravity == 1
        if p.mode == 'ship' and p.y > self.ship_ceiling - radius:
            p.y = self.ship_ceiling-radius
            p.vy = 0
            p.grounded = p.gravity == -1
        full = (p.x-radius, p.y-radius, p.x+radius, p.y+radius)
        inner = (p.x-5, p.y-5, p.x+5, p.y+5)
        for o in self.level.nearby(p.x-180, p.x+180):
            box = o.bounds()
            if o.id in {29, 30} and previous[0] <= o.x < p.x and o.uid not in self.used:
                self.used.add(o.uid)
                attr = 'color' if o.id == 29 else 'ground_color'
                target = tuple(int(o.props.get(str(k), 255)) for k in (7, 8, 9))
                self.color_transitions[attr] = (getattr(self, attr), target, self.ticks, max(1, float(o.props.get('10', 0))*HZ))
            if not overlaps(full, box): continue
            if o.id in SOLIDS:
                landed = False
                if p.vy <= 0 and previous[1]-radius >= box[3]-0.5:
                    p.y, p.vy, p.grounded = box[3]+radius, 0, p.gravity == 1
                    landed = True
                elif p.vy >= 0 and previous[1]+radius <= box[1]+0.5:
                    if p.mode == 'ship' or p.gravity == -1:
                        p.y, p.vy, p.grounded = box[1]-radius, 0, p.gravity == -1
                        landed = True
                if not landed and overlaps(inner, box): self.kill(o)
                full = (p.x-radius, p.y-radius, p.x+radius, p.y+radius)
                inner = (p.x-5, p.y-5, p.x+5, p.y+5)
            elif o.id in HAZARDS:
                # Narrow spike rectangles approximate the original hitboxes.
                self.kill(o)
            elif o.id in PORTALS and o.uid not in self.used:
                self.used.add(o.uid)
                if o.id == 12:
                    p.mode = 'cube'
                elif o.id == 13:
                    p.mode = 'ship'
                    self.ship_floor = max(0, round((o.y-150)/30)*30)
                    self.ship_ceiling = self.ship_floor+300
                    p.vy = max(-6.4, min(8., p.vy))
                elif o.id == 10: p.gravity = -1
                elif o.id == 11: p.gravity = 1
            elif o.id == 142 and o.uid not in self.used:
                self.used.add(o.uid)
                self.coins += 1
            elif o.id == 35 and o.uid not in self.used:
                self.used.add(o.uid)
                p.vy, p.grounded = 14.5*p.gravity, False
            elif o.id == 67 and o.uid not in self.used:
                self.used.add(o.uid)
                p.gravity *= -1
                p.vy, p.grounded = 8*p.gravity, False
            elif o.id == 36 and pressed and o.uid not in self.used:
                self.used.add(o.uid)
                p.vy, p.grounded = cfg.cube_jump*p.gravity, False
        if p.mode == 'cube' and not p.grounded:
            p.angle = (p.angle-360/HZ/0.39*p.gravity) % 360
        elif p.mode == 'cube': p.angle = round(p.angle/90)*90
        else: p.angle = math.degrees(math.atan2(p.vy*cfg.position_scale, cfg.dx)) * .6
        if p.y > 4000 or p.y < -100: self.kill()
        for attr, (start, end, tick, duration) in self.color_transitions.items():
            t = min(1, (self.ticks-tick)/duration)
            setattr(self, attr, tuple(round(a+(b-a)*t) for a,b in zip(start,end)))
        self.ticks += 1
        self.done = p.x >= self.level.length and not p.dead

    @property
    def progress(self):
        return min(100, 100*self.player.x/self.level.length)
