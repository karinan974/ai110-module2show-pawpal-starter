from datetime import time

import streamlit as st

# Bring the specific PawPal+ classes we need into this script's namespace.
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

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Plan your pets' care for the day. Add pets and tasks, then generate a schedule
that orders them by priority and fits them into your available time.
"""
)

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care
tasks for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

# --- Lookup tables: UI labels -> domain objects ----------------------------
PRIORITY_BY_LABEL = {
    "low": Priority.LOW,
    "medium": Priority.MEDIUM,
    "high": Priority.HIGH,
}
TASK_TYPES = {
    "Walk": Walk,
    "Feeding": Feeding,
    "Medication": Medication,
    "Grooming": Grooming,
    "Enrichment": Enrichment,
}


# --- Session vault ----------------------------------------------------------
# Create the Owner exactly once so pets/tasks persist across Streamlit reruns.
# The `if "owner" not in st.session_state` guard is what stops us from wiping
# the accumulated data every time the script re-runs.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)

owner: Owner = st.session_state.owner

st.divider()

# --- Owner & constraints ----------------------------------------------------
st.subheader("Owner & Constraints")
owner_name = st.text_input("Owner name", value=owner.name)
available = st.number_input(
    "Time available today (minutes)",
    min_value=15,
    max_value=600,
    value=owner.available_minutes,
    step=15,
)
day_start = st.text_input("Day start (HH:MM)", value="08:00")

# Sync editable fields back onto the persisted Owner each rerun (otherwise the
# name/budget would be frozen at whatever they were when the Owner was created).
owner.name = owner_name
owner.available_minutes = int(available)

st.divider()

# --- Add a pet --------------------------------------------------------------
# Submitting this form hands the data to Owner.add_pet(), which appends the
# new Pet to the owner's list. Because `owner` lives in st.session_state,
# Streamlit's rerun re-reads owner.pets and the change shows up immediately.
st.subheader("Add a Pet")
pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with pcol2:
    new_species = st.selectbox("Species", ["dog", "cat", "other"])
with pcol3:
    new_breed = st.text_input("Breed", value="")

if st.button("Add pet"):
    if not new_pet_name.strip():
        st.warning("Give the pet a name first.")
    elif any(p.name == new_pet_name for p in owner.pets):
        st.warning(f"A pet named “{new_pet_name}” already exists.")
    else:
        owner.add_pet(Pet(name=new_pet_name, species=new_species, breed=new_breed))
        st.success(f"Added {new_pet_name}.")

st.divider()

# --- Add a task -------------------------------------------------------------
# Submitting this form calls Pet.add_task() on the selected pet.
st.subheader("Add a Task")
if not owner.pets:
    st.info("Add a pet first, then you can add tasks for it.")
else:
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.selectbox("Pet", [p.name for p in owner.pets])
        task_type = st.selectbox("Task type", list(TASK_TYPES))
    with col2:
        task_title = st.text_input("Task title", value="Morning walk")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", list(PRIORITY_BY_LABEL), index=2)

    use_preferred = st.checkbox("Set a preferred time")
    preferred = st.time_input("Preferred time", value=time(8, 0)) if use_preferred else None

    if st.button("Add task"):
        pet = next(p for p in owner.pets if p.name == pet_name)
        task_cls = TASK_TYPES[task_type]
        task = task_cls(
            name=task_title,
            duration=int(duration),
            priority=PRIORITY_BY_LABEL[priority],
            preferred_time=preferred.strftime("%H:%M") if preferred else None,
        )
        pet.add_task(task)
        st.success(f"Added “{task_title}” to {pet_name}.")

# --- Current tasks ----------------------------------------------------------
# Uses the Scheduler's sort_by_time / filter_by_pet / filter_by_status methods
# so the table reflects the same logic the schedule is built from.
st.markdown("### Current tasks")
all_tasks = owner.all_tasks()
if not all_tasks:
    st.info("No tasks yet. Add one above.")
else:
    view = Scheduler.from_owner(owner, day_start=day_start)

    fcol1, fcol2 = st.columns(2)
    with fcol1:
        pet_filter = st.selectbox(
            "View tasks for", ["All pets"] + [p.name for p in owner.pets]
        )
    with fcol2:
        hide_done = st.checkbox("Hide completed", value=False)

    tasks = view.sort_by_time(all_tasks)  # chronological order
    if pet_filter != "All pets":
        tasks = view.filter_by_pet(tasks, pet_filter)
    if hide_done:
        tasks = view.filter_by_status(tasks, done=False)

    if tasks:
        st.table(
            [
                {
                    "time": t.preferred_time or "flexible",
                    "pet": t.pet.name,
                    "task": t.name,
                    "type": type(t).__name__,
                    "min": t.duration,
                    "priority": t.priority.name.lower(),
                    "status": "✓ done" if t.completed else "pending",
                }
                for t in tasks
            ]
        )
    else:
        st.caption("No tasks match this view.")

    if st.button("Clear all pets & tasks"):
        st.session_state.owner = Owner(
            name=owner_name, available_minutes=int(available)
        )
        st.rerun()

st.divider()

# --- Build schedule ---------------------------------------------------------
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    if not owner.all_tasks():
        st.warning("Add at least one task first.")
    else:
        try:
            scheduler = Scheduler.from_owner(owner, day_start=day_start)
            conflicts = scheduler.detect_conflicts()  # proactive check
            plan = scheduler.generate_plan()
        except ValueError:
            st.error("Day start must be in HH:MM format, e.g. 08:00.")
        else:
            # Same-time clashes: shown up front so the owner can rethink a slot.
            for warning in conflicts:
                st.warning(warning)

            st.success(
                f"Scheduled {len(plan.scheduled_items)} task(s) — "
                f"{plan.total_duration()} of {owner.available_minutes} minutes used."
            )

            if plan.scheduled_items:
                st.table(
                    [
                        {
                            "time": item.start_time,
                            "pet": item.task.pet.name if item.task.pet else "—",
                            "task": item.task.name,
                            "type": type(item.task).__name__,
                            "min": item.task.duration,
                            "priority": item.task.priority.name.lower(),
                        }
                        for item in plan.scheduled_items
                    ]
                )

            # Tasks the scheduler had to shift to avoid an overlap.
            for c in plan.conflicts:
                st.warning(
                    f"⏰ {c['task']} wanted {c['requested']} but was moved to "
                    f"{c['actual']} to avoid an overlap."
                )

            # Tasks dropped because the day ran out of time.
            if plan.skipped_tasks:
                names = ", ".join(t.name for t in plan.skipped_tasks)
                st.error(f"Skipped (out of time): {names}")

            st.info(plan.reasoning)
