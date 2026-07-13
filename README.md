# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## ✨ Features

- **Multi-pet task tracking** — one owner manages several pets, each with its own care tasks (walks, feeding, meds, grooming, enrichment).
- **Priority-aware scheduling** — tasks are ordered by priority, then by shorter duration to fit more into the day; medications always sort first and are never dropped for time.
- **Sorting by time** — `sort_by_time()` returns tasks in chronological order (flexible/untimed tasks last).
- **Filtering** — view tasks by pet (`filter_by_pet`) or by completion status (`filter_by_status`); completed tasks are skipped when building a plan.
- **Time-budget fitting** — tasks that don't fit the owner's available minutes are dropped and reported (`filter_by_time`).
- **Conflict warnings** — `detect_conflicts()` flags two tasks wanting the same time slot (same pet or across pets), and the planner reports any task it shifted to avoid an overlap.
- **Daily & weekly recurrence** — completing a recurring task auto-creates the next occurrence (tomorrow for daily, +7 days for weekly) using `timedelta`.
- **Explained plans** — every generated plan includes a plain-language reason for its choices.

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
python -m pytest

# Run with coverage:
pytest --cov
```

**What the tests cover** (16 tests in `tests/test_pawpal.py`):

- **Core behaviors** — task completion (`mark_complete`) and adding tasks to a pet.
- **Sorting correctness** — `sort_by_time()` returns tasks in chronological order, flexible tasks last.
- **Filtering** — by completion status and by pet; `generate_plan()` skips completed tasks.
- **Recurrence logic** — completing a daily task creates a new task for the next day, weekly advances 7 days, and once-off tasks don't recur.
- **Conflict detection** — `detect_conflicts()` flags duplicate times (same pet and across pets); shifted tasks are recorded during placement.
- **Edge cases** — an owner with no tasks returns an empty plan (no crash), and daily recurrence rolls over the month/year boundary (Dec 31 → Jan 1).

Successful run:

```text
$ python -m pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.9.0, pytest-8.4.2, pluggy-1.6.0
collected 16 items

tests/test_pawpal.py::test_mark_complete_changes_status PASSED           [  6%]
tests/test_pawpal.py::test_add_task_increases_pet_task_count PASSED      [ 12%]
tests/test_pawpal.py::test_filter_by_status_keeps_only_incomplete PASSED [ 18%]
tests/test_pawpal.py::test_generate_plan_skips_completed_tasks PASSED    [ 25%]
tests/test_pawpal.py::test_filter_by_pet_returns_only_that_pets_tasks PASSED [ 31%]
tests/test_pawpal.py::test_sort_by_time_orders_timed_first_flexible_last PASSED [ 37%]
tests/test_pawpal.py::test_for_day_includes_daily_and_matching_weekly PASSED [ 43%]
tests/test_pawpal.py::test_conflict_detection_records_shifted_task PASSED [ 50%]
tests/test_pawpal.py::test_completing_daily_task_spawns_next_day PASSED  [ 56%]
tests/test_pawpal.py::test_completing_weekly_task_spawns_next_week PASSED [ 62%]
tests/test_pawpal.py::test_completing_once_task_does_not_spawn PASSED    [ 68%]
tests/test_pawpal.py::test_detect_conflicts_flags_same_time_across_pets PASSED [ 75%]
tests/test_pawpal.py::test_detect_conflicts_empty_when_no_clash PASSED   [ 81%]
tests/test_pawpal.py::test_generate_plan_with_no_tasks_returns_empty_plan PASSED [ 87%]
tests/test_pawpal.py::test_detect_conflicts_flags_same_pet_duplicate_times PASSED [ 93%]
tests/test_pawpal.py::test_daily_recurrence_rolls_over_month_boundary PASSED [100%]

============================== 16 passed in 0.06s ==============================
```

**Confidence Level: ★★★★☆ (4 / 5)**

The core scheduling logic — sorting, filtering, recurrence, and conflict
detection — is covered by unit tests including edge cases, and all 16 pass.
One star is held back because the tests exercise the domain logic directly, not
the Streamlit UI, and `detect_conflicts()` only catches exact same-time clashes
rather than overlapping durations (see the tradeoff in `reflection.md`).

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

### Main UI features (what a user can do)

Launch the app with `streamlit run app.py`. The single-page UI lets a user:

- **Set owner & constraints** — owner name, minutes available today, and the day's start time.
- **Add pets** — name, species, breed (each becomes a schedulable pet).
- **Add tasks** — choose the pet, a task type (Walk / Feeding / Medication / Grooming / Enrichment), duration, priority, and an optional preferred time.
- **Review current tasks** — a live table with a "View tasks for" pet filter and a "Hide completed" toggle, sorted chronologically.
- **Generate a schedule** — a formatted plan table plus warning/info banners.

### Example workflow

1. **Add a pet** → fill the "Add a Pet" form and click **Add pet** (calls `Owner.add_pet()`).
2. **Schedule a task** → pick that pet, set duration/priority/preferred time, click **Add task** (calls `Pet.add_task()`). It appears instantly in the Current tasks table (state persists via `st.session_state`).
3. **View today's schedule** → click **Generate schedule** (runs `Scheduler.from_owner(owner).generate_plan()`).

### Key Scheduler behaviors shown

- **Sorting** — the Current tasks table is ordered by time (`sort_by_time`); the plan orders by priority.
- **Filtering** — the pet dropdown (`filter_by_pet`) and "Hide completed" toggle (`filter_by_status`) change what's shown.
- **Conflict warnings** — two tasks at the same time raise an `st.warning` banner (`detect_conflicts`), and any task the planner shifts is reported ("moved to 09:20 to avoid an overlap").
- **Skipped tasks** — anything that won't fit the time budget is flagged with `st.error`.
- **Reasoning** — the plan's explanation is shown in an `st.info` banner.

### Sample CLI output (`python main.py`)

```text
Sorted by time (sort_by_time):
  08:00 — 🐕 Morning walk (30 min) [priority: high]  ·  Biscuit
  09:15 — 💊 Heart meds (5 min) [priority: high]  ·  Biscuit
  09:15 — 🍽️ Breakfast (10 min) [priority: medium]  ·  Mittens
  12:30 — 🛁 Brush coat (15 min) [priority: low]  ·  Mittens
  17:00 — 🧸 Puzzle toy (20 min) [priority: low]  ·  Biscuit

Conflict check (detect_conflicts):
  ⚠️  Conflict at 09:15: Heart meds (Biscuit), Breakfast (Mittens)

================================================
Today's Schedule
================================================
Daily plan for Alex:
  09:15 — 💊 Heart meds (5 min) [priority: high]  ·  Biscuit
  09:20 — 🍽️ Breakfast (10 min) [priority: medium]  ·  Mittens
  12:30 — 🛁 Brush coat (15 min) [priority: low]  ·  Mittens
  17:00 — 🧸 Puzzle toy (20 min) [priority: low]  ·  Biscuit

Time conflicts (shifted):
  - Breakfast: wanted 09:15, moved to 09:20

Why this plan:
  Scheduled 4 task(s) using 50 of 120 available minutes. Tasks are ordered by
  priority (medications first), then by shorter duration so more fit in the day.
  Time conflicts resolved by shifting: Breakfast wanted 09:15 but was moved to 09:20.
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
