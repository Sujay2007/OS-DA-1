import streamlit as st
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Process Lab",
    page_icon="⚙️",
    layout="wide"
)

# ============================================================
# CONSTANTS
# ============================================================

ROOT_PID = 1000
INIT_PID = 1


# ============================================================
# SESSION STATE
# ============================================================

if "processes" not in st.session_state:
    st.session_state.processes = {}

if "next_pid" not in st.session_state:
    st.session_state.next_pid = 1001

if "selected_pid" not in st.session_state:
    st.session_state.selected_pid = ROOT_PID

if "logs" not in st.session_state:
    st.session_state.logs = []

if "last_event" not in st.session_state:
    st.session_state.last_event = ""

if "initialized" not in st.session_state:
    st.session_state.initialized = False


# ============================================================
# INITIALIZATION
# ============================================================

def initialize():

    st.session_state.processes = {
        ROOT_PID: {
            "pid": ROOT_PID,
            "ppid": 0,
            "name": "Process 1000",
            "state": "Running",
            "type": "Parent",
            "waiting": False
        }
    }

    st.session_state.next_pid = 1001
    st.session_state.selected_pid = ROOT_PID

    st.session_state.logs = [
        "Process 1000 created."
    ]

    st.session_state.last_event = (
        "Process 1000 is running. "
        "Select it and use fork() to create a child."
    )

    st.session_state.initialized = True


if not st.session_state.initialized:
    initialize()


# ============================================================
# BASIC HELPERS
# ============================================================

def get_process(pid):
    return st.session_state.processes.get(pid)


def get_children(pid):
    return [
        process
        for process in st.session_state.processes.values()
        if process["ppid"] == pid
    ]


def add_log(message):
    st.session_state.logs.append(message)


def set_event(message):
    st.session_state.last_event = message
    add_log(message)


def reset():
    initialize()


# ============================================================
# FORK
# ============================================================

def fork_process(parent_pid):

    parent = get_process(parent_pid)

    if parent is None:
        return

    if parent["state"] != "Running":
        set_event(
            f"Cannot call fork(): Process {parent_pid} "
            f"is not running."
        )
        return

    child_pid = st.session_state.next_pid
    st.session_state.next_pid += 1

    child_number = len(st.session_state.processes)

    st.session_state.processes[child_pid] = {
        "pid": child_pid,
        "ppid": parent_pid,
        "name": f"Process {child_pid}",
        "state": "Running",
        "type": "Child",
        "waiting": False
    }

    set_event(
        f"fork() → Process {child_pid} created "
        f"with parent {parent_pid}."
    )

    st.session_state.selected_pid = child_pid


# ============================================================
# TERMINATE PROCESS
# ============================================================

def terminate_process(pid):

    process = get_process(pid)

    if process is None:
        return

    if process["state"] in ["Terminated", "Zombie", "Removed"]:
        set_event(
            f"Process {pid} has already terminated."
        )
        return

    # --------------------------------------------------------
    # TERMINATING A RUNNING PROCESS
    # --------------------------------------------------------

    process["state"] = "Terminated"

    # --------------------------------------------------------
    # HANDLE CHILDREN
    # --------------------------------------------------------

    children = get_children(pid)

    # Any running children become orphans.
    for child in children:

        if child["state"] == "Running":

            child["ppid"] = INIT_PID
            child["type"] = "Orphan"

            child["state"] = "Orphan"

            set_event(
                f"Process {pid} terminated. "
                f"Process {child['pid']} became an ORPHAN."
            )

        elif child["state"] == "Zombie":

            # A zombie child is reaped when its parent disappears.
            child["state"] = "Removed"
            child["type"] = "Reaped"

            set_event(
                f"Zombie child {child['pid']} was "
                f"cleaned up when parent {pid} terminated."
            )

    # --------------------------------------------------------
    # PROCESS ITSELF
    # --------------------------------------------------------

    parent = get_process(process["ppid"])

    if parent is not None:

        # If parent is waiting, child is immediately reaped.
        if parent["waiting"]:

            process["state"] = "Removed"
            process["type"] = "Reaped"

            parent["waiting"] = False

            if parent["state"] == "Waiting":
                parent["state"] = "Running"

            set_event(
                f"Process {pid} terminated while parent "
                f"{parent['pid']} was waiting. "
                f"Child was immediately REAPED."
            )

            return

        # Otherwise, the terminated child becomes a zombie.
        if process["state"] == "Terminated":

            process["state"] = "Zombie"
            process["type"] = "Zombie"

            set_event(
                f"Process {pid} terminated. "
                f"Parent {parent['pid']} has not called wait(). "
                f"Process {pid} is now a ZOMBIE."
            )

            return

    # --------------------------------------------------------
    # ORPHAN TERMINATION
    # --------------------------------------------------------

    if process["type"] == "Orphan":

        process["state"] = "Removed"
        process["type"] = "Reaped"

        set_event(
            f"Orphan process {pid} terminated "
            f"and was removed."
        )

        return

    # --------------------------------------------------------
    # ROOT PROCESS
    # --------------------------------------------------------

    if pid == ROOT_PID:

        set_event(
            f"Root process {pid} terminated."
        )


# ============================================================
# WAIT
# ============================================================

def wait_process(parent_pid):

    parent = get_process(parent_pid)

    if parent is None:
        return

    if parent["state"] != "Running":
        set_event(
            f"Process {parent_pid} cannot call wait() "
            f"because it is not running."
        )
        return

    children = get_children(parent_pid)

    # --------------------------------------------------------
    # FIND ZOMBIE CHILD
    # --------------------------------------------------------

    zombie_children = [
        child
        for child in children
        if child["state"] == "Zombie"
    ]

    if zombie_children:

        zombie = zombie_children[0]

        zombie["state"] = "Removed"
        zombie["type"] = "Reaped"

        set_event(
            f"Process {parent_pid} called wait(). "
            f"Zombie {zombie['pid']} was REAPED."
        )

        return

    # --------------------------------------------------------
    # RUNNING CHILD
    # --------------------------------------------------------

    running_children = [
        child
        for child in children
        if child["state"] in ["Running", "Orphan"]
    ]

    if running_children:

        parent["waiting"] = True
        parent["state"] = "Waiting"

        set_event(
            f"Process {parent_pid} called wait(). "
            f"It is now WAITING for a child to terminate."
        )

        return

    # --------------------------------------------------------
    # NO CHILDREN
    # --------------------------------------------------------

    set_event(
        f"Process {parent_pid} has no child "
        f"available for wait()."
    )


# ============================================================
# PROCESS TREE
# ============================================================

def render_tree(pid, depth=0):

    process = get_process(pid)

    if process is None:
        return

    # --------------------------------------------------------
    # STATE ICON
    # --------------------------------------------------------

    state = process["state"]

    icons = {
        "Running": "🟢",
        "Waiting": "🟡",
        "Zombie": "🔴",
        "Orphan": "🟠",
        "Terminated": "⚫",
        "Removed": "⚪"
    }

    icon = icons.get(state, "⚪")

    # --------------------------------------------------------
    # SELECTED PROCESS
    # --------------------------------------------------------

    selected = (
        process["pid"] == st.session_state.selected_pid
    )

    marker = " **← selected**" if selected else ""

    # --------------------------------------------------------
    # PROCESS DISPLAY
    # --------------------------------------------------------

    indent = "&nbsp;" * (depth * 8)

    st.markdown(
        f"""
        {indent}{icon} **P{process['pid']}**
        — {state}
        {marker}
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # CHILDREN
    # --------------------------------------------------------

    children = get_children(pid)

    for child in children:

        if child["state"] != "Removed":
            render_tree(child["pid"], depth + 1)


# ============================================================
# PROCESS TABLE
# ============================================================

def process_table():

    rows = []

    for process in st.session_state.processes.values():

        if process["state"] == "Removed":
            continue

        rows.append(
            {
                "PID": process["pid"],
                "PPID": process["ppid"],
                "State": process["state"],
                "Type": process["type"]
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["PID", "PPID", "State", "Type"]
        )

    return pd.DataFrame(rows).sort_values("PID")


# ============================================================
# MAIN UI
# ============================================================

st.title("⚙️ Process Lab")

st.caption(
    "Interactive Orphan & Zombie Process Simulator"
)


# ============================================================
# TOP STATUS
# ============================================================

selected = get_process(
    st.session_state.selected_pid
)

if selected is None:
    st.session_state.selected_pid = ROOT_PID
    selected = get_process(ROOT_PID)


# ============================================================
# PROCESS TREE
# ============================================================

st.subheader("Process Tree")

tree_container = st.container(
    border=True
)

with tree_container:

    render_tree(ROOT_PID)

    # Show adopted/orphan processes.
    orphan_roots = [
        process
        for process in st.session_state.processes.values()
        if process["ppid"] == INIT_PID
        and process["pid"] != ROOT_PID
        and process["state"] != "Removed"
    ]

    if orphan_roots:

        st.markdown("---")
        st.caption("Adopted by the operating system")

        for orphan in orphan_roots:

            icon = "🟠" if orphan["state"] == "Orphan" else "⚪"

            st.markdown(
                f"{icon} **P{orphan['pid']}** "
                f"— {orphan['state']} "
                f"(PPID: 1)"
            )


# ============================================================
# SELECT PROCESS
# ============================================================

st.subheader("Selected Process")

process_options = [
    pid
    for pid, process in st.session_state.processes.items()
    if process["state"] != "Removed"
]

if process_options:

    selected_pid = st.selectbox(
        "Choose a process to control",
        process_options,
        index=(
            process_options.index(
                st.session_state.selected_pid
            )
            if st.session_state.selected_pid
            in process_options
            else 0
        ),
        format_func=lambda pid:
            f"P{pid} — {get_process(pid)['state']}"
    )

    st.session_state.selected_pid = selected_pid

    selected = get_process(selected_pid)


# ============================================================
# SELECTED PROCESS DETAILS
# ============================================================

if selected:

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "PID",
            selected["pid"]
        )

    with col2:

        st.metric(
            "PPID",
            selected["ppid"]
        )

    with col3:

        st.metric(
            "State",
            selected["state"]
        )

    if selected["type"] in [
        "Zombie",
        "Orphan"
    ]:

        if selected["type"] == "Zombie":

            st.error(
                f"💀 P{selected['pid']} is a ZOMBIE. "
                f"It has terminated but remains in the "
                f"process table until its parent calls wait()."
            )

        else:

            st.warning(
                f"👻 P{selected['pid']} is an ORPHAN. "
                f"Its parent terminated while it was still running."
            )


# ============================================================
# ACTIONS
# ============================================================

st.subheader("Actions")

action1, action2, action3 = st.columns(3)


# ------------------------------------------------------------
# FORK
# ------------------------------------------------------------

with action1:

    if st.button(
        "＋ fork()",
        use_container_width=True
    ):

        fork_process(
            st.session_state.selected_pid
        )

        st.rerun()


# ------------------------------------------------------------
# TERMINATE
# ------------------------------------------------------------

with action2:

    if st.button(
        "🛑 Terminate",
        use_container_width=True
    ):

        terminate_process(
            st.session_state.selected_pid
        )

        st.rerun()


# ------------------------------------------------------------
# WAIT
# ------------------------------------------------------------

with action3:

    if st.button(
        "⏳ wait()",
        use_container_width=True
    ):

        wait_process(
            st.session_state.selected_pid
        )

        st.rerun()


# ============================================================
# LAST EVENT
# ============================================================

if st.session_state.last_event:

    st.info(
        st.session_state.last_event
    )


# ============================================================
# RESET
# ============================================================

if st.button(
    "↻ Reset Simulation",
    use_container_width=True
):

    reset()
    st.rerun()


# ============================================================
# COLLAPSIBLE INFORMATION
# ============================================================

with st.expander("Process Table"):

    st.dataframe(
        process_table(),
        use_container_width=True,
        hide_index=True
    )


with st.expander("Event Log"):

    for number, event in enumerate(
        st.session_state.logs,
        start=1
    ):

        st.write(
            f"{number}. {event}"
        )


with st.expander("What are Orphans and Zombies?"):

    st.markdown(
        """
        **Zombie**

        A child terminates while its parent is still alive,
        but the parent has not yet collected the child's
        termination status using `wait()`.

        **Orphan**

        A parent terminates while its child is still running.
        The child is then adopted by another system process.

        **Important distinction**

        A zombie has **terminated** but still has a process-table
        entry.

        An orphan is **still running** even though its original
        parent has terminated.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Windows-safe simulation • No real operating-system "
    "processes are created"
)
