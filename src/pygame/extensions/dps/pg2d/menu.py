from typing import List

import pygame.extensions.dps.core as pgcore
from pygame.sprite import LayeredDirty

import pygame

from . import button


class Menu(pgcore.Scene):
    """Base class for in-game menus

    Args:
        screen (pygame.Surface): draw surface for rendering the menu
    """

    def __init__(self, screen: pygame.Surface):
        super().__init__(screen)
        # need https://github.com/pygame/pygame/pull/4635 to be merged
        # to get rid of the pylance type assignment error here
        self.buttons: LayeredDirty[button.Button] = LayeredDirty()  # type: ignore

    def draw(self) -> List[pygame.Rect]:
        self.buttons.update()
        return self.buttons.draw(self.screen)

    def handle_event(self, event: pygame.event.Event):
        # XXX: should this be button up/click instead of down?
        # best would be to catch buttondown and then trigger on
        # buttonup if mouse is inside button rect, as this is
        # normal behaviour for buttons in most applications
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    # dirty sprites so they are redrawn
                    # when the scene is reloaded
                    self.dirty_all_sprites()
                    button.on_click()
                    return
        elif event.type == pygame.MOUSEMOTION:
            for button in self.buttons:
                button.hovered = button.rect.collidepoint(event.pos)

    def tick(self, dt: float):
        pass  # noop

    def dirty_all_sprites(self):
        for btn in self.buttons:
            if btn.visible:
                btn.dirty = 1
