import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import launcher
from assets import find_resources


class StartupTests(unittest.TestCase):
    def copied_source(self, folder):
        for name in ('main.py', 'launcher.py', 'assets.py', 'core.py', 'modding.py'):
            shutil.copy2(Path(__file__).parent/name, folder/name)

    def test_missing_pygame_is_logged_before_main_import(self):
        with tempfile.TemporaryDirectory(prefix='dash startup ') as temp:
            folder = Path(temp)
            self.copied_source(folder)
            env = dict(os.environ, DASH_NO_ERROR_DIALOG='1')
            result = subprocess.run([sys.executable, '-S', str(folder/'main.py'), '--audit'],
                                    cwd=folder, env=env, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            text = (folder/'user_data/launch.log').read_text(encoding='utf-8')
            self.assertIn('ModuleNotFoundError', text)
            self.assertIn('pygame', text)
            self.assertGreater((folder/'user_data/crash.log').stat().st_size, 100)

    def test_invalid_resources_produces_actionable_log(self):
        with tempfile.TemporaryDirectory(prefix='dash startup ') as temp:
            folder = Path(temp)
            self.copied_source(folder)
            env = dict(os.environ, DASH_NO_ERROR_DIALOG='1')
            result = subprocess.run([sys.executable, str(folder/'launcher.py'), '--audit',
                                     '--resources', str(folder/'missing game')],
                                    cwd=folder, env=env, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            text = (folder/'user_data/launch.log').read_text(encoding='utf-8')
            self.assertIn('FileNotFoundError', text)
            self.assertIn('resources-path.txt', text)

    def test_log_folder_falls_back_when_install_folder_is_unwritable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            blocker = root/'not-a-directory'
            blocker.write_text('blocker')
            with patch.object(launcher, 'app_root', return_value=blocker), \
                 patch.dict(os.environ, {'LOCALAPPDATA': str(root/'local')}):
                folder = launcher.data_directory()
                self.assertEqual(folder, root/'local/DashRebuild/user_data')
                self.assertTrue(folder.is_dir())

    def test_explicit_game_folder_and_resources_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'Resources/levels').mkdir(parents=True)
            (root/'Resources/levels/1.txt').write_text('test')
            self.assertEqual(find_resources(str(root)), (root/'Resources').resolve())
            self.assertEqual(find_resources(str(root/'Resources')), (root/'Resources').resolve())
            with self.assertRaises(FileNotFoundError):find_resources(str(root/'missing'))


if __name__ == '__main__':unittest.main(verbosity=2)
