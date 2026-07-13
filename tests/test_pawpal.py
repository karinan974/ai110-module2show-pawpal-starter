"""Tests for the PawPal+ domain model."""

from datetime import date

from pawpal_system import (
    Feeding,
    Frequency,
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    Walk,
)


def test_mark_complete_changes_status():
    """Calling mark_complete() flips a task's completed flag to True."""
    task = Task("Morning walk", duration=30)
    assert task.completed is False  # tasks start incomplete

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet grows that pet's task list by one."""
    pet = Pet("Biscuit", "Dog", "Golden Retriever")
    assert len(pet.tasks) == 0

    pet.add_task(Walk("Evening walk", duration=20))

    assert len(pet.tasks) == 1


# --- New scheduling-logic features -----------------------------------------


def _scheduler(*tasks) -> Scheduler:
    """Build a Scheduler over a throwaway pet holding the given tasks."""
    pet = Pet("Rex", "Dog", "Mutt")
    for task in tasks:
        pet.add_task(task)
    owner = Owner("Sam", available_minutes=240)
    owner.add_pet(pet)
    return Scheduler.from_owner(owner)


def test_filter_by_status_keeps_only_incomplete():
    """filter_by_status(done=False) drops completed tasks."""
    done = Walk("Done walk", duration=20)
    done.mark_complete()
    todo = Walk("Todo walk", duration=20)
    sched = _scheduler(done, todo)

    result = sched.filter_by_status(sched.tasks, done=False)

    assert result == [todo]


def test_generate_plan_skips_completed_tasks():
    """A completed task is not scheduled by default."""
    done = Walk("Done walk", duration=20)
    done.mark_complete()
    todo = Walk("Todo walk", duration=20)
    sched = _scheduler(done, todo)

    plan = sched.generate_plan()
    scheduled_names = [item.task.name for item in plan.scheduled_items]

    assert scheduled_names == ["Todo walk"]


def test_filter_by_pet_returns_only_that_pets_tasks():
    """filter_by_pet keeps tasks belonging to the named pet."""
    biscuit = Pet("Biscuit", "Dog", "Golden")
    mittens = Pet("Mittens", "Cat", "Tabby")
    biscuit.add_task(Walk("Walk", duration=20))
    mittens.add_task(Feeding("Feed", duration=10))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(biscuit)
    owner.add_pet(mittens)
    sched = Scheduler.from_owner(owner)

    result = sched.filter_by_pet(sched.tasks, "Biscuit")

    assert [t.name for t in result] == ["Walk"]


def test_sort_by_time_orders_timed_first_flexible_last():
    """sort_by_time puts earlier preferred times first, untimed tasks last."""
    late = Walk("Late", duration=10, preferred_time="17:00")
    early = Walk("Early", duration=10, preferred_time="08:00")
    flexible = Walk("Flexible", duration=10)
    sched = _scheduler(late, early, flexible)

    ordered = sched.sort_by_time(sched.tasks)

    assert [t.name for t in ordered] == ["Early", "Late", "Flexible"]


def test_for_day_includes_daily_and_matching_weekly():
    """for_day keeps daily tasks and only same-day weekly tasks."""
    daily = Feeding("Breakfast", duration=10, frequency=Frequency.DAILY)
    monday = Walk("Monday walk", duration=20, frequency=Frequency.WEEKLY,
                  scheduled_weekday=0)
    friday = Walk("Friday groom", duration=20, frequency=Frequency.WEEKLY,
                  scheduled_weekday=4)
    sched = _scheduler(daily, monday, friday)

    result = sched.for_day(sched.tasks, weekday=0)  # Monday

    names = {t.name for t in result}
    assert names == {"Breakfast", "Monday walk"}


def test_conflict_detection_records_shifted_task():
    """Two tasks wanting overlapping slots produce a recorded conflict."""
    first = Walk("First", duration=30, priority=Priority.HIGH, preferred_time="08:00")
    clash = Feeding("Clash", duration=10, priority=Priority.HIGH, preferred_time="08:10")
    sched = _scheduler(first, clash)

    plan = sched.generate_plan()

    assert len(plan.conflicts) == 1
    assert plan.conflicts[0]["task"] == "Clash"
    assert plan.conflicts[0]["requested"] == "08:10"
    assert plan.conflicts[0]["actual"] == "08:30"  # bumped to after First ends


# --- Recurring task regeneration -------------------------------------------


def test_completing_daily_task_spawns_next_day():
    """Completing a DAILY task adds a fresh copy due tomorrow to the pet."""
    pet = Pet("Rex", "Dog", "Mutt")
    task = Feeding("Breakfast", duration=10, frequency=Frequency.DAILY,
                   due_date=date(2026, 7, 12))
    pet.add_task(task)

    upcoming = task.mark_complete()

    assert len(pet.tasks) == 2  # original + next occurrence
    assert isinstance(upcoming, Feeding)  # subclass preserved
    assert upcoming.due_date == date(2026, 7, 13)  # today + 1 day
    assert upcoming.completed is False
    assert upcoming.pet is pet  # re-linked to the same pet


def test_completing_weekly_task_spawns_next_week():
    """Completing a WEEKLY task advances the due date by 7 days, same weekday."""
    pet = Pet("Rex", "Dog", "Mutt")
    task = Walk("Park visit", duration=40, frequency=Frequency.WEEKLY,
                scheduled_weekday=0, due_date=date(2026, 7, 6))  # a Monday
    pet.add_task(task)

    upcoming = task.mark_complete()

    assert upcoming.due_date == date(2026, 7, 13)  # +1 week
    assert upcoming.scheduled_weekday == 0  # still Monday


def test_completing_once_task_does_not_spawn():
    """A non-recurring (ONCE) task creates no next occurrence."""
    pet = Pet("Rex", "Dog", "Mutt")
    task = Walk("One-off vet trip", duration=60)  # frequency defaults to ONCE
    pet.add_task(task)

    result = task.mark_complete()

    assert result is None
    assert len(pet.tasks) == 1


# --- Same-time conflict detection ------------------------------------------


def test_detect_conflicts_flags_same_time_across_pets():
    """Two tasks (different pets) at the same slot produce one warning."""
    biscuit = Pet("Biscuit", "Dog", "Golden")
    mittens = Pet("Mittens", "Cat", "Tabby")
    biscuit.add_task(Walk("Meds", duration=5, preferred_time="09:15"))
    mittens.add_task(Feeding("Breakfast", duration=10, preferred_time="09:15"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(biscuit)
    owner.add_pet(mittens)
    sched = Scheduler.from_owner(owner)

    warnings = sched.detect_conflicts()

    assert len(warnings) == 1
    assert "09:15" in warnings[0]
    assert "Meds" in warnings[0] and "Breakfast" in warnings[0]


def test_detect_conflicts_empty_when_no_clash():
    """Distinct times (and flexible tasks) yield no warnings."""
    pet = Pet("Rex", "Dog", "Mutt")
    pet.add_task(Walk("Walk", duration=20, preferred_time="08:00"))
    pet.add_task(Feeding("Feed", duration=10, preferred_time="09:00"))
    pet.add_task(Walk("Play", duration=15))  # flexible, no preferred_time
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler.from_owner(owner)

    assert sched.detect_conflicts() == []


# --- Edge cases -------------------------------------------------------------


def test_generate_plan_with_no_tasks_returns_empty_plan():
    """An owner with a pet but no tasks yields an empty plan, not a crash."""
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(Pet("Rex", "Dog", "Mutt"))  # pet, but zero tasks
    sched = Scheduler.from_owner(owner)

    plan = sched.generate_plan()

    assert plan.scheduled_items == []
    assert plan.skipped_tasks == []
    assert plan.total_duration() == 0


def test_detect_conflicts_flags_same_pet_duplicate_times():
    """Two tasks on the SAME pet at the same slot are also flagged."""
    pet = Pet("Rex", "Dog", "Mutt")
    pet.add_task(Walk("Walk", duration=20, preferred_time="07:30"))
    pet.add_task(Feeding("Feed", duration=10, preferred_time="07:30"))
    owner = Owner("Sam", available_minutes=120)
    owner.add_pet(pet)
    sched = Scheduler.from_owner(owner)

    warnings = sched.detect_conflicts()

    assert len(warnings) == 1
    assert "07:30" in warnings[0]


def test_daily_recurrence_rolls_over_month_boundary():
    """timedelta advances a daily task from Dec 31 to Jan 1 correctly."""
    pet = Pet("Rex", "Dog", "Mutt")
    task = Feeding("Dinner", duration=10, frequency=Frequency.DAILY,
                   due_date=date(2026, 12, 31))
    pet.add_task(task)

    upcoming = task.mark_complete()

    assert upcoming.due_date == date(2027, 1, 1)  # month AND year roll over
