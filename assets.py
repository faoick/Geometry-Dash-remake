"""Read-only access to the user's installed assets; nothing is copied to the project."""
from pathlib import Path
import os
import plistlib
import re
import pygame
from launcher import app_root

SPRITES = {**{i: f'square_{i:02}_001.png' for i in range(1, 8)},
    8: 'spike_01_001.png', 9: 'pit_01_001.png', 39: 'spike_02_001.png',
    103: 'spike_03_001.png', 15: 'rod_01_001.png', 16: 'rod_02_001.png',
    17: 'rod_03_001.png', 18: 'd_spikes_01_001.png', 19: 'd_spikes_02_001.png',
    20: 'd_spikes_03_001.png', 21: 'd_spikes_04_001.png', 40: 'plank_01_001.png',
    41: 'chain_01_001.png', 110: 'd_chain_02_001.png', 67: 'gravbump_01_001.png',
    52: 'sawblade_01_001.png', 53: 'sawblade_02_001.png',
    54: 'sawblade_03_001.png', 35: 'bump_01_001.png', 36: 'ring_01_001.png',
    142: 'secretCoin_01_001.png', 83: 'square_08_001.png',
    10: 'portal_01_front_001.png', 11: 'portal_02_front_001.png',
    12: 'portal_03_front_001.png', 13: 'portal_04_front_001.png'}


def find_resources(explicit=None):
    candidates = []
    config = app_root()/'resources-path.txt'
    selected = explicit or os.environ.get('GD_RESOURCES')
    if not selected and config.exists():
        selected = config.read_text(encoding='utf-8-sig').strip().strip('"')
    if selected:
        path = Path(selected).expanduser()
        if path.is_file(): path = path.parent
        for candidate in (path, path/'Resources'):
            if (candidate/'levels/1.txt').is_file(): return candidate.resolve()
        raise FileNotFoundError(f'По указанному пути не найдены уровни Geometry Dash: {selected}. '
                                'Укажи папку игры или Resources в resources-path.txt рядом с программой.')
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            steam = Path(winreg.QueryValueEx(key, 'SteamPath')[0])
        candidates.append(steam/'steamapps/common/Geometry Dash/Resources')
        libraries = (steam/'steamapps/libraryfolders.vdf').read_text(encoding='utf-8')
        for lib in re.findall(r'"path"\s+"([^"]+)"', libraries):
            candidates.append(Path(lib.replace('\\\\', '\\'))/'steamapps/common/Geometry Dash/Resources')
    except (OSError, ImportError): pass
    candidates.append(Path(r'C:\Program Files (x86)\Steam\steamapps\common\Geometry Dash\Resources'))
    for path in candidates:
        if (path/'levels/1.txt').is_file(): return path.resolve()
    raise FileNotFoundError('Не найдена установленная Geometry Dash. Создай resources-path.txt рядом с программой '
                            'и запиши туда полный путь к папке игры или Resources. Также доступны --resources и GD_RESOURCES.')


class Assets:
    def __init__(self, root):
        self.root = Path(root)
        self.frames = {}
        self.sheets = {}
        self.cache = {}
        self.transformed = {}
        self.missing = set()
        paths = [self.root/f'GJ_GameSheet{suffix}.plist' for suffix in ('', '02', '03', '04')]
        paths += [self.root/'icons/player_01.plist', self.root/'icons/ship_01.plist']
        for path in paths:
            if not path.exists(): continue
            with path.open('rb') as f: data = plistlib.load(f)
            for name, frame in data.get('frames', {}).items(): self.frames[name] = (path, frame)

    def frame(self, name):
        if name in self.cache: return self.cache[name]
        if name not in self.frames:
            self.missing.add(name)
            return None
        path, info = self.frames[name]
        if path not in self.sheets: self.sheets[path] = pygame.image.load(str(path.with_suffix('.png'))).convert_alpha()
        nums = lambda s: [int(float(n)) for n in re.findall(r'-?\d+(?:\.\d+)?', s)]
        x, y, w, h = nums(info['textureRect'])
        if info.get('textureRotated'):
            crop = self.sheets[path].subsurface((x, y, h, w)).copy()
            crop = pygame.transform.rotate(crop, 90)
        else: crop = self.sheets[path].subsurface((x, y, w, h)).copy()
        sw, sh = nums(info['spriteSourceSize'])
        ox, oy = nums(info['spriteOffset'])
        result = pygame.Surface((sw, sh), pygame.SRCALPHA)
        result.blit(crop, ((sw-w)//2+ox, (sh-h)//2-oy))
        self.cache[name] = result
        return result

    def sprite(self, obj, zoom):
        name = SPRITES.get(obj.id)
        if not name: return None
        key = (name, obj.scale, obj.angle, obj.props.get('4'), obj.props.get('5'), zoom)
        if key not in self.transformed:
            source = self.frame(name)
            if source is None: return None
            source = pygame.transform.flip(source, obj.props.get('4') == '1', obj.props.get('5') == '1')
            self.transformed[key] = pygame.transform.rotozoom(source, -obj.angle, obj.scale*zoom)
        return self.transformed[key]

    def image(self, name):
        key = 'file:'+name
        if key not in self.cache:
            self.cache[key] = pygame.image.load(str(self.root/name)).convert_alpha()
        return self.cache[key]

    def player(self, mode, zoom, primary, secondary):
        key = ('player', mode, zoom, primary, secondary)
        if key in self.transformed: return self.transformed[key]
        body = pygame.Surface((96,96),pygame.SRCALPHA)
        def layers(prefix, center, scale):
            for suffix, tint in [('_2_001.png',secondary),('_001.png',primary)]:
                sprite = self.frame(prefix+suffix)
                if sprite is None: continue
                sprite = sprite.copy()
                sprite.fill((*tint,255), special_flags=pygame.BLEND_RGBA_MULT)
                sprite = pygame.transform.smoothscale_by(sprite, scale)
                body.blit(sprite,sprite.get_rect(center=center))
        if mode == 'ship':
            layers('player_01',(45,36),zoom*.55)
            layers('ship_01',(48,52),zoom)
        else: layers('player_01',(48,48),zoom)
        self.transformed[key] = body
        return body
