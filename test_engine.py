import base64
import gzip
import tempfile
import unittest
from pathlib import Path

from core import Level, World, decode_level
from assets import find_resources


def tiny(objects=''):
    return Level.from_string('kA2,0;'+objects)


class ParserTests(unittest.TestCase):
    def test_compressed_and_legacy_formats(self):
        raw='kA2,0;1,8,2,525,3,15;'
        packed=base64.urlsafe_b64encode(gzip.compress(raw.encode(),mtime=0)).decode()
        self.assertEqual(decode_level(packed),raw)
        self.assertEqual(decode_level(packed[13:]),raw)
        self.assertEqual(decode_level(raw),raw)

    def test_binary_padding_after_c_terminator(self):
        raw=b'kA2,0;1,1,2,15,3,15;'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'level.txt'
            path.write_bytes(base64.urlsafe_b64encode(gzip.compress(raw))+b'\x00\xcd')
            self.assertEqual(len(Level.load(path).objects),1)

    def test_rejects_corrupt_or_nonfinite_data(self):
        for raw in ['not a level', 'kA2,0;1,8,2,nan,3,15;', 'kA2,0;1,8,2;']:
            with self.assertRaises(ValueError): Level.from_string(raw)


class SimulationTests(unittest.TestCase):
    def test_landing_on_platform_survives(self):
        world=World(tiny('1,1,2,100,3,15;'))
        world.player.x=95;world.player.y=50;world.player.vy=-8
        for _ in range(8): world.step(False)
        self.assertFalse(world.player.dead)
        self.assertEqual(world.player.y,45)
        self.assertTrue(world.player.grounded)

    def test_block_side_is_lethal(self):
        world=World(tiny('1,1,2,100,3,15;'))
        for _ in range(100):world.step(False)
        self.assertTrue(world.player.dead)
        self.assertEqual(world.death_object,1)

    def test_ship_entry_requires_vertical_contact(self):
        level=tiny('1,13,2,50,3,165;')
        world=World(level)
        for _ in range(60):world.step(False)
        self.assertEqual(world.player.mode,'cube')
        world=World(level);world.player.y=165;world.player.x=49
        world.step(False)
        self.assertEqual(world.player.mode,'ship')

    def test_coin_and_pad_activate_once(self):
        world=World(tiny('1,142,2,10,3,15;1,35,2,50,3,4;'))
        for _ in range(45):world.step(False)
        self.assertEqual(world.coins,1)
        self.assertGreater(world.player.y,15)
        self.assertEqual(len(world.used),2)

    def test_reset_determinism(self):
        world=World(tiny('1,8,2,525,3,15;'))
        def play():
            for i in range(500):world.step(354<=i<=357)
            return (world.player.x,world.player.y,world.player.vy,world.player.dead)
        first=play();world.reset();self.assertEqual(first,play())


class InstalledDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:cls.root=find_resources()
        except FileNotFoundError:raise unittest.SkipTest('Geometry Dash is not installed')

    def test_all_bundled_levels_parse(self):
        for path in (self.root/'levels').glob('*.txt'):
            with self.subTest(level=path.stem):
                level=Level.load(path)
                self.assertGreater(len(level.objects),0)

    def test_original_first_spike_requires_jump(self):
        level=Level.load(self.root/'levels/1.txt')
        walking=World(level)
        while not walking.player.dead and walking.ticks<1000:walking.step(False)
        self.assertTrue(walking.player.dead)
        self.assertEqual(walking.death_object,8)
        self.assertLess(walking.player.x,525)
        jumping=World(level)
        while jumping.player.x<800 and not jumping.player.dead:jumping.step(460<jumping.player.x<465)
        self.assertFalse(jumping.player.dead)
        self.assertGreater(jumping.player.x,800)


if __name__=='__main__':unittest.main(verbosity=2)
