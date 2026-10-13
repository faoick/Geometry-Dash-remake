"""Build a Windows x64 folder + ZIP without user assets, caches, or a copied venv."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    if sys.platform != 'win32':raise SystemExit('Build this Windows package on Windows.')
    dist = (ROOT/'release').resolve()
    work = (ROOT/'user_data/packaging').resolve()
    for path in (dist, work):
        if not path.is_relative_to(ROOT):raise ValueError('Build output escaped the project')
        path.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--onedir',
                    '--name', 'DashRebuild', '--distpath', str(dist), '--workpath', str(work/'work'),
                    '--specpath', str(work), '--hidden-import', 'pygame', str(ROOT/'launcher.py')],
                   cwd=ROOT, check=True)
    package = dist/'DashRebuild'
    for name in ('Start.cmd', 'README.md', 'COMPATIBILITY.md', 'READ_FIRST.txt'):
        shutil.copy2(ROOT/name, package/name)
    (package/'mods').mkdir(exist_ok=True)
    for path in (ROOT/'mods').glob('*.py'):shutil.copy2(path, package/'mods'/path.name)
    (package/'source').mkdir(exist_ok=True)
    for name in ('Start.cmd', 'README.md', 'COMPATIBILITY.md', 'READ_FIRST.txt'):
        shutil.copy2(ROOT/name, package/'source'/name)
    (package/'source/mods').mkdir(exist_ok=True)
    for path in (ROOT/'mods').glob('*.py'):shutil.copy2(path, package/'source/mods'/path.name)
    for name in ('launcher.py', 'main.py', 'core.py', 'assets.py', 'modding.py',
                 'requirements.txt', 'test_engine.py', 'test_startup.py', 'build_portable.py'):
        shutil.copy2(ROOT/name, package/'source'/name)
    archive = dist/'DashRebuild-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(package.rglob('*')):
            if path.is_file() and not {'user_data', '__pycache__'} & set(path.relative_to(package).parts):
                output.write(path, path.relative_to(dist))
    print(f'Portable archive: {archive} ({archive.stat().st_size/1024/1024:.1f} MB)')


if __name__ == '__main__':main()
