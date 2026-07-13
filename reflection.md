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

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
