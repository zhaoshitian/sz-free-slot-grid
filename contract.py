"""Typed input and output declarations for Free Slot Grid."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RUN = "find_slots"


class Task(Enum):
    RUN = "find-slots"


@dataclass
class Interval(Output):
    start: Annotated[int, "Inclusive minute from 0 through 1440"]
    end: Annotated[int, "Exclusive minute from 0 through 1440"]


@dataclass
class ResultRow(Output):
    start: Annotated[int, "Inclusive slot start minute"]
    end: Annotated[int, "Exclusive slot end minute"]


@dataclass
class TaskInput(Output):
    window_start: Annotated[int, "Inclusive daily search window start"]
    window_end: Annotated[int, "Exclusive daily search window end"]
    length: Annotated[int, "Meeting duration from 1 through 1440 minutes"]
    step: Annotated[int, "Start grid spacing from 1 through 1440 minutes"]
    blocked: Annotated[list[Interval], "At most 100 half-open blocked intervals"]
    destination: Annotated[str, "New relative .json output path, never overwritten"]


@dataclass
class TaskOutput(Output):
    path: Annotated[str, "Artifact path matching destination"]
    records: Annotated[list[ResultRow], "Complete ordered task results"]
    total: Annotated[int, "Number of available grid-aligned slots"]


TOOLS = {Tool.RUN: (TaskInput, TaskOutput)}
TASKS = {Task.RUN: (TaskInput, TaskOutput)}
