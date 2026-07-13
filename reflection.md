# PawPal+ Project Reflection

## 1. System Design

- Three Core Actions:
    1. Add a Pet
    2. Track Pet Care Tasks
    3. Provide a Daily Plan that considers Constraints

**a. Initial design**

My initial UML design used six classes, organized around one key split: **data objects** hold information, and a single **algorithm object** makes decisions. This keeps the scheduling logic testable in isolation and keeps the data classes simple.

- **`Task` (base class)** — represents one care activity. Holds `name`, `duration`, `priority`, optional `preferred_time`, and `recurring`. Responsible for describing itself (`describe()`) and expressing its own urgency (`priority_score()`).
- **`Walk`, `Feeding`, `Medication`, `Grooming`, `Enrichment`** — subclasses of `Task` that exist to *override behavior*, not just carry a label. `Medication`, for example, overrides `priority_score()` so meds sort to the top and are rarely skipped. This is where inheritance earns its place.
- **`Pet`** — the animal being cared for. Owns its list of `Task`s and is responsible for managing them (`add_task()`, `remove_task()`, `list_tasks()`). Tasks live here because a task is meaningless without its pet (composition).
- **`Owner`** — the person and their daily constraints. Holds `available_minutes`, `preferences`, and the list of `pets`. Responsible for being the source of constraints and for gathering every task across all pets (`all_tasks()`) to hand off for scheduling.
- **`Scheduler`** — the algorithm ("the brain"), and the only non-dataclass. Responsible for all decision-making: `sort_tasks()`, `filter_by_time()`, `resolve_conflicts()`, `generate_plan()`, and `explain()`. Isolated here because this is what the tests target.
- **`DailyPlan`** — the output. Holds `scheduled_items`, `total_minutes`, `skipped_tasks`, and `reasoning`. Kept as a separate object (rather than a plain string) so the reasoning and skipped tasks have somewhere to live — which satisfies the requirement to explain *why* the scheduler chose a plan.

**b. Design changes**

Yes. After generating the skeleton I reviewed it for missing relationships and logic bottlenecks, and made several changes before writing any scheduling logic:

- **Added a `Task` → `Pet` back-reference.** The first draft flattened every pet's tasks into one list for the scheduler, which meant a task couldn't say *which* pet it belonged to. Since the target output is "Daily plan for Biscuit," a task needs to know its pet. `Pet.add_task()` now sets this link (excluded from `repr`/`eq` to avoid infinite recursion).
- **Made the `Scheduler` steps compose.** Originally `sort_tasks()`, `filter_by_time()`, and `resolve_conflicts()` each took no arguments and read `self.tasks` fresh, so sorting was lost before filtering ran. I changed them to take a task list and return a new one, so they can be chained as a real pipeline.
- **Switched to sturdier types.** `priority` became a `Priority` enum and `recurring` became a `Frequency` enum (once/daily/weekly), so a typo can't silently break sorting and "weekly" is expressible. Times are now handled as minutes-since-midnight via helper functions, because you can't add a duration to a `"08:00"` string when checking for overlaps.
- **Tightened the output types.** I replaced the loose `(str, Task)` tuple with a `ScheduledItem` dataclass, removed the stored `total_minutes` in favor of a computed `total_duration()` (one source of truth), and added a `Scheduler.from_owner()` classmethod plus a `day_start` anchor so the "reads constraints from Owner" relationship is real in code.

The biggest lesson: the scheduling pipeline only works if the intermediate results flow between steps and time is represented as a number, not a string — problems that were invisible in the UML but obvious once I traced how the methods would actually be called.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

My `detect_conflicts()` method flags a conflict only when two tasks share the
**exact same** preferred start time (e.g., both at 09:15). It does **not**
account for overlapping durations — a 30-minute walk starting at 09:00 and a
feeding at 09:15 genuinely collide, but because their start strings differ, the
lightweight check stays silent about them. It groups tasks by their "HH:MM"
string and warns on any slot claimed more than once.

This tradeoff is reasonable for this scenario for three reasons. First, it keeps
the check simple and fast (a single O(n) pass grouping by time), which fits a
"lightweight warning" whose job is to nudge the owner, not to guarantee a
perfect timetable. Second, it never crashes and degrades gracefully: it returns
a plain list of warnings and the app keeps running. Third, the *real* overlap
handling still happens downstream — `generate_plan()` places tasks sequentially
and never starts one before the previous ends, then records any task it had to
shift in `plan.conflicts`. So exact-match detection is an early advisory, while
the scheduler's placement logic is the actual safety net. The cost is that a
purely advisory warning can miss duration-based overlaps; catching those would
mean comparing `[start, start + duration)` intervals pairwise, which is more
correct but heavier and beyond what a quick heads-up needs.

---

## 3. AI Collaboration

**a. How you used AI**

I used the AI coding assistant across every phase: brainstorming the object
model from the README, drafting the UML, generating class skeletons, filling in
scheduling logic, writing tests, and wiring the Streamlit UI. The most effective
features were:

- Whole-file context** — attaching `pawpal_system.py`  and asking targeted
  questions ("how should the Scheduler retrieve all tasks from the owner's
  pets?") produced answers grounded in my actual code, not generic advice.
- Incremental, verifiable steps** — asking for one method or one feature at a
  time (skeleton → logic → tests) kept each change small enough to check.

The most helpful prompts were specific and outcome-oriented: "what edge cases
matter for a pet scheduler with recurring tasks?", "how do I use `timedelta` to
compute the next due date?", and "is the bug in my test or my logic?".

**b. Judgment and verification**

- **A suggestion I modified:** when I asked how to simplify `detect_conflicts()`,
  the assistant offered a compact `itertools.groupby` one-liner. I rejected it —
  `groupby` yields one-shot iterators, so testing a group's length *and* listing
  its members in the same comprehension creates bugs, and the nested version was
  harder to read. I kept the plain "group into a dict, then warn" loop. Cleaner
  design beat a clever one-liner.
- **A suggestion I redirected:** the first skeleton let pets be created
  implicitly whenever a task was added. I changed it to an explicit "Add a Pet"
  form calling `Owner.add_pet()`, so each UI form maps to one class method.
- **How I verified:** I relied on the test suite (16 passing tests, including
  edge cases like an empty owner and a Dec 31 → Jan 1 recurrence rollover),
  running `main.py` to eyeball real output, and booting the Streamlit app to
  confirm it loaded without errors.

**c. AI strategy — working across phases**

Using a **separate chat session per phase** (design, implementation, testing, UI)
kept each conversation focused and prevented context from one concern bleeding
into another — the testing session, for example, stayed entirely about edge
cases and `pytest` rather than re-litigating design decisions. It also made it
easy to attach only the files relevant to that phase.

The biggest lesson was about being the **lead architect**: the AI is fast and
often right if you provide all the information needed.
The AI provided the *how*; I stayed responsible for the *what* and
the *why*.

---

## 4. Testing and Verification

**a. What you tested**

I wrote 16 tests in `tests/test_pawpal.py` covering the behaviors most likely to
break:

- **Core data behavior** — `mark_complete()` flips a task's status; `add_task()`
  grows a pet's task list.
- **Sorting** — `sort_by_time()` returns tasks in chronological order with
  flexible (untimed) tasks last.
- **Filtering** — `filter_by_status()` keeps only incomplete tasks, and
  `generate_plan()` skips completed ones; `filter_by_pet()` returns just the
  named pet's tasks.
- **Recurrence** — completing a DAILY task spawns tomorrow's copy, a WEEKLY task
  advances 7 days (same weekday), and a ONCE task spawns nothing.
- **Conflict detection** — same-time clashes are flagged both across pets and on
  the same pet; a shifted task is recorded in `plan.conflicts`.
- **Edge cases** — an owner with no tasks returns an empty plan without crashing,
  and daily recurrence rolls over the month/year boundary (Dec 31 → Jan 1).


**b. Confidence**

I am fairly confident — about **4 out of 5**. All 16 tests pass, and they cover
the core algorithms plus the edge cases I considered most fragile. The
confidence isn't higher because the tests exercise the domain logic directly,
not the Streamlit UI, and because `detect_conflicts()` only catches exact
same-time clashes rather than overlapping durations (a documented tradeoff).

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the clean separation between **data** (`Task`, `Pet`,
`Owner`, `DailyPlan`) and the **algorithm** (`Scheduler`). That single decision
paid off repeatedly: I could add sorting, filtering, recurrence, and conflict
detection as small composable methods, test them in isolation, and wire them
into the UI without touching the data classes. The composable pipeline
(sort → filter → resolve → place) made the whole system feel predictable.

**b. What you would improve**

I would unify the two recurrence mechanisms. Right now `due_date` (advanced by
`timedelta` when a task is completed) and `scheduled_weekday` (used by
`for_day()`) coexist but aren't connected, so "which day is this task actually
due" is tracked in two places. I'd make `generate_plan()` filter by a real
calendar date so the daily plan only shows tasks genuinely due today. I'd also
upgrade `detect_conflicts()` to catch overlapping durations, not just exact
time matches.

**c. Key takeaway**

The most important thing I learned is that **good structure is what makes a
system have the ability to grow**. Every feature I added in later phases was easy *because* the
early design isolated responsibilities.
