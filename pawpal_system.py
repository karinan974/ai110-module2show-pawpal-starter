"""PawPal+ domain model.

Core implementation of the PawPal+ classes. The design separates *data*
(Task, Pet, Owner, DailyPlan) from the *algorithm* (Scheduler), so the
scheduling logic can be tested in isolation.

Key types:
  * Priority / Frequency  -- enums so invalid values can't break sorting.
  * Time is handled as minutes-since-midnight via helpers, so overlaps and
    end-times are computable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import Enum, IntEnum
from typing import Optional


# ---------------------------------------------------------------------------
# Value types / helpers
# ---------------------------------------------------------------------------


class Priority(IntEnum):
    """Task priority. IntEnum so higher value == more urgent when sorting."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Frequency(Enum):
    """How often a task recurs (replaces the old recurring bool)."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


def time_to_minutes(hhmm: str) -> int:
    """Convert a 'HH:MM' string to minutes since midnight (e.g. '08:30' -> 510)."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to a 'HH:MM' string (e.g. 510 -> '08:30')."""
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


# ---------------------------------------------------------------------------
# Task hierarchy
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single pet-care activity (base class for all task types)."""

    name: str
    duration: int  # minutes
    priority: Priority = Priority.MEDIUM
    preferred_time: Optional[str] = None  # "HH:MM", or None if flexible
    frequency: Frequency = Frequency.ONCE
    scheduled_weekday: Optional[int] = None  # 0=Mon..6=Sun; only used for WEEKLY
    due_date: Optional[date] = None  # the day this occurrence is due
    completed: bool = False
    # Back-reference to the owning pet. Set by Pet.add_task(); excluded from
    # repr/eq to avoid infinite recursion (Pet holds Tasks, Task holds Pet).
    pet: Optional["Pet"] = field(default=None, repr=False, compare=False)

    def priority_score(self) -> int:
        """Return a sortable number for this task's priority (higher = sooner)."""
        return int(self.priority)

    def preferred_start_minutes(self) -> Optional[int]:
        """Return preferred_time as minutes since midnight, or None if flexible."""
        if self.preferred_time is None:
            return None
        return time_to_minutes(self.preferred_time)

    def _next_due_date(self) -> Optional[date]:
        """Return the next occurrence's date, or None if the task doesn't recur.

        Uses timedelta so date arithmetic rolls over months/years correctly.
        Counts forward from this task's due_date if set, else from today.
        """
        base = self.due_date or date.today()
        if self.frequency is Frequency.DAILY:
            return base + timedelta(days=1)
        if self.frequency is Frequency.WEEKLY:
            return base + timedelta(weeks=1)  # +7 days keeps the same weekday
        return None  # ONCE tasks do not recur

    def next_occurrence(self) -> Optional["Task"]:
        """Return a fresh, incomplete copy scheduled for the next date.

        Returns None for non-recurring (ONCE) tasks. The clone keeps the same
        subclass, name, duration, priority, time, and frequency.
        """
        next_due = self._next_due_date()
        if next_due is None:
            return None
        # replace() builds a new instance of the same subclass with these
        # fields overridden; pet is cleared so add_task() can re-link it.
        return replace(self, completed=False, due_date=next_due, pet=None)

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task as done; recurring tasks spawn their next occurrence.

        For DAILY/WEEKLY tasks that belong to a pet, a new incomplete instance
        for the next date is created and added to that pet. Returns the new
        task (or None if the task doesn't recur).
        """
        self.completed = True
        upcoming = self.next_occurrence()
        if upcoming is not None and self.pet is not None:
            self.pet.add_task(upcoming)
        return upcoming

    def _label(self) -> str:
        """Icon-free base label; subclasses prepend an icon in describe()."""
        status = "✓ " if self.completed else ""
        return f"{status}{self.name} ({self.duration} min) [priority: {self.priority.name.lower()}]"

    def describe(self) -> str:
        """Return a human-readable one-line description of this task."""
        return self._label()


@dataclass
class Walk(Task):
    """A walk/exercise task."""

    def describe(self) -> str:
        """Return the task label prefixed with a dog icon."""
        return f"🐕 {self._label()}"


@dataclass
class Feeding(Task):
    """A feeding task (typically recurring daily)."""

    def describe(self) -> str:
        """Return the task label prefixed with a food icon."""
        return f"🍽️ {self._label()}"


@dataclass
class Medication(Task):
    """A medication task.

    Overrides priority_score() to outrank everything else; filter_by_time()
    also lets medications bypass the time budget so they're never skipped.
    """

    def priority_score(self) -> int:
        """Return a score above any ordinary priority so meds sort first."""
        # Sit above the highest ordinary priority so meds always sort first.
        return int(Priority.HIGH) + 100

    def describe(self) -> str:
        """Return the task label prefixed with a pill icon."""
        return f"💊 {self._label()}"


@dataclass
class Grooming(Task):
    """A grooming task (flexible timing, lower priority)."""

    def describe(self) -> str:
        """Return the task label prefixed with a bath icon."""
        return f"🛁 {self._label()}"


@dataclass
class Enrichment(Task):
    """An enrichment/play task (flexible timing, lower priority)."""

    def describe(self) -> str:
        """Return the task label prefixed with a toy icon."""
        return f"🧸 {self._label()}"


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
        """Add a care task to this pet and set the task's back-reference."""
        task.pet = self
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        self.tasks.remove(task)
        task.pet = None

    def list_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        return list(self.tasks)


@dataclass
class Owner:
    """The pet owner and the scheduling constraints for their day."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Gather tasks across all of this owner's pets (flattened)."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.list_tasks())
        return tasks


# ---------------------------------------------------------------------------
# Daily plan (output)
# ---------------------------------------------------------------------------


@dataclass
class ScheduledItem:
    """One placed task: a start time plus the task itself.

    The task carries its own pet, so display() can name who it's for.
    """

    start_time: str  # "HH:MM"
    task: Task


@dataclass
class DailyPlan:
    """The generated schedule plus the reasoning behind it."""

    owner_name: str = ""
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)  # tasks shifted off their preferred time
    reasoning: str = ""

    def add_item(self, start_time: str, task: Task) -> None:
        """Place a task at a given start time in the plan."""
        self.scheduled_items.append(ScheduledItem(start_time, task))

    def total_duration(self) -> int:
        """Return the total scheduled minutes (computed from scheduled_items)."""
        return sum(item.task.duration for item in self.scheduled_items)

    def display(self) -> str:
        """Return a formatted, human-readable version of the plan."""
        header = f"Daily plan for {self.owner_name or 'your pets'}:"
        lines = [header]
        for item in self.scheduled_items:
            owner_of = f"  ·  {item.task.pet.name}" if item.task.pet else ""
            lines.append(f"  {item.start_time} — {item.task.describe()}{owner_of}")
        if self.skipped_tasks:
            lines.append("")
            lines.append("Skipped (out of time):")
            for task in self.skipped_tasks:
                lines.append(f"  - {task.describe()}")
        if self.conflicts:
            lines.append("")
            lines.append("Time conflicts (shifted):")
            for c in self.conflicts:
                lines.append(f"  - {c['task']}: wanted {c['requested']}, moved to {c['actual']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler (algorithm / "brain")
# ---------------------------------------------------------------------------


class Scheduler:
    """Turns a set of tasks + constraints into a DailyPlan.

    Not a dataclass: this is the algorithm, not a data record. It *reads*
    constraints from an Owner (see from_owner) but does not own the domain data.
    """

    def __init__(
        self,
        tasks: list[Task],
        available_minutes: int,
        day_start: str = "08:00",
        preferences: Optional[dict] = None,
        owner_name: str = "",
    ) -> None:
        """Store the task list and scheduling constraints."""
        self.tasks = tasks
        self.available_minutes = available_minutes
        self.day_start = day_start  # clock anchor for assigning slots
        self.preferences = preferences or {}
        self.owner_name = owner_name

    @classmethod
    def from_owner(cls, owner: Owner, day_start: str = "08:00") -> "Scheduler":
        """Build a Scheduler from an Owner's tasks and constraints.

        This is how the Scheduler retrieves every task across all of the
        owner's pets: it delegates to Owner.all_tasks(), which flattens each
        pet's task list into one collection.
        """
        return cls(
            tasks=owner.all_tasks(),
            available_minutes=owner.available_minutes,
            day_start=day_start,
            preferences=owner.preferences,
            owner_name=owner.name,
        )

    # --- filters / sorts: each takes a task list and returns a new one so they
    # --- compose, e.g. filter_by_time(sort_tasks(filter_by_status(tasks))).

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority (desc), then shorter duration first."""
        return sorted(tasks, key=lambda t: (-t.priority_score(), t.duration))

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks chronologically by their 'HH:MM' time; untimed tasks last.

        Zero-padded 24-hour strings sort lexicographically in clock order
        ("08:00" < "09:30" < "17:00"), so we can sort the preferred_time
        strings directly with a lambda key. Tasks with no preferred time get
        the sentinel "99:99" so they sort after any real time; priority breaks
        ties when two tasks share a slot.
        """
        return sorted(
            tasks,
            key=lambda t: (t.preferred_time or "99:99", -t.priority_score()),
        )

    def filter_by_pet(self, tasks: list[Task], pet_name: str) -> list[Task]:
        """Keep only tasks belonging to the named pet."""
        return [t for t in tasks if t.pet is not None and t.pet.name == pet_name]

    def filter_by_status(self, tasks: list[Task], done: bool = False) -> list[Task]:
        """Keep tasks whose completed flag matches `done` (incomplete by default)."""
        return [t for t in tasks if t.completed == done]

    def for_day(self, tasks: list[Task], weekday: int) -> list[Task]:
        """Keep tasks that occur on the given weekday (0=Mon..6=Sun).

        ONCE and DAILY tasks always occur; WEEKLY tasks occur only when their
        scheduled_weekday matches.
        """
        kept: list[Task] = []
        for task in tasks:
            if task.frequency in (Frequency.ONCE, Frequency.DAILY):
                kept.append(task)
            elif task.frequency is Frequency.WEEKLY and task.scheduled_weekday == weekday:
                kept.append(task)
        return kept

    def filter_by_time(self, tasks: list[Task]) -> list[Task]:
        """Keep tasks that fit the time budget; medications always stay."""
        kept: list[Task] = []
        used = 0
        for task in tasks:
            if isinstance(task, Medication):
                kept.append(task)  # meds bypass the budget
                used += task.duration
            elif used + task.duration <= self.available_minutes:
                kept.append(task)
                used += task.duration
        return kept

    def detect_conflicts(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """Return warning messages for tasks that share the same preferred time.

        Lightweight strategy: group tasks by their 'HH:MM' preferred_time and
        flag any slot claimed by two or more tasks — whether they belong to the
        same pet or different pets. Untimed (flexible) tasks are ignored.

        Returns an empty list when there are no clashes; it never raises, so
        callers can print the warnings and keep going.
        """
        if tasks is None:
            tasks = self.tasks

        by_time: dict[str, list[Task]] = {}
        for task in tasks:
            if task.preferred_time is None:
                continue  # flexible tasks can't clash on a fixed slot
            by_time.setdefault(task.preferred_time, []).append(task)

        warnings: list[str] = []
        for slot in sorted(by_time):
            clashing = by_time[slot]
            if len(clashing) > 1:
                labels = ", ".join(
                    f"{t.name} ({t.pet.name})" if t.pet else t.name for t in clashing
                )
                warnings.append(f"⚠️  Conflict at {slot}: {labels}")
        return warnings

    def resolve_conflicts(self, tasks: list[Task]) -> list[Task]:
        """Order timed tasks by their preferred slot; flexible tasks follow.

        Actual overlap prevention happens during placement in generate_plan(),
        which never starts a task before the previous one ends.
        """
        timed = [t for t in tasks if t.preferred_start_minutes() is not None]
        flexible = [t for t in tasks if t.preferred_start_minutes() is None]
        timed.sort(key=lambda t: t.preferred_start_minutes())
        return timed + flexible

    def generate_plan(
        self, weekday: Optional[int] = None, include_completed: bool = False
    ) -> DailyPlan:
        """Produce the daily plan by running the pipeline over self.tasks.

        By default, already-completed tasks are excluded. Pass a `weekday`
        (0=Mon..6=Sun) to also drop weekly tasks not scheduled for that day.
        """
        candidates = list(self.tasks)
        if not include_completed:
            candidates = self.filter_by_status(candidates, done=False)
        if weekday is not None:
            candidates = self.for_day(candidates, weekday)

        ordered = self.sort_tasks(candidates)
        kept = self.filter_by_time(ordered)
        placed_order = self.resolve_conflicts(kept)

        kept_ids = {id(t) for t in kept}
        skipped = [t for t in candidates if id(t) not in kept_ids]

        plan = DailyPlan(owner_name=self.owner_name, skipped_tasks=skipped)
        clock = time_to_minutes(self.day_start)
        for task in placed_order:
            preferred = task.preferred_start_minutes()
            # Honor a preferred time if it's not in the past relative to the
            # clock; otherwise place the task right after the previous one.
            start = max(clock, preferred) if preferred is not None else clock
            plan.add_item(minutes_to_time(start), task)
            # Conflict detection: a timed task pushed past its preferred slot
            # collided with an earlier task and had to be shifted.
            if preferred is not None and start > preferred:
                plan.conflicts.append(
                    {
                        "task": task.name,
                        "requested": minutes_to_time(preferred),
                        "actual": minutes_to_time(start),
                    }
                )
            clock = start + task.duration

        plan.reasoning = self.explain(plan)
        return plan

    def explain(self, plan: DailyPlan) -> str:
        """Explain why the scheduler chose this plan."""
        parts = [
            f"Scheduled {len(plan.scheduled_items)} task(s) using "
            f"{plan.total_duration()} of {self.available_minutes} available minutes.",
            "Tasks are ordered by priority (medications first), then by shorter "
            "duration so more fit in the day.",
        ]
        if plan.skipped_tasks:
            names = ", ".join(t.name for t in plan.skipped_tasks)
            parts.append(f"Skipped due to the time budget: {names}.")
        if plan.conflicts:
            notes = "; ".join(
                f"{c['task']} wanted {c['requested']} but was moved to {c['actual']}"
                for c in plan.conflicts
            )
            parts.append(f"Time conflicts resolved by shifting: {notes}.")
        return " ".join(parts)
