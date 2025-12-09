import dataclasses
import math
from typing import List, Tuple, Type

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
    top: bool = True
    left: bool = True
    right: bool = True
    bottom: bool = True
    # TODO: collision offsets


@dataclasses.dataclass
class PhysicsObjectSettings(pgcore.Configurable):
    # TODO: mass
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
        self.collision_box = settings.collision_box
        self.is_static = settings.is_static
        self.last_pos: types.Coordinate = self.rect.topleft

    def apply_force(self, force: pygame.Vector2):
        if not self.is_static:
            self.velocity += force

    def impact(self, o: "PhysicsObject"):
        o.apply_force(self.velocity)

    def towards(self, v: pygame.Vector2, pos: types.Coordinate) -> Tuple[bool, bool]:
        px, py = pos
        dx = px - self.rect.centerx
        dy = py - self.rect.centery
        return dx * v.x > 0, dy * v.y > 0

    def moving_towards(
        self, p: "PhysicsObject | types.Coordinate"
    ) -> Tuple[bool, bool]:
        # XXX: using the object's center will fail for e.g. slopes;
        # need to refactor this at some point
        if isinstance(p, PhysicsObject):
            p = p.rect.center
        return self.towards(self.velocity, p)

    def colliding(self, o: "PhysicsObject") -> bool:
        curr_x, curr_y = self.rect.topleft
        last_x, last_y = self.last_pos

        colliding = False

        if self.collision_box.top and o.collision_box.bottom:
            colliding = colliding or last_y >= o.rect.bottom >= curr_y
        if self.collision_box.bottom and o.collision_box.top:
            colliding = (
                colliding or last_y + self.rect.h <= o.rect.top <= curr_y + self.rect.h
            )
        if self.collision_box.left and o.collision_box.right:
            colliding = colliding or last_x >= o.rect.right >= curr_x
        if self.collision_box.right and o.collision_box.left:
            colliding = (
                colliding or last_x + self.rect.w <= o.rect.left <= curr_x + self.rect.w
            )

        return colliding

    def reset(self):
        super().reset()
        self.velocity = pygame.Vector2()
        self.last_pos = self.origin


# TODO: rework the surface concept to have multiple surfaces per object
class PhysicsSurface(PhysicsObject):

    settings_type: Type[PhysicsObjectSettings] = PhysicsSurfaceSettings

    def __init__(self, settings: PhysicsSurfaceSettings, rect: pygame.Rect):
        super().__init__(settings, rect)
        self.incline = settings.incline
        self.friction_coefficient = settings.friction_coefficient
        self.restitution_coefficient = settings.restitution_coefficient

    def normal(self, o: PhysicsObject) -> pygame.Vector2:
        tx, ty = o.moving_towards(self)
        # perpendicular to the surface
        # FIXME: need this to work for a box; that is, side and top of the same object
        # maybe surface should be reworked so that an object has multiple surfaces with
        # different incline values?
        mx = -o.velocity.x * math.cos(math.radians(90 - self.incline)) if tx else 0
        my = -o.velocity.y * math.cos(math.radians(self.incline)) if ty else 0
        return pygame.Vector2(mx, my)

    def friction(self, net_force: pygame.Vector2) -> pygame.Vector2:
        if net_force.length() == 0:
            return pygame.Vector2()
        mx = self.friction_coefficient * math.cos(math.radians(self.incline))
        my = self.friction_coefficient * math.cos(math.radians(90 - self.incline))
        friction_f = pygame.Vector2(mx, my)
        # parallel to the surface, opposite the direction of force
        friction_f = friction_f.elementwise() * net_force.rotate(180).normalize()
        # the force of friction cannot exceed the net force on the object
        abs_x, abs_y = abs(net_force.x), abs(net_force.y)
        friction_f.x = pygame.math.clamp(friction_f.x, -abs_x, abs_x)
        friction_f.y = pygame.math.clamp(friction_f.y, -abs_y, abs_y)
        return friction_f

    def fix_overlap(self, o: PhysicsObject):
        """Move an overlapping object such that it no longer intersects.

        Args:
            o (PhysicsObject): the overlapping physics object
        """
        overlap = o.rect.clip(self.rect)
        normal = self.normal(o)
        x = pygame.math.clamp(normal.x, -overlap.w, overlap.w)
        y = pygame.math.clamp(normal.y, -overlap.h, overlap.h)
        o.rect.move_ip((x, y))

    def impact(self, o: PhysicsObject):
        if not o.is_static:
            self.fix_overlap(o)
        # collision with a surface is a special case - apply the normal vector
        # and force of friction based on the object's direction of movement
        normal = self.normal(o)
        o.apply_force(normal * (1 + self.restitution_coefficient))
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

    def add_physics_objects(self, *o: PhysicsObject):
        self._objects.extend(o)

    def update(self, dt: float):
        for i, o in enumerate(self._objects):
            o.update(dt)

            o.apply_force(self._gravity_f)

            # use a rect 1 pixel larger than o in all directions so that we
            # still collide when left/right or top/bottom edges are equal
            boundary_lefttop = (o.rect.left - 1, o.rect.top - 1)
            boundary_size = (o.rect.w + 2, o.rect.h + 2)
            boundary = pygame.Rect(boundary_lefttop, boundary_size)

            remaining = self._objects[i + 1 :]
            collisions = boundary.collideobjectsall(remaining, key=lambda o: o.rect)

            for c in collisions:
                if o.is_static and c.is_static:
                    continue
                if o.colliding(c):
                    o.impact(c)
                    c.impact(o)

            o.velocity.y = min(o.velocity.y, self.terminal_velocity)
            # store last position for collision detection
            o.last_pos = o.rect.topleft
            # XXX: is there a better way to apply dt? slight variations won't
            # have any impact at this scale; maybe better to scale up values
            # and apply to all changes by passing to apply force..?
            o.rect.move_ip(o.velocity * (1 + dt))

    def reset(self):
        for o in self._objects:
            o.reset()
