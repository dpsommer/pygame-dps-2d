import dataclasses
import math
from typing import List, Type

import pygame.extensions.dps.core as pgcore

import pygame

from . import common, types


@dataclasses.dataclass
class PhysicsSettings(pgcore.Configurable):
    gravity: float
    # XXX: have this be a separate configurable value for simplicity
    terminal_velocity: float


@dataclasses.dataclass
class CollisionBox(pgcore.Configurable):
    top: bool
    left: bool
    right: bool
    bottom: bool
    # TODO: collision offsets


@dataclasses.dataclass
class PhysicsObjectSettings(pgcore.Configurable):
    # TODO: mass
    max_speed: float
    collision_box: CollisionBox
    is_static: bool = False


@dataclasses.dataclass
class PhysicsSurfaceSettings(PhysicsObjectSettings):
    # XXX: treat each surface as having a single
    # static friction coefficient with all other
    # objects to avoid overcomplexity
    friction_coefficient: float = 0.8
    restitution_coefficient: float = 0.0
    incline: float = 0.0


# PhysicsObject2D is the lowest-level free-body physics object in 2 dimensions
class PhysicsObject(pgcore.Loadable, common.GameObject):

    settings_type: Type[PhysicsObjectSettings] = PhysicsObjectSettings

    def __init__(self, settings: PhysicsObjectSettings, rect: pygame.Rect):
        super().__init__(rect)

        self.velocity = pygame.Vector2()
        self.max_speed = settings.max_speed
        self.collision_box = settings.collision_box
        self.is_static = settings.is_static
        self.last_pos: types.Coordinate = self.rect.topleft

    def falling(self):
        return self.velocity.y > 0

    def apply_force(self, force: pygame.Vector2):
        if not self.is_static:
            self.velocity += force
        # TODO: air "resistance" for horizontal movement
        # if self.falling():
        #     force.x *= self._air_manoeuvring_coefficient

    def impact(self, o: "PhysicsObject"):
        self.fix_overlap(o)
        o.apply_force(self.velocity)

    def fix_overlap(self, o: "PhysicsObject"):
        """Move an overlapping object such that it no longer intersects.

        Magnitude of the vector is determined using Pythagorean theorem with
        the width and height of the clipping area, and vector direction is
        the inverted direction of impact.

        Args:
            o (PhysicsObject): the overlapping physics object
        """
        overlap = o.rect.clip(self.rect)
        magnitude = overlap.w**2 + overlap.h**2
        fix_vector = o.velocity.rotate(180).normalize() * magnitude
        o.rect.move_ip(fix_vector)

    def colliding(self, o: "PhysicsObject") -> bool:
        curr_x, curr_y = self.rect.topleft
        last_x, last_y = self.last_pos

        if self.collision_box.top and o.collision_box.bottom:
            return last_y > o.rect.bottom >= curr_y
        if self.collision_box.bottom and o.collision_box.top:
            return last_y + self.rect.h < o.rect.top <= curr_y + self.rect.h
        if self.collision_box.left and o.collision_box.right:
            return last_x > o.rect.right >= curr_x
        if self.collision_box.right and o.collision_box.left:
            return last_x + self.rect.w < o.rect.left <= curr_x + self.rect.w
        return False

    def reset(self):
        super().reset()
        self.velocity = pygame.Vector2()
        self.last_pos = self.origin


class PhysicsSurface(PhysicsObject):

    settings_type: Type[PhysicsObjectSettings] = PhysicsSurfaceSettings

    def __init__(self, settings: PhysicsSurfaceSettings, rect: pygame.Rect):
        super().__init__(settings, rect)
        self.incline = settings.incline
        self.friction_coefficient = settings.friction_coefficient
        self.restitution_coefficient = settings.restitution_coefficient

    def normal(self, gravity: float) -> pygame.Vector2:
        magnitude = -gravity * math.cos(math.radians(self.incline))
        return pygame.Vector2(0, magnitude).rotate(self.incline)

    def friction(self, net_force: pygame.Vector2) -> pygame.Vector2:
        # friction should be a vector opposite the net force
        friction = net_force.rotate(180).normalize() * self.friction_coefficient
        # the force of friction cannot exceed the net force on the object
        return pygame.Vector2(
            min(net_force.x, friction.x), min(net_force.y, friction.y)
        )

    def impact(self, o: PhysicsObject):
        super().impact(o)
        # collision with a surface is a special case - apply the normal vector
        # and force of friction based on the object's direction of movement
        normal = self.normal(o.velocity.y)
        normal *= 1 + self.restitution_coefficient
        # FIXME: make sure that this always zeros out
        o.apply_force(normal)
        o.apply_force(self.friction(o.velocity))


class PhysicsController(pgcore.Loadable):

    settings_type: Type[PhysicsSettings] = PhysicsSettings

    def __init__(self, settings: PhysicsSettings) -> None:
        self._gravity = settings.gravity
        self._gravity_f = pygame.Vector2(0, self._gravity)
        self.terminal_velocity = settings.terminal_velocity
        self._objects: List[PhysicsObject] = []

    @property
    def gravity(self) -> float:
        return self._gravity

    @gravity.setter
    def gravity(self, g: float):
        self._gravity = g
        self._gravity_f.y = g

    def add_physics_object(self, o: PhysicsObject):
        self._objects.append(o)

    def update(self, dt: float):
        for i, o in enumerate(self._objects):
            o.apply_force(self._gravity_f)

            remaining = self._objects[i + 1 :]
            collisions = o.rect.collideobjectsall(remaining, key=lambda o: o.rect)
            for c in collisions:
                if o.colliding(c):
                    o.impact(c)
                    c.impact(o)

            o.velocity.x = max(o.velocity.x, o.max_speed)
            o.velocity.y = min(o.velocity.y, self.terminal_velocity)
            # store last position for collision detection
            o.last_pos = o.rect.topleft
            o.rect.move_ip(o.velocity * dt)

    def reset(self):
        for o in self._objects:
            o.reset()
