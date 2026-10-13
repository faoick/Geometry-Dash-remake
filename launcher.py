"""Startup boundary: only stdlib imports until an on-disk log is open."""
from datetime import datetime
import faulthandler
import os
from pathlib import Path
import platform
import sys
import tempfile
import traceback

VERSION = '0.1.1-portable'


def app_root():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def data_directory():
    candidates = [app_root() / 'user_data']
    if os.environ.get('LOCALAPPDATA'):
        candidates.append(Path(os.environ['LOCALAPPDATA']) / 'DashRebuild' / 'user_data')
    candidates.append(Path(tempfile.gettempdir()) / 'DashRebuild' / 'user_data')
    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # A real write catches read-only install folders before the error handler runs.
            with tempfile.TemporaryFile(dir=directory):
                pass
            return directory
        except OSError:
            continue
    raise OSError('Нет доступной папки для журнала запуска')


def show_error(message):
    if os.environ.get('DASH_NO_ERROR_DIALOG') == '1':
        return
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Dash Rebuild — ошибка запуска', 0x10)
            return
        except Exception:
            pass
    if sys.__stderr__:
        print(message, file=sys.__stderr__)


def run():
    try:
        directory = data_directory()
        log = (directory / 'launch.log').open('w', encoding='utf-8', buffering=1)
    except OSError as exc:
        show_error(f'Не удалось открыть журнал: {exc}\nРаспакуй игру в доступную для записи папку.')
        return 1
    old_out, old_err = sys.stdout, sys.stderr
    exit_code = 0
    with log:
        sys.stdout = sys.stderr = log
        try:
            print(f'Dash Rebuild {VERSION} | {datetime.now().astimezone().isoformat()}')
            print(f'OS: {platform.platform()} | Python: {sys.version}')
            print(f'Executable: {sys.executable}\nApp folder: {app_root()}')
            print(f'Frozen: {getattr(sys, "frozen", False)} | Arguments: {sys.argv[1:]}')
            log.flush()
            faulthandler.enable(file=log, all_threads=True)
            # Catch pygame/DLL/import failures as well as failures inside main().
            import main
            main.main()
            print('EXIT OK')
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
            print(f'EXIT {exit_code}')
        except Exception as exc:
            exit_code = 1
            details = traceback.format_exc()
            print(details)
            log.flush()
            crash = directory / 'crash.log'
            try:
                crash.write_text(f'Dash Rebuild {VERSION}\n{details}', encoding='utf-8')
            except OSError:
                crash = directory / 'launch.log'
            show_error(
                f'{type(exc).__name__}: {exc}\n\n'
                f'Полный журнал:\n{directory / "launch.log"}\n\n'
                'Пришли этот файл для диагностики. Запускай игру после полной распаковки архива.'
            )
        finally:
            if faulthandler.is_enabled():
                faulthandler.disable()
            sys.stdout, sys.stderr = old_out, old_err
    return exit_code


if __name__ == '__main__':
    raise SystemExit(run())
