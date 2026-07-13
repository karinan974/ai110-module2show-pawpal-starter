# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running `python main.py` builds one owner (Alex) with two pets — Biscuit (dog)
and Mittens (cat) — adds care tasks at different times, and prints the generated
schedule:

```text
Pets registered: Biscuit, Mittens
Time available today: 120 minutes

================================================
Today's Schedule
================================================
Daily plan for Alex:
  08:00 — 🐕 Morning walk (30 min) [priority: high]  ·  Biscuit
  09:00 — 🍽️ Breakfast (10 min) [priority: high]  ·  Biscuit
  09:15 — 💊 Heart meds (5 min) [priority: high]  ·  Biscuit
  09:30 — 🍽️ Breakfast (10 min) [priority: medium]  ·  Mittens
  17:00 — 🛁 Brush coat (15 min) [priority: low]  ·  Mittens
  17:15 — 🧸 Puzzle toy (20 min) [priority: low]  ·  Biscuit

Why this plan:
  Scheduled 6 task(s) using 90 of 120 available minutes. Tasks are ordered by priority (medications first), then by shorter duration so more fit in the day.
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```text
$ pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.9.0, pytest-8.4.2, pluggy-1.6.0
collected 13 items

tests/test_pawpal.py::test_mark_complete_changes_status PASSED           [  7%]
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED      [ 15%]
tests/test_pawpal.py::test_filter_by_status_keeps_only_incomplete PASSED [ 23%]
tests/test_pawpal.py::test_generate_plan_skips_completed_tasks PASSED    [ 30%]
tests/test_pawpal.py::test_filter_by_pet_returns_only_that_pets_tasks PASSED [ 38%]
tests/test_pawpal.py::test_sort_by_time_orders_timed_first_flexible_last PASSED [ 46%]
tests/test_pawpal.py::test_for_day_includes_daily_and_matching_weekly PASSED [ 53%]
tests/test_pawpal.py::test_conflict_detection_records_shifted_task PASSED [ 61%]
tests/test_pawpal.py::test_completing_daily_task_spawns_next_day PASSED  [ 69%]
tests/test_pawpal.py::test_completing_weekly_task_spawns_next_week PASSED [ 76%]
tests/test_pawpal.py::test_completing_once_task_does_not_spawn PASSED    [ 84%]
tests/test_pawpal.py::test_detect_conflicts_flags_same_time_across_pets PASSED [ 92%]
tests/test_pawpal.py::test_detect_conflicts_empty_when_no_clash PASSED   [100%]

============================== 13 passed in 0.03s ==============================
```

The suite covers task completion, pet/task wiring, the filter and sort methods,
recurring-task regeneration, and both conflict-detection paths.

## 📐 Smarter Scheduling

All scheduling behavior lives in the `Scheduler` class (the "brain") in
`pawpal_system.py`, with recurrence handled on `Task`. Each feature and the
method that implements it:

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| **Priority sorting** | `Scheduler.sort_tasks()` | Orders by priority (desc), then shorter duration first, so more tasks fit the day. Medications outrank everything via `Medication.priority_score()`. |
| **Chronological sorting** | `Scheduler.sort_by_time()` | Sorts by the `"HH:MM"` preferred-time string directly (zero-padded 24h strings sort in clock order); flexible/untimed tasks fall to the end. |
| **Filter by pet** | `Scheduler.filter_by_pet(tasks, pet_name)` | Returns only the named pet's tasks (uses the `Task.pet` back-reference). |
| **Filter by status** | `Scheduler.filter_by_status(tasks, done=False)` | Keeps incomplete tasks by default; `generate_plan()` uses it to skip already-completed tasks. |
| **Time-budget filtering** | `Scheduler.filter_by_time()` | Drops tasks once the owner's `available_minutes` runs out — but medications always stay. |
| **Conflict detection** | `Scheduler.detect_conflicts()` | Lightweight, non-crashing check: groups tasks by preferred time and returns warning strings for any slot claimed by 2+ tasks (same or different pets). |
| **Conflict resolution** | `Scheduler.resolve_conflicts()` + `generate_plan()` | Placement never starts a task before the previous one ends; any task shifted off its preferred slot is recorded in `DailyPlan.conflicts`. |
| **Recurring tasks** | `Task.mark_complete()` → `Task.next_occurrence()` / `Task._next_due_date()` | Completing a `DAILY`/`WEEKLY` task auto-creates the next occurrence (today + `timedelta(days=1)` or `weeks=1`), preserving the subclass. `Scheduler.for_day(tasks, weekday)` filters weekly tasks to the right day. |
| **Explanation** | `Scheduler.explain()` | Builds the human-readable reasoning string (budget used, skips, shifted conflicts) attached to each `DailyPlan`. |

## 📸 Demo Walkthrough

Launch the app with `streamlit run app.py`, then:

1. **Set the owner and constraints.** Enter the owner's name, the total minutes
   available today, and the day's start time (e.g., `08:00`).
2. **Add a pet.** Fill in the "Add a Pet" form (name, species, breed) and click
   **Add pet** — this calls `Owner.add_pet()`. Add a second pet to see
   multi-pet scheduling.
3. **Add tasks.** Pick a pet, choose a task type (Walk, Feeding, Medication,
   Grooming, Enrichment), set duration and priority, and optionally a preferred
   time. Click **Add task** to call `Pet.add_task()`. The task appears in the
   "Current tasks" table immediately (thanks to `st.session_state`).
4. **Create a deliberate clash** by giving two tasks the same preferred time —
   the app can then show conflict handling.
5. **Generate the schedule.** Click **Generate schedule** to run
   `Scheduler.from_owner(owner).generate_plan()`. The plan lists each task with
   its assigned time and pet, notes any tasks skipped for time, flags shifted
   conflicts, and shows the reasoning.

To try the same flow in the terminal instead, run `python main.py`, which builds
a two-pet scenario and prints the sorting, filtering, conflict-detection, and
schedule output shown in the Sample Output section above.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
