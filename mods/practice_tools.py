"""Example mod. Edit this file or add another .py, then restart the application.

H = collision boxes; N = no-death practice; T = half-speed practice.
Runs only inside Dash Rebuild, does not modify the Steam installation.
"""
import pygame

NAME = 'Practice Tools'


def on_key(app, key):
    if key == pygame.K_h: app.hitboxes = not app.hitboxes
    elif key == pygame.K_n:
        app.noclip = not app.noclip
        app.world.noclip = app.noclip
    elif key == pygame.K_t:
        app.slow = not app.slow
        app.sync_music()


def on_reset(app):
    app.world.noclip = app.noclip
