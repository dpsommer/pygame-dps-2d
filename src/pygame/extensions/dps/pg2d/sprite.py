import dataclasses
from typing import List

import pygame.extensions.dps.core as pgcore

import pygame

from . import types


@dataclasses.dataclass
class SpriteOptions(pgcore.Configurable):
    topleft: types.Coordinate = (0, 0)
    width: float = 0
    height: float = 0
    image: pygame.Surface | None = None
    layer: int = 0


@dataclasses.dataclass
class AnimationOptions(pgcore.Configurable):
    name: str
    repeat: int


@dataclasses.dataclass
class SpriteSheetOptions(pgcore.Configurable):
    sprite_sheet: pygame.Surface
    sprite_width: int
    sprite_height: int
    animations: List[AnimationOptions]


class GameSprite(pygame.sprite.WeakDirtySprite):

    def __init__(self, opts: SpriteOptions) -> None:
        super().__init__()
        self._layer = opts.layer
        self.origin = opts.topleft
        image_size = (opts.width, opts.height)
        self.image = opts.image if opts.image else pygame.Surface(image_size)

        # source image from its bounding rect
        # (inner rect at first non-transparent pixels)
        self.source_rect = self.image.get_bounding_rect()
        self.rect = self.image.get_rect()
        self.rect.update(self.origin, self.source_rect.size)

        # store last x, y position for use in collision detection
        self.last_pos: types.Coordinate = self.rect.topleft

    def reset(self):
        self.rect.update(self.origin, self.source_rect.size)
        self.last_pos = self.rect.topleft


# TODO:
class Animation(pygame.sprite.WeakSprite):

    def __init__(self, opts: AnimationOptions, frames: List[pygame.Surface]):
        self.repeat = opts.repeat
        self.frames = frames
        self.frames_inverted = [pygame.transform.flip(f, True, False) for f in frames]
        self.image = frames[0]
        self.rect = self.image.get_rect()

    def play(self, pos: types.Coordinate):
        pass


class SpriteSheet:

    def __init__(self, opts: SpriteSheetOptions):
        self.sprite_sheet = opts.sprite_sheet
        self.sprite_width = opts.sprite_width
        self.sprite_height = opts.sprite_height
        self.animations = {}

        # each row in the sprite sheet represents an animation
        for i, animation_opts in enumerate(opts.animations):
            frames = self._split_frames(i)
            self.animations[animation_opts.name] = Animation(animation_opts, frames)

    def _split_frames(self, idx: int) -> List[pygame.Surface]:
        frames = []

        for i in range(self.sprite_sheet.get_width() // self.sprite_width):
            topleft = (i * self.sprite_width, idx * self.sprite_height)
            wh = (self.sprite_width, self.sprite_height)
            frame = self.sprite_sheet.subsurface(topleft, wh)
            # create a mask of the frame and check if it contains any
            # non-transparent pixels. if not, break and return
            mask = pygame.mask.from_surface(frame)
            if mask.count() == 0:
                break
            frames.append(frame)
        return frames
