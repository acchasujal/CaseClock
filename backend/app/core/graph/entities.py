"""Graph node models for the unified investigation graph."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GraphEntityBase(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime


class Case(GraphEntityBase):
    pass


class Person(GraphEntityBase):
    pass


class Officer(GraphEntityBase):
    pass


class Unit(GraphEntityBase):
    pass


class Court(GraphEntityBase):
    pass


class Location(GraphEntityBase):
    pass


class Act(GraphEntityBase):
    pass


class Section(GraphEntityBase):
    pass


class CrimeHead(GraphEntityBase):
    pass


class CrimeSubHead(GraphEntityBase):
    pass


class Evidence(GraphEntityBase):
    pass


class Dependency(GraphEntityBase):
    pass


class ClockInstance(GraphEntityBase):
    pass


class EscalationEvent(GraphEntityBase):
    pass


class ConversationLog(GraphEntityBase):
    pass