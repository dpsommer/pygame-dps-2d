import dataclasses
from typing import Callable

import pygame
import pygame.extensions.dps.core as pgcore

from . import types
from . import sprite


@dataclasses.dataclass
class TextOptions(pgcore.Configurable):
    font: pygame.font.Font
    antialias: bool
    color: types.ColorValue
    hover_color: types.ColorValue
    text: str = ""


@dataclasses.dataclass
class ButtonOptions(sprite.SpriteOptions):
    color: types.ColorValue = ""
    text_opts: TextOptions | None = None


class Button(sprite.GameSprite):
    """Clickable image or text button

    Args:
        opts (ButtonOptions): configuration options for the button
        on_click (Callable): on-click callback
    """

    _hovered: bool = False

    def __init__(self, opts: ButtonOptions, on_click: Callable):
        super().__init__(opts)
        self.color = opts.color
        self.text_opts = opts.text_opts
        self.on_click = on_click

    def update(self):
        if self.text_opts is not None:
            text_opts = self.text_opts

            text_color = text_opts.hover_color if self.hovered else text_opts.color
            img = text_opts.font.render(text_opts.text, text_opts.antialias, text_color)
            w, h = img.get_size()
            pos = (self.rect.centerx - (w / 2), self.rect.centery - (h / 2))

            self.image.fill(self.color)
            self.image.blit(img, pos)

    @property
    def hovered(self):
        return self._hovered

    @hovered.setter
    def hovered(self, hovered):
        # only dirty the sprite if we're changing state
        if self._hovered is not hovered:
            self.dirty = 1
        self._hovered = hovered
