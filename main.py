"""PawPal+ demo script.

Builds a small scenario — one owner, two pets, tasks added *out of order* —
then demonstrates the Scheduler's sorting and filtering methods and prints
today's schedule to the terminal.

Run it with:

    python main.py
"""

from pawpal_system import (
    Enrichment,
    Feeding,
    Grooming,
    Medication,
    Owner,
    Pet,
    Priority,
    Scheduler,
    Walk,
)


def build_owner() -> Owner:
    """Create an owner with two pets and tasks added in a jumbled time order."""
    owner = Owner(name="Alex", available_minutes=120)

    # Tasks are intentionally added OUT OF chronological order so the sorting
    # methods have something real to fix.
    biscuit = Pet(name="Biscuit", species="Dog", breed="Golden Retriever")
    biscuit.add_task(Enrichment("Puzzle toy", duration=20, priority=Priority.LOW,
                                preferred_time="17:00"))
    biscuit.add_task(Walk("Morning walk", duration=30, priority=Priority.HIGH,
                          preferred_time="08:00"))
    biscuit.add_task(Medication("Heart meds", duration=5, priority=Priority.HIGH,
                                preferred_time="09:15"))

    mittens = Pet(name="Mittens", species="Cat", breed="Tabby")
    mittens.add_task(Grooming("Brush coat", duration=15, priority=Priority.LOW,
                              preferred_time="12:30"))
    # Deliberate clash: this is at 09:15, the same slot as Biscuit's heart meds,
    # so detect_conflicts() has a real cross-pet conflict to warn about.
    mittens.add_task(Feeding("Breakfast", duration=10, priority=Priority.MEDIUM,
                             preferred_time="09:15"))

    owner.add_pet(biscuit)
    owner.add_pet(mittens)
    return owner


def print_tasks(title: str, tasks) -> None:
    """Print a labeled list of tasks with their time and pet."""
    print(title)
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        when = task.preferred_time or "flexible"
        pet = task.pet.name if task.pet else "?"
        print(f"  {when} — {task.describe()}  ·  {pet}")


def main() -> None:
    owner = build_owner()
    scheduler = Scheduler.from_owner(owner, day_start="08:00")

    print(f"Pets registered: {', '.join(pet.name for pet in owner.pets)}")
    print(f"Time available today: {owner.available_minutes} minutes\n")

    # --- Order tasks were entered (jumbled) ------------------------------
    print_tasks("Tasks as entered (out of order):", scheduler.tasks)
    print()

    # --- Sorting by time -------------------------------------------------
    print_tasks("Sorted by time (sort_by_time):", scheduler.sort_by_time(scheduler.tasks))
    print()

    # --- Filtering by pet ------------------------------------------------
    print_tasks("Filtered to Biscuit (filter_by_pet):",
                scheduler.filter_by_pet(scheduler.tasks, "Biscuit"))
    print()

    # --- Filtering by completion status ----------------------------------
    # Mark one task done, then show only what's still outstanding.
    scheduler.tasks[1].mark_complete()  # Biscuit's "Morning walk"
    print_tasks("Still to do (filter_by_status done=False):",
                scheduler.filter_by_status(scheduler.tasks, done=False))
    print()

    # --- Conflict detection ----------------------------------------------
    print("Conflict check (detect_conflicts):")
    warnings = scheduler.detect_conflicts()
    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("  No same-time conflicts found.")
    print()

    # --- Final generated schedule ----------------------------------------
    plan = scheduler.generate_plan()
    print("=" * 48)
    print("Today's Schedule")
    print("=" * 48)
    print(plan.display())
    print()
    print("Why this plan:")
    print(f"  {plan.reasoning}")


if __name__ == "__main__":
    main()
