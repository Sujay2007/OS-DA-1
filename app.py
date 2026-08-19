import io
import streamlit as st
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Process Lab",
    layout="wide"
)

# ============================================================
# CONSTANTS
# ============================================================

ROOT_PID = 1000
INIT_PID = 1

STATE_META = {
    "Running":    {"label": "RUNNING",    "class": "badge-running"},
    "Waiting":    {"label": "WAITING",    "class": "badge-waiting"},
    "Zombie":     {"label": "ZOMBIE",     "class": "badge-zombie"},
    "Orphan":     {"label": "ORPHAN",     "class": "badge-orphan"},
    "Terminated": {"label": "TERMINATED", "class": "badge-terminated"},
    "Removed":    {"label": "REMOVED",    "class": "badge-removed"},
}


def badge_html(state):
    meta = STATE_META.get(
        state,
        {"label": state.upper(), "class": "badge-removed"}
    )
    return f'<span class="state-badge {meta["class"]}">{meta["label"]}</span>'


# ============================================================
# GLOBAL STYLES
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --bg:            #0f1115;
        --surface:       #161922;
        --surface-alt:   #1c2029;
        --border:        #2a2f3a;
        --text:          #e7e9ee;
        --text-muted:    #9aa2b1;
        --accent:        #6c8cff;
        --accent-soft:   rgba(108, 140, 255, 0.14);

        --running:       #3ddc84;
        --waiting:       #f5c451;
        --zombie:        #f5566b;
        --orphan:        #ff9e5e;
        --terminated:    #7d8494;
        --removed:       #4a4f5b;
    }

    /* ---------- App shell ---------- */
    .stApp {
        background: radial-gradient(circle at 20% 0%, #171b26 0%, var(--bg) 55%);
        color: var(--text);
    }

    html, body, [class*="css"] {
        font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
    }

    section.main > div {
        padding-top: 1.5rem;
    }

    /* ---------- Header ---------- */
    .app-header {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin-bottom: 1.25rem;
    }

    .app-header h1 {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: var(--text);
    }

    .app-header p {
        margin: 0;
        color: var(--text-muted);
        font-size: 0.95rem;
    }

    /* ---------- Section headings ---------- */
    h3, .stMarkdown h3 {
        font-size: 1.02rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted) !important;
        margin-top: 0 !important;
        margin-bottom: 0.75rem !important;
    }

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px 10px 0 0;
        padding: 0.6rem 1.1rem;
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.92rem;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        background: var(--accent-soft) !important;
    }

    /* ---------- Cards / containers ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
    }

    /* ---------- State badges ---------- */
    .state-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        line-height: 1.6;
        white-space: nowrap;
    }

    .badge-running    { background: rgba(61, 220, 132, 0.15); color: var(--running); }
    .badge-waiting    { background: rgba(245, 196, 81, 0.15); color: var(--waiting); }
    .badge-zombie     { background: rgba(245, 86, 107, 0.16); color: var(--zombie); }
    .badge-orphan     { background: rgba(255, 158, 94, 0.16); color: var(--orphan); }
    .badge-terminated { background: rgba(125, 132, 148, 0.18); color: var(--terminated); }
    .badge-removed    { background: rgba(74, 79, 91, 0.18);   color: var(--text-muted); }

    /* ---------- Process tree ---------- */
    .tree-node {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.4rem 0.6rem;
        margin: 0.15rem 0;
        border-radius: 8px;
        border-left: 2px solid transparent;
        font-size: 0.92rem;
    }

    .tree-node.selected {
        background: var(--accent-soft);
        border-left: 2px solid var(--accent);
    }

    .tree-node .pid-label {
        font-weight: 600;
        color: var(--text);
    }

    .tree-node .selected-tag {
        color: var(--accent);
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-left: auto;
    }

    .adopted-heading {
        color: var(--text-muted);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0.9rem 0 0.4rem 0;
    }

    /* ---------- Alert banners (zombie / orphan callouts) ---------- */
    .info-banner {
        border-radius: 10px;
        padding: 0.85rem 1.1rem;
        font-size: 0.9rem;
        line-height: 1.45;
        margin-top: 0.75rem;
        border: 1px solid;
    }

    .info-banner.zombie {
        background: rgba(245, 86, 107, 0.08);
        border-color: rgba(245, 86, 107, 0.35);
        color: #ffb4bf;
    }

    .info-banner.orphan {
        background: rgba(255, 158, 94, 0.08);
        border-color: rgba(255, 158, 94, 0.35);
        color: #ffc79a;
    }

    .info-banner b { color: inherit; }

    /* ---------- Metrics ---------- */
    div[data-testid="stMetric"] {
        background: var(--surface-alt);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
    }

    /* ---------- Buttons ---------- */
    .stButton > button {
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.15s ease;
    }

    .stButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"] {
        background: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #0f1115 !important;
    }

    .stButton > button[kind="primary"]:hover {
        filter: brightness(1.08);
        color: #0f1115 !important;
    }

    /* ---------- Selectbox ---------- */
    div[data-baseweb="select"] > div {
        background: var(--surface-alt) !important;
        border-color: var(--border) !important;
        border-radius: 10px !important;
    }

    /* ---------- Expanders ---------- */
    details {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    /* ---------- Code blocks (C code tab) ---------- */
    .code-caption {
        color: var(--text-muted);
        font-size: 0.85rem;
        margin: -0.25rem 0 0.75rem 0;
    }

    /* ---------- Definition cards ---------- */
    .def-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
    }

    .def-card h4 {
        margin-top: 0;
        margin-bottom: 0.5rem;
        font-size: 1.05rem;
    }

    .def-card.zombie h4 { color: var(--zombie); }
    .def-card.orphan h4 { color: var(--orphan); }

    /* ---------- Divider / caption ---------- */
    .footer-caption {
        color: var(--text-muted);
        font-size: 0.8rem;
        text-align: center;
        margin-top: 0.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


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

if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False


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
    st.session_state.confirm_reset = False


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

    state = process["state"]

    selected = (
        process["pid"] == st.session_state.selected_pid
    )

    node_class = "tree-node selected" if selected else "tree-node"
    indent_px = depth * 26

    selected_tag = (
        '<span class="selected-tag">SELECTED</span>' if selected else ""
    )

    st.markdown(
        f"""
        <div class="{node_class}" style="margin-left:{indent_px}px;">
            <span class="pid-label">P{process['pid']}</span>
            {badge_html(state)}
            {selected_tag}
        </div>
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

def process_table(state_filter=None):

    rows = []

    for process in st.session_state.processes.values():

        if process["state"] == "Removed":
            continue

        if state_filter and state_filter != "All" and process["state"] != state_filter:
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


def state_counts():

    counts = {key: 0 for key in STATE_META.keys()}

    for process in st.session_state.processes.values():
        if process["state"] in counts:
            counts[process["state"]] += 1

    return counts


# ============================================================
# C CODE SNIPPETS (reference only — not executed)
# ============================================================

ZOMBIE_C_CODE = r"""#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork failed");
        exit(EXIT_FAILURE);
    }

    if (pid == 0) {
        /* ---- Child process ---- */
        printf("Child (PID %d): running, about to exit.\n", getpid());
        exit(EXIT_SUCCESS);          /* Child dies almost immediately. */
    } else {
        /* ---- Parent process ---- */
        printf("Parent (PID %d): forked child PID %d.\n", getpid(), pid);
        printf("Parent is sleeping for 30s WITHOUT calling wait().\n");
        printf("In another terminal run:\n");
        printf("  ps -o pid,ppid,stat,cmd -p %d\n", pid);
        printf("The child will show STAT = Z (zombie) the whole time.\n");

        sleep(30);

        /* Reaping it here removes the zombie from the process table. */
        wait(NULL);
        printf("Parent (PID %d): reaped the zombie child.\n", getpid());
    }

    return 0;
}
"""

ORPHAN_C_CODE = r"""#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork failed");
        exit(EXIT_FAILURE);
    }

    if (pid == 0) {
        /* ---- Child process ---- */
        printf("Child (PID %d): original parent is %d.\n",
               getpid(), getppid());

        sleep(5);   /* Give the parent time to exit first. */

        printf("Child (PID %d): new parent is now %d.\n",
               getpid(), getppid());
        printf("The child was adopted by init/systemd "
               "(or a subreaper), not left behind.\n");
    } else {
        /* ---- Parent process ---- */
        printf("Parent (PID %d): exiting immediately, "
               "child PID %d keeps running.\n", getpid(), pid);
        exit(EXIT_SUCCESS);
    }

    return 0;
}
"""

DETECTION_SHELL_SNIPPET = r"""# Find zombie processes on a real Linux system
ps aux | awk '$8=="Z" {print}'

# Or, using the STAT column directly
ps -eo pid,ppid,stat,cmd | grep 'Z'

# Watch the parent's PID of a specific process (spot re-parenting to PID 1)
watch -n 1 "ps -o pid,ppid,cmd -p <PID>"
"""


# ============================================================
# MAIN UI — HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">
        <h1>Process Lab</h1>
        <p>Interactive orphan &amp; zombie process simulator</p>
    </div>
    """,
    unsafe_allow_html=True
)

tab_sim, tab_code, tab_defs = st.tabs(
    ["Simulation", "C Code", "Definitions"]
)


# ============================================================
# TAB 1 — SIMULATION
# ============================================================

with tab_sim:

    selected = get_process(
        st.session_state.selected_pid
    )

    if selected is None:
        st.session_state.selected_pid = ROOT_PID
        selected = get_process(ROOT_PID)

    # --------------------------------------------------------
    # METRICS DASHBOARD
    # --------------------------------------------------------

    counts = state_counts()

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.metric("Running", counts["Running"])
    with m2:
        st.metric("Waiting", counts["Waiting"])
    with m3:
        st.metric("Zombies", counts["Zombie"])
    with m4:
        st.metric("Orphans", counts["Orphan"])
    with m5:
        st.metric("Terminated", counts["Terminated"])

    # --------------------------------------------------------
    # PROCESS TREE
    # --------------------------------------------------------

    st.subheader("Process Tree")

    tree_container = st.container(border=True)

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

            st.markdown(
                '<div class="adopted-heading">Adopted by the operating system</div>',
                unsafe_allow_html=True
            )

            for orphan in orphan_roots:

                st.markdown(
                    f"""
                    <div class="tree-node">
                        <span class="pid-label">P{orphan['pid']}</span>
                        {badge_html(orphan['state'])}
                        <span style="color: var(--text-muted); font-size: 0.82rem;">PPID: 1</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --------------------------------------------------------
    # SELECT PROCESS
    # --------------------------------------------------------

    st.subheader("Selected Process")

    process_options = [
        pid
        for pid, process in st.session_state.processes.items()
        if process["state"] != "Removed"
    ]

    if process_options:

        select_col, jump_col = st.columns([3, 1])

        with select_col:

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
                    f"P{pid} — {get_process(pid)['state']}",
                label_visibility="collapsed"
            )

            st.session_state.selected_pid = selected_pid

        with jump_col:

            jump_pid = st.number_input(
                "Jump to PID",
                min_value=0,
                value=0,
                step=1,
                label_visibility="collapsed",
                placeholder="Jump to PID"
            )

            if jump_pid and jump_pid in process_options:
                st.session_state.selected_pid = jump_pid
            elif jump_pid and jump_pid not in process_options:
                st.caption(f"No active process P{jump_pid}.")

        selected = get_process(st.session_state.selected_pid)

    # --------------------------------------------------------
    # SELECTED PROCESS DETAILS
    # --------------------------------------------------------

    if selected:

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("PID", selected["pid"])

        with col2:
            st.metric("PPID", selected["ppid"])

        with col3:
            st.metric("State", selected["state"])

        if selected["type"] in ["Zombie", "Orphan"]:

            if selected["type"] == "Zombie":

                st.markdown(
                    f"""
                    <div class="info-banner zombie">
                        <b>P{selected['pid']} is a zombie process.</b>
                        It has terminated but remains in the process table
                        until its parent calls wait().
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="info-banner orphan">
                        <b>P{selected['pid']} is an orphan process.</b>
                        Its parent terminated while it was still running.
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    st.subheader("Actions")

    action1, action2, action3 = st.columns(3)

    with action1:

        if st.button("Fork Process", use_container_width=True, type="primary"):
            fork_process(st.session_state.selected_pid)
            st.rerun()

    with action2:

        if st.button("Terminate", use_container_width=True):
            terminate_process(st.session_state.selected_pid)
            st.rerun()

    with action3:

        if st.button("Call wait()", use_container_width=True):
            wait_process(st.session_state.selected_pid)
            st.rerun()

    # --------------------------------------------------------
    # LAST EVENT
    # --------------------------------------------------------

    if st.session_state.last_event:
        st.info(st.session_state.last_event)

    # --------------------------------------------------------
    # RESET (with confirmation, so it isn't a one-click accident)
    # --------------------------------------------------------

    if not st.session_state.confirm_reset:

        if st.button("Reset Simulation", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()

    else:

        st.warning("This clears every process and log entry. Reset anyway?")

        confirm_col, cancel_col = st.columns(2)

        with confirm_col:
            if st.button("Confirm Reset", use_container_width=True, type="primary"):
                reset()
                st.rerun()

        with cancel_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

    # --------------------------------------------------------
    # COLLAPSIBLE INFORMATION
    # --------------------------------------------------------

    with st.expander("Process Table"):

        filter_state = st.selectbox(
            "Filter by state",
            ["All"] + list(STATE_META.keys()),
            key="table_filter"
        )

        table = process_table(filter_state)

        st.dataframe(table, use_container_width=True, hide_index=True)

    with st.expander("Event Log"):

        for number, event in enumerate(st.session_state.logs, start=1):
            st.write(f"{number}. {event}")

        if st.session_state.logs:

            log_text = "\n".join(
                f"{i}. {e}" for i, e in enumerate(st.session_state.logs, start=1)
            )

            st.download_button(
                "Download log as .txt",
                data=log_text,
                file_name="process_lab_event_log.txt",
                mime="text/plain",
                use_container_width=True
            )


# ============================================================
# TAB 2 — C CODE (reference only, not executed)
# ============================================================

with tab_code:

    st.subheader("Reference C Programs")
    st.caption("Not compiled or executed by this app.")

    code_choice = st.radio(
        "Example",
        ["Zombie process", "Orphan process", "Detection commands"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if code_choice == "Zombie process":

        st.markdown(
            '<p class="code-caption">'
            'Child exits while the parent never calls '
            '<code>wait()</code> / <code>waitpid()</code>.'
            '</p>',
            unsafe_allow_html=True
        )
        st.code(ZOMBIE_C_CODE, language="c")
        st.markdown(
            "```bash\n"
            "gcc zombie_demo.c -o zombie_demo\n"
            "./zombie_demo\n"
            "```"
        )

    elif code_choice == "Orphan process":

        st.markdown(
            '<p class="code-caption">'
            'Parent exits before its child; the child is re-parented '
            'to init or a subreaper.'
            '</p>',
            unsafe_allow_html=True
        )
        st.code(ORPHAN_C_CODE, language="c")
        st.markdown(
            "```bash\n"
            "gcc orphan_demo.c -o orphan_demo\n"
            "./orphan_demo\n"
            "```"
        )

    else:

        st.markdown(
            '<p class="code-caption">'
            'Commands for locating zombies and re-parented processes '
            'on a live system.'
            '</p>',
            unsafe_allow_html=True
        )
        st.code(DETECTION_SHELL_SNIPPET, language="bash")


# ============================================================
# TAB 3 — DEFINITIONS
# ============================================================

with tab_defs:

    st.subheader("Understanding Orphans & Zombies")

    st.markdown(
        """
        <div class="def-card zombie">
            <h4> Zombie Process</h4>
            <p>
                In Unix/Linux, every process has an exit status that its
                parent is expected to collect with <code>wait()</code> or
                <code>waitpid()</code>. When a child terminates, the kernel
                keeps a small entry in the process table — PID, exit code,
                resource usage — so the parent can retrieve it later.
            </p>
            <p>
                If the parent never calls <code>wait()</code>, that entry
                is never cleaned up. The process has already freed its
                memory, file descriptors, and other resources; only the
                table entry remains. That leftover entry is the
                <b>zombie</b> (<code>STAT = Z</code> in <code>ps</code>).
            </p>
            <p>
                Zombies cost almost nothing individually, but each one
                occupies a PID slot. A parent that never reaps them can
                eventually exhaust available process IDs. A zombie
                disappears the moment its parent calls <code>wait()</code>,
                or immediately if the parent itself terminates first
                (the zombie is then reaped by whichever process adopts it).
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="def-card orphan">
            <h4> Orphan Process</h4>
            <p>
                An <b>orphan</b> is the opposite situation: the parent
                terminates while the child is still running. The child
                doesn't stop — the kernel simply re-parents it, usually to
                <code>init</code> (PID 1) or a designated "subreaper", so
                every process always has a valid parent to eventually
                collect its exit status.
            </p>
            <p>
                Orphans are a completely normal and harmless part of
                process management — daemonized services, background
                jobs, and shells with <code>nohup</code> or <code>&amp;</code>
                rely on this behavior on purpose. The new parent
                (<code>init</code>/<code>systemd</code>) automatically
                calls <code>wait()</code> on it when it eventually exits,
                so an orphan can never become a zombie of its own accord.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("Side-by-side comparison")

    comparison_df = pd.DataFrame(
        [
            {
                "Aspect": "Is it still running?",
                "Zombie": "No — already terminated",
                "Orphan": "Yes — still executing"
            },
            {
                "Aspect": "What's missing",
                "Zombie": "Parent hasn't called wait() yet",
                "Orphan": "Original parent no longer exists"
            },
            {
                "Aspect": "Who fixes it",
                "Zombie": "Its parent, by calling wait()/waitpid()",
                "Orphan": "The kernel, by re-parenting to init/PID 1"
            },
            {
                "Aspect": "Resource use",
                "Zombie": "Just a process-table entry",
                "Orphan": "Full process — CPU, memory, file descriptors"
            },
            {
                "Aspect": "ps STAT column",
                "Zombie": "Z (defunct)",
                "Orphan": "Normal (R, S, etc.) with PPID = 1"
            },
        ]
    )

    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    st.subheader("Why this matters in practice")

    st.markdown(
        """
        - **Zombies accumulate silently.** A long-running server that
          forks workers but forgets to reap them will slowly fill up its
          process table — eventually `fork()` starts failing.
        - **Orphans are usually intentional.** Background daemons,
          detached jobs, and containers' entrypoint processes are
          designed to be orphaned/re-parented.
        - **The fix for zombies is a parent-side fix**: call
          `wait()`/`waitpid()`, or install a `SIGCHLD` handler that reaps
          children as they exit.
        - **The fix for orphans is already built into the kernel** — no
          application code needs to do anything for the re-parenting
          itself to happen safely.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    '<p class="footer-caption">Made by Sujay Krishna R | 25BCE1420 | Vellore Institute of Technology Chennai</p>',
    unsafe_allow_html=True
)
