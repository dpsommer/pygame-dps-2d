import dataclasses
from typing import Callable

import pygame.extensions.dps.core as pgcore

import pygame

from . import sprite, types


@dataclasses.dataclass
class TextOptions(pgcore.Configurable):
    font: pygame.font.Font
    antialias: bool
    color: types.ColorValue
    hover_color: types.ColorValue


@dataclasses.dataclass
class ButtonOptions(sprite.SpriteOptions):
    color: types.ColorValue = ""
    text: str = ""
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
        self.text = opts.text
        self.text_opts = opts.text_opts
        self.on_click = on_click

    def update(self):
        if self.text and self.text_opts is not None:
            text_opts = self.text_opts

            text_color = text_opts.hover_color if self.hovered else text_opts.color
            img = text_opts.font.render(self.text, text_opts.antialias, text_color)
            button_w, button_h = self.rect.size
            text_w, text_h = img.get_size()
            pos = ((button_w / 2) - (text_w / 2), (button_h / 2) - (text_h / 2))

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
