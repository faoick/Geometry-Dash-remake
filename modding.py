"""Local Python mods: on_load(app), on_reset(app), on_key(app,key), on_tick(app,held).

Mods execute as ordinary Python code with the user's permissions.
Faulty mods are disabled and their error is shown in the application.
"""
import importlib.util
import traceback


class Mods:
    def __init__(self, folder, app):
        self.active = []
        self.errors = []
        self.app = app
        for path in sorted(folder.glob('*.py')):
            if path.name.startswith('_'): continue
            try:
                spec = importlib.util.spec_from_file_location('dash_mod_'+path.stem, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'on_load'): module.on_load(app)
                self.active.append((path.stem, module))
            except Exception:
                self.fail(path.stem)

    def fail(self, name):
        error = f'Мод {name} отключён: {traceback.format_exc().splitlines()[-1]}'
        self.errors.append(error)
        print(error)

    def emit(self, event, *args):
        for name, module in self.active[:]:
            hook = getattr(module, event, None)
            if hook:
                try: hook(self.app, *args)
                except Exception:
                    self.fail(name)
                    self.active.remove((name, module))
