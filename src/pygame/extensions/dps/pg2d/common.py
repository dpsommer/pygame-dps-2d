import pygame


# common class for 2D game objects
# XXX: flesh this out
class GameObject2D:

    def __init__(self, rect: pygame.Rect):
        self.origin = rect.topleft
        self.original_size = rect.size
        self.rect = rect

    def reset(self):
        self.rect.update(self.origin, self.original_size)
