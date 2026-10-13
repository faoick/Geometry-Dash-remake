# 🔷 Geometry Dash Remake (`Dash Rebuild`)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Engine-Pygame--CE_2.5.8-FBE042?style=for-the-badge&logo=python&logoColor=black" alt="Pygame-CE" />
  <img src="https://img.shields.io/badge/Platform-Windows_x64-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Windows x64" />
  <img src="https://img.shields.io/badge/Modding-Python_API-brightgreen?style=for-the-badge" alt="Modding Support" />
</p>

Экспериментальный независимый 2D-движок на **Python / pygame-ce**, воссоздающий физику и механику **Geometry Dash**, с поддержкой оригинальных уровней из Steam, парсингом игровых атласов и гибкой системой модов.

> [!NOTE]
> Это независимая реализация физики и игрового цикла. Проект не включает проприетарные ресурсы игры: спрайты, текстуры, музыка и уровни считываются напрямую из вашей локальной установки Steam Geometry Dash.

---

## 🎮 Реализованный функционал

- 🕹️ **Физический движок**: прыжки куба, режим полёта корабля, гравитационные порталы, жёлтые и синие сферы (orbs), батуты (pads), сбор монет и обнаружение препятствий.
- 🗺️ **Парсер уровней**: декодирование и воспроизведение всех 27 файлов уровней оригинальной игры (URL-safe Base64 + zlib/gzip декомпрессия).
- 🎵 **Графика и звук**: чтение оригинальных PNG-атласов, plist-разметки и фоновой музыки из локальной папки Geometry Dash.
- 🧩 **Система модов на Python**: подключение пользовательских скриптов из папки `mods/` с доступом к состоянию мира и тикам симуляции (отображение хитбоксов, noclip, изменение скорости).
- 📦 **Портативная сборка**: скрипт для упаковки игры в самостоятельный `.exe` и ZIP-архив без необходимости устанавливать Python на ПК игрока.

---

## ⌨️ Управление

| Клавиша | Действие |
| :---: | :--- |
| <kbd>←</kbd> / <kbd>→</kbd> | Выбор уровня в меню |
| <kbd>Enter</kbd> | Начать игру / продолжить |
| <kbd>Space</kbd> / <kbd>W</kbd> / <kbd>↑</kbd> / <kbd>ЛКМ</kbd> | Прыжок / удержание для полёта корабля |
| <kbd>Esc</kbd> | Пауза / возобновление игры |
| <kbd>R</kbd> | Быстрый перезапуск попытки |
| <kbd>Backspace</kbd> | Выход обратно в меню уровней |
| <kbd>M</kbd> | Включение / выключение музыки |
| <kbd>H</kbd> | *(Мод)* Включить/выключить отображение хитбоксов |
| <kbd>N</kbd> | *(Мод)* Режим бессмертия (Noclip) |
| <kbd>T</kbd> | *(Мод)* Замедление времени (0.5× без музыки) |

---

## 🚀 Установка и запуск

### Системные требования
- **ОС**: Windows 10 / 11 (x64)
- **Python**: 3.11+
- **Geometry Dash**: установленная игра в Steam (для загрузки игровых ресурсов).

### Быстрый запуск на Windows (Start.cmd)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/faoick/Geometry-Dash-remake.git
   cd Geometry-Dash-remake
   ```
2. Дважды щёлкните **`Start.cmd`**.  
   Скрипт автоматически настроит виртуальное окружение, установит библиотеку `pygame-ce` и запустит движок.

---

### Ручной запуск через командную строку

```powershell
# Создание и активация виртуального окружения
python -m venv .venv
.\.venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск игры
python main.py
```

> [!TIP]
> Движок автоматически находит Steam и стандартную папку игры. Если ваша Geometry Dash установлена на другом диске, укажите путь аргументом:
> ```powershell
> python main.py --resources "D:\SteamLibrary\steamapps\common\Geometry Dash\Resources"
> ```
> Либо создайте файл `resources-path.txt` рядом с `main.py`, содержащий одну строку с полным путём к папке игры.

---

## 🧩 Создание собственных модов

Чтобы создать мод, просто добавьте `.py` файл в папку `mods/` — он подгрузится автоматически.

Пример мода:
```python
def on_reset(app):
    """Вызывается при каждом старте или перезапуске попытки."""
    app.world.physics.cube_jump = 13.5  # изменение силы прыжка

def on_tick(app, held):
    """Вызывается перед каждым тиком физики (240 раз в игровую секунду)."""
    pass

def on_key(app, key):
    """Обработка нажатий дополнительных горячих клавиш."""
    pass
```

Готовый пример функциональных модов доступен в файле [`mods/practice_tools.py`](mods/practice_tools.py).

---

## 🏗️ Структура проекта

- [`main.py`](main.py) — графический цикл, меню, камера, отрисовка сцены и обработка пользовательского ввода.
- [`core.py`](core.py) — математика физики, обработка столкновений, декодер уровней (чистая логика без зависимостей от окна).
- [`assets.py`](assets.py) — парсер атласов спрайтов, plist-метаданных и алгоритм автопоиска директории Steam.
- [`modding.py`](modding.py) — диспетчер и безопасный загрузчик модов.
- [`launcher.py`](launcher.py) — безопасный лаунчер с перехватом системных исключений и записью crash-логов.
- [`build_portable.py`](build_portable.py) — генератор автономной портативной сборки (собирает `.exe` с PyInstaller).
- [`COMPATIBILITY.md`](COMPATIBILITY.md) — подробный аудит физики, парсера и статуса совместимости.

---

## 🧪 Тестирование и диагностика

```powershell
# Запуск автоматических тестов
python -m unittest -v

# Аудит всех 27 оригинальных уровней
python main.py --audit

# Проверка рендерера в headless-режиме
python main.py --smoke
```

---

## 📦 Сборка переносимого EXE

Для упаковки проекта в автономный дистрибутив:
```powershell
pip install pyinstaller==6.22.3
python build_portable.py
```
Собранный архив появится по пути `release/DashRebuild-Windows-x64.zip`.