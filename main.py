from __future__ import annotations

# Direct source runs must enter the logger before importing pygame or other modules.
if __name__ == '__main__':
    from launcher import run
    raise SystemExit(run())

import argparse
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from assets import Assets, find_resources
from core import HZ, Level, World, NAMES, SONGS, SOLIDS, HAZARDS, TRIGGERS
from modding import Mods
from launcher import app_root, data_directory

ROOT = app_root()
BG = (12, 18, 33)
PANEL = (23, 33, 54)
WHITE = (240, 245, 255)
MUTED = (164, 181, 205)
ACCENT = (113, 243, 167)
BLUE = (82, 150, 255)


class App:
    def __init__(self, resources, custom=None, headless=False):
        pygame.init()
        self.window = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        pygame.display.set_caption('Dash Rebuild — independent engine / experimental')
        self.screen = pygame.Surface((1280, 720))
        self.root = resources
        self.assets = Assets(resources)
        self.fonts = {}
        self.levels = [Level.load(resources/f'levels/{i}.txt', NAMES[i-1]) for i in (1, 2, 3)]
        if custom: self.levels.append(Level.load(custom))
        self.selected = len(self.levels)-1 if custom else 0
        self.world = World(self.levels[self.selected])
        self.state = 'menu'
        self.running = True
        self.hitboxes = self.noclip = self.slow = False
        self.muted = headless
        self.audio_available = bool(pygame.mixer.get_init())
        self.attempt = 1
        self.death_time = 0
        self.accumulator = 0
        self.camera_y = 0
        self.buttons = []
        self.focus = 0
        self.key_held = self.mouse_held = False
        self.clock = pygame.time.Clock()
        self.mods = Mods(ROOT/'mods', self)
        self.notice = ''

    def text(self, message, x, y, size=22, color=WHITE, bold=False, center=False):
        key = (size, bold)
        if key not in self.fonts: self.fonts[key] = pygame.font.SysFont('segoeui', size, bold=bold)
        img = self.fonts[key].render(str(message), True, color)
        rect = img.get_rect(midtop=(x, y)) if center else img.get_rect(topleft=(x, y))
        self.screen.blit(img, rect)
        return rect

    def mouse(self):
        w, h = self.window.get_size()
        scale = min(w/1280, h/720)
        x, y = pygame.mouse.get_pos()
        return ((x-(w-1280*scale)/2)/scale, (y-(h-720*scale)/2)/scale)

    def button(self, label, rect, action, primary=False):
        rect = pygame.Rect(rect)
        focused = self.focus == len(self.buttons)
        hovered = rect.collidepoint(self.mouse())
        color = ACCENT if primary else ((38, 57, 83) if hovered else PANEL)
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        if focused or hovered: pygame.draw.rect(self.screen, WHITE if not primary else (184,255,211), rect, 2, border_radius=12)
        self.text(label, rect.centerx, rect.y+13, 22, BG if primary else WHITE, True, True)
        self.buttons.append((rect, action))

    def choose(self, index):
        self.selected = index % len(self.levels)
        self.world = World(self.levels[self.selected])

    def start(self):
        self.attempt = 1
        self.state = 'play'
        self.reset()

    def reset(self):
        self.world = World(self.levels[self.selected])
        self.accumulator = self.death_time = 0
        self.camera_y = 0
        self.mods.emit('on_reset')
        self.sync_music()

    def sync_music(self):
        if not self.audio_available: return
        pygame.mixer.music.stop()
        if self.muted or self.slow or self.state != 'play': return
        if self.selected >= len(SONGS): return
        path = self.root/(SONGS[self.selected]+'.mp3') if self.selected < 3 else None
        if path and path.exists():
            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(.45)
                pygame.mixer.music.play(start=self.world.ticks/HZ)
            except pygame.error as exc:
                self.notice = 'Звук недоступен: '+str(exc)

    def pause(self):
        if self.state == 'play':
            self.state = 'pause'
            if self.audio_available: pygame.mixer.music.pause()
        elif self.state == 'pause':
            self.state = 'play'
            self.sync_music()
        self.accumulator = 0

    def menu(self):
        self.state = 'menu'
        self.key_held = self.mouse_held = False
        self.focus = 0
        if self.audio_available: pygame.mixer.music.stop()

    def key(self, key):
        self.mods.emit('on_key', key)
        if key == pygame.K_m:
            self.muted = not self.muted
            self.sync_music()
        if key == pygame.K_ESCAPE:
            if self.state in ('play', 'pause'): self.pause()
            elif self.state == 'complete': self.menu()
        if key == pygame.K_BACKSPACE: self.menu()
        if key == pygame.K_r and self.state in ('play', 'pause', 'complete'):
            self.state = 'play'
            self.attempt += 1
            self.reset()
        if self.state == 'menu':
            if key == pygame.K_LEFT: self.choose(self.selected-1)
            elif key == pygame.K_RIGHT: self.choose(self.selected+1)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.buttons: self.buttons[self.focus % len(self.buttons)][1]()
                else: self.start()
            elif key == pygame.K_TAB: self.focus = (self.focus+1) % max(1, len(self.buttons))
        elif key == pygame.K_RETURN:
            if self.state == 'pause': self.pause()
            elif self.state == 'complete': self.menu()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            elif event.type == pygame.KEYDOWN:
                before = self.state
                self.key(event.key)
                if before == 'play' and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w): self.key_held = True
            elif event.type == pygame.KEYUP and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w): self.key_held = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == 'play': self.mouse_held = True
                else:
                    for rect, action in self.buttons:
                        if rect.collidepoint(self.mouse()):
                            action()
                            break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.mouse_held = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.key_held = self.mouse_held = False
                if self.state == 'play': self.pause()

    def update(self, elapsed):
        if self.state != 'play': return
        if elapsed > .2:
            self.pause()  # Avoid silently losing simulation time and drifting from the song.
            return
        if self.world.player.dead:
            if self.death_time == 0 and self.audio_available: pygame.mixer.music.stop()
            self.death_time += elapsed
            if self.death_time >= .85:
                self.attempt += 1
                self.reset()
            return
        self.accumulator += elapsed*(.5 if self.slow else 1)
        held = self.key_held or self.mouse_held
        while self.accumulator >= 1/HZ:
            self.mods.emit('on_tick', held)
            self.world.step(held)
            self.accumulator -= 1/HZ
            if self.world.player.dead or self.world.done: break
        if self.world.done:
            self.state = 'complete'
            if self.audio_available: pygame.mixer.music.stop()

    def draw_menu(self):
        self.screen.fill(BG)
        for x in range(760, 1350, 64): pygame.draw.line(self.screen, (20,31,51), (x,0), (x-340,720), 1)
        self.text('DASH / REBUILD', 72, 44, 22, ACCENT, True)
        self.text('Свой код. Тот же ритм.', 72, 96, 49, WHITE, True)
        self.text('Оригинальные уровни из твоей Steam-установки', 74, 165, 23, MUTED)
        pygame.draw.rect(self.screen, (33,43,66), (920,48,288,36), border_radius=18)
        self.text('ЭКСПЕРИМЕНТАЛЬНЫЙ ДВИЖОК', 1064,55,14,MUTED,True,True)
        for i, level in enumerate(self.levels):
            if i > 2: continue
            rect = pygame.Rect(72+i*384, 238, 360, 220)
            selected = i == self.selected
            pygame.draw.rect(self.screen, PANEL if selected else (18,27,45), rect, border_radius=16)
            pygame.draw.rect(self.screen, BLUE if selected else (39,52,74), rect, 2 if selected else 1, border_radius=16)
            self.text(f'0{i+1}', rect.x+24, rect.y+19, 22, BLUE, True)
            self.text('STEAM', rect.right-80, rect.y+24, 14, MUTED, True)
            self.text(level.name, rect.x+24, rect.y+72, 29, WHITE, True)
            self.text(f'{len(level.objects):,} объектов'.replace(',', ' '), rect.x+24, rect.y+118, 19, MUTED)
            self.text('Выбран  •  Enter — играть' if selected else 'Нажми, чтобы выбрать', rect.x+24, rect.y+171, 17, ACCENT if selected else MUTED)
            # Start stays first in keyboard focus order; cards are mouse-accessible below.
        self.button('Играть  /  Enter', (72,492,290,58), self.start, True)
        self.button('Папка модов', (382,492,220,58), lambda: os.startfile(ROOT/'mods'))
        self.button('О проекте', (622,492,200,58), lambda: os.startfile(ROOT/'README.md'))
        for i in range(min(3,len(self.levels))):
            self.buttons.append((pygame.Rect(72+i*384,238,360,220), lambda i=i: self.choose(i)))
        if self.selected >= 3: self.text('Импорт: '+self.world.level.name, 850, 504, 20, ACCENT)
        self.text('Пока поддерживаются базовые объекты, куб и корабль. Точность 1:1 ещё не подтверждена.', 74,581,19,MUTED)
        self.text('← →  Уровень     SPACE / ЛКМ  Прыжок     ESC  Пауза     M  Звук', 74,626,18,WHITE)
        self.text(f'Моды: {len(self.mods.active)}     H  Хитбоксы     N  Без смерти     T  Замедление', 74,660,17,MUTED)

    def draw_world(self):
        world, p = self.world, self.world.player
        zoom = 1.8
        camera_x = max(-80, p.x-160)
        target_y = max(0, p.y-210) if p.mode == 'cube' else world.ship_floor
        self.camera_y += (target_y-self.camera_y)*.12
        floor_y = 560+self.camera_y*zoom
        pos = lambda x,y: (round((x-camera_x)*zoom), round(floor_y-y*zoom))
        self.screen.fill(world.color)
        bg = self.assets.image('game_bg_01_001.png').copy()
        bg.fill((*world.color,255), special_flags=pygame.BLEND_RGBA_MULT)
        bg = pygame.transform.smoothscale(bg,(720,720))
        offset = int(-camera_x*.18)%720
        for x in range(offset-720,1280,720): self.screen.blit(bg,(x,0))
        for obj in world.level.nearby(camera_x-120, camera_x+1280/zoom+120):
            if obj.id in TRIGGERS: continue
            if obj.id == 142 and obj.uid in world.used: continue
            sprite = self.assets.sprite(obj, zoom)
            if sprite:
                rect = sprite.get_rect(center=pos(obj.x,obj.y))
                self.screen.blit(sprite,rect)
            elif obj.id not in TRIGGERS:
                x,y = pos(obj.x,obj.y)
                pygame.draw.rect(self.screen,(255,100,200),(x-12,y-12,24,24),2)
                self.text(str(obj.id),x,y,12,WHITE,False,True)
            if self.hitboxes and obj.id in SOLIDS | HAZARDS:
                left,bottom,right,top = obj.bounds()
                x,y = pos(left,top)
                pygame.draw.rect(self.screen,(255,92,100) if obj.id in HAZARDS else (85,255,161), (x,y,(right-left)*zoom,(top-bottom)*zoom),1)
        def ground(y, upside=False):
            sy = pos(0,y)[1]
            rect = pygame.Rect(0,0 if upside else sy,1280,sy if upside else 720-sy)
            if rect.height > 0:
                pygame.draw.rect(self.screen,world.ground_color,rect)
                tile = self.assets.image('groundSquare_01_001.png').copy()
                tile.fill((*world.ground_color,255),special_flags=pygame.BLEND_RGBA_MULT)
                tile = pygame.transform.smoothscale_by(tile,zoom)
                if upside: tile = pygame.transform.flip(tile,False,True)
                for tx in range(-int(camera_x*zoom)%tile.get_width()-tile.get_width(),1280,tile.get_width()):
                    self.screen.blit(tile,(tx,sy-tile.get_height() if upside else sy))
                pygame.draw.line(self.screen,WHITE,(0,sy),(1280,sy),2)
        ground(world.ship_floor if p.mode == 'ship' else 0)
        if p.mode == 'ship': ground(world.ship_ceiling,True)
        if not p.dead:
            cx,cy = pos(p.x,p.y)
            body = self.assets.player(p.mode,zoom,ACCENT,(92,219,255))
            body = pygame.transform.rotate(body,p.angle)
            self.screen.blit(body,body.get_rect(center=(cx,cy)))
            if self.hitboxes:
                r=(15 if p.mode=='cube' else 12)*zoom
                pygame.draw.rect(self.screen,(255,235,87),(cx-r,cy-r,r*2,r*2),1)
                pygame.draw.rect(self.screen,(255,102,120),(cx-9,cy-9,18,18),1)
        else:
            cx,cy=pos(p.x,p.y)
            for i in range(12):
                a=i*math.tau/12
                d=20+self.death_time*180
                pygame.draw.rect(self.screen,ACCENT,(cx+math.cos(a)*d,cy+math.sin(a)*d,7,7))
        hud=pygame.Surface((1280,78),pygame.SRCALPHA)
        hud.fill((6,13,28,205));self.screen.blit(hud,(0,0))
        self.text(world.level.name,28,21,24,WHITE,True)
        pygame.draw.rect(self.screen,(47,62,87),(440,31,390,14),border_radius=7)
        pygame.draw.rect(self.screen,ACCENT,(440,31,max(1,390*world.progress/100),14),border_radius=7)
        self.text(f'{world.progress:.1f}%',852,22,22,WHITE,True)
        self.text(f'Попытка {self.attempt}',1050,22,22,MUTED)
        footer=pygame.Surface((1280,42),pygame.SRCALPHA);footer.fill((6,13,28,220));self.screen.blit(footer,(0,678))
        self.text('SPACE / ЛКМ — прыжок / полёт    ESC — пауза    R — заново',24,687,16,WHITE)
        flags=[]
        if self.noclip: flags.append('БЕЗ СМЕРТИ')
        if self.slow: flags.append('0.5× • БЕЗ ЗВУКА')
        if self.muted: flags.append('ЗВУК ВЫКЛ.')
        self.text(' · '.join(flags) or 'ЭКСПЕРИМЕНТАЛЬНАЯ ФИЗИКА',840,687,15,ACCENT)
        if world.level.unsupported:
            self.text(f'Неподдерживаемые ID: {world.level.unsupported[:12]}',24,88,17,(255,235,140))

    def draw(self):
        self.buttons=[]
        if self.state == 'menu': self.draw_menu()
        else:
            self.draw_world()
            if self.state in ('pause','complete'):
                overlay=pygame.Surface((1280,720),pygame.SRCALPHA);overlay.fill((6,12,25,205));self.screen.blit(overlay,(0,0))
                pygame.draw.rect(self.screen,PANEL,(365,185,550,345),border_radius=20)
                self.text('Пауза' if self.state=='pause' else 'Уровень завершён',640,220,40,WHITE,True,True)
                self.text('Экспериментальный движок · результат локальный',640,286,18,MUTED,False,True)
                self.button('Продолжить  /  Enter' if self.state=='pause' else 'Ещё раз  /  R',(420,342,440,58),self.pause if self.state=='pause' else self.start,True)
                self.button('К уровням  /  Backspace',(420,422,440,58),self.menu)
        errors=self.mods.errors[-1:] or ([self.notice] if self.notice else [])
        if errors:
            pygame.draw.rect(self.screen,(96,30,46),(0,0,1280,32))
            self.text(errors[0][:115],12,3,17,WHITE)
        w,h=self.window.get_size();scale=min(w/1280,h/720)
        frame=pygame.transform.smoothscale(self.screen,(max(1,int(1280*scale)),max(1,int(720*scale))))
        self.window.fill((0,0,0));self.window.blit(frame,frame.get_rect(center=(w//2,h//2)))
        pygame.display.flip()

    def run(self):
        while self.running:
            elapsed=self.clock.tick(144)/1000
            self.events();self.update(elapsed);self.draw()
        pygame.quit()


def audit(root):
    result=[]
    for path in sorted((root/'levels').glob('*.txt'),key=lambda p:int(p.stem)):
        i=int(path.stem)
        try:
            level=Level.load(path,NAMES[i-1] if 1<=i<=len(NAMES) else path.stem)
            result.append({'id':i,'name':level.name,'objects':len(level.objects),
                           'object_types':len(level.counts),'unsupported_ids':level.unsupported,
                           'ignored_visual_trigger_ids':sorted(set(level.counts) & (TRIGGERS-{29,30})),
                           'parser':'ok','physics':'unverified'})
        except Exception as exc: result.append({'id':i,'parser':'error','error':str(exc)})
    output=data_directory()
    (output/'level_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Parsed {sum(r["parser"]=="ok" for r in result)}/{len(result)} levels. Report: {output / "level_audit.json"}')


def main():
    parser=argparse.ArgumentParser(description='Independent experimental Geometry Dash compatibility engine')
    parser.add_argument('--resources');parser.add_argument('--level-file')
    parser.add_argument('--audit',action='store_true');parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    resources=find_resources(args.resources)
    print(f'Resources: {resources}')
    if args.audit: audit(resources);return
    if args.smoke:
        os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
    app=App(resources,args.level_file,args.smoke)
    if args.smoke:
        out=data_directory()
        app.draw();pygame.image.save(app.screen,str(out/'menu.png'))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        app.events();assert app.state=='play'
        for _ in range(144):app.update(1/144)
        assert 300<app.world.player.x<315
        app.draw();pygame.image.save(app.screen,str(out/'gameplay.png'))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        app.events();assert app.state=='pause'
        before=app.world.ticks;app.update(.1);assert app.world.ticks==before
        app.draw();pygame.image.save(app.screen,str(out/'pause.png'))
        app.key(pygame.K_h);assert app.hitboxes
        app.key(pygame.K_n);assert app.world.noclip
        app.reset();assert app.world.noclip
        app.key(pygame.K_t);assert app.slow
        print('Smoke OK: menu/start, fixed timestep, pause, mod keys, reset. Missing sprites:',sorted(app.assets.missing))
        pygame.quit()
    else: app.run()
