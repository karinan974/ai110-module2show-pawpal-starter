"""PawPal+ domain model (skeleton).

Class stubs generated from diagrams/uml_draft.mmd. Attributes and method
signatures only — no scheduling logic yet. Fill in the method bodies in
small increments (see the README workflow) and add tests as you go.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Task hierarchy
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single pet-care activity (base class for all task types)."""

    name: str
    duration: int  # minutes
    priority: str  # e.g. "high" | "medium" | "low"
    preferred_time: Optional[str] = None  # e.g. "08:00", or None if flexible
    recurring: bool = False

    def priority_score(self) -> int:
        """Return a sortable number for this task's priority (higher = sooner)."""
        raise NotImplementedError

    def describe(self) -> str:
        """Return a human-readable one-line description of this task."""
        raise NotImplementedError


@dataclass
class Walk(Task):
    """A walk/exercise task."""

    def describe(self) -> str:
        raise NotImplementedError


@dataclass
class Feeding(Task):
    """A feeding task (typically recurring)."""

    def describe(self) -> str:
        raise NotImplementedError


@dataclass
class Medication(Task):
    """A medication task (should rarely, if ever, be skipped)."""

    def priority_score(self) -> int:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


@dataclass
class Grooming(Task):
    """A grooming task (flexible timing, lower priority)."""

    def describe(self) -> str:
        raise NotImplementedError


@dataclass
class Enrichment(Task):
    """An enrichment/play task (flexible timing, lower priority)."""

    def describe(self) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Pet and Owner
# ---------------------------------------------------------------------------


@dataclass
class Pet:
    """An animal being cared for; owns a list of care tasks."""

    name: str
    species: str
    breed: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner and the scheduling constraints for their day."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        raise NotImplementedError

    def all_tasks(self) -> list[Task]:
        """Gather tasks across all of this owner's pets."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Daily plan (output)
# ---------------------------------------------------------------------------


@dataclass
class DailyPlan:
    """The generated schedule plus the reasoning behind it."""

    scheduled_items: list = field(default_factory=list)  # e.g. list[tuple[str, Task]]
    total_minutes: int = 0
    skipped_tasks: list[Task] = field(default_factory=list)
    reasoning: str = ""

    def add_item(self, time: str, task: Task) -> None:
        """Place a task at a given time slot in the plan."""
        raise NotImplementedError

    def total_duration(self) -> int:
        """Return the total scheduled minutes."""
        raise NotImplementedError

    def display(self) -> str:
        """Return a formatted, human-readable version of the plan."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Scheduler (algorithm / "brain")
# ---------------------------------------------------------------------------


class Scheduler:
    """Turns a set of tasks + constraints into a DailyPlan.

    Not a dataclass: this is the algorithm, not a data record. It *reads*
    constraints from an Owner but does not own the domain data.
    """

    def __init__(
        self,
        tasks: list[Task],
        available_minutes: int,
        preferences: Optional[dict] = None,
    ) -> None:
        self.tasks = tasks
        self.available_minutes = available_minutes
        self.preferences = preferences or {}

    def sort_tasks(self) -> list[Task]:
        """Order tasks (e.g. by priority, then duration)."""
        raise NotImplementedError

    def filter_by_time(self) -> list[Task]:
        """Drop tasks that don't fit within the available time budget."""
        raise NotImplementedError

    def resolve_conflicts(self) -> list[Task]:
        """Handle overlapping preferred time slots."""
        raise NotImplementedError

    def generate_plan(self) -> DailyPlan:
        """Produce the daily plan from tasks and constraints."""
        raise NotImplementedError

    def explain(self) -> str:
        """Explain why the scheduler chose this plan."""
        raise NotImplementedError
