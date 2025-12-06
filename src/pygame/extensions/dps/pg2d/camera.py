import dataclasses
from typing import List, Tuple, TypeVar

import pygame.extensions.dps.core as pgcore

import pygame

from . import common, types


@dataclasses.dataclass
class Camera2DOptions(pgcore.Configurable):
    pass


class Camera2D:

    def __init__(self, opts: Camera2DOptions, follow: common.GameObject2D):
        self.follow = follow
        x, y = self._follow_centered()
        self.pos = pygame.Vector2(x, y)

    def update(self):
        # rect.center is the draw point relative to the screen;
        # we need to follow, ie. self.x should trend towards
        # follow.rect.centerx + window_width / 2
        x, y = self._follow_centered()
        self.pos += (pygame.Vector2((x, y)) - self.pos) * 0.05
        # TODO: clamp x/y values to background bounds

    def _follow_centered(self) -> Tuple[float, float]:
        w, h = pygame.display.get_window_size()
        x = -self.follow.rect.centerx + (w / 2)
        y = -self.follow.rect.centery + (h / 2)
        return x, y

    def reset(self):
        self.pos.update(self._follow_centered())


T = TypeVar("T", bound=types.SpriteSupportsCamera)


class CameraGroup(pygame.sprite.AbstractGroup[T]):

    def __init__(
        self, *sprites: T, camera: Camera2D, background: pygame.Surface | None = None
    ):
        super().__init__(*sprites)
        self.camera = camera
        self.background = background

    def draw(
        self,
        surface: pygame.Surface,
        bgsurf: pygame.Surface | None = None,
        special_flags: int = 0,
    ) -> List[pygame.Rect]:
        sprites: List[T] = self.sprites()
        bgsurf = self.background or bgsurf
        # FIXME: get background position separately and apply camera offset
        if bgsurf is not None:
            surface.blit(bgsurf, (0, 0))

        sprite_blits = []
        for spr in sprites:
            with_camera_offset = spr.rect.move(self.camera.pos)
            sprite_blits.append(
                (spr.image, with_camera_offset, spr.source_rect, special_flags)
            )

        draw_rects = surface.blits(sprite_blits)
        if draw_rects is not None:
            self.spritedict.update(zip(sprites, draw_rects, strict=False))
            return draw_rects
        return []
