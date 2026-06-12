#!/usr/bin/env python3
"""build_ui.py — tkinter GUI for the JL site builder.

Reads the scan plan from builders.scan.build_plan(), lists units in a
Listbox, and shells `python3 build.py --only <unit>` (or `build.py` for
all) streaming stdout+stderr into a text pane.

This is a dev/authoring convenience tool. The canonical interface is:
    python3 Toolbox/Python/build.py

No network listener, no shell=True. Safe to leave running while editing YAML.
"""

import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import scrolledtext
import tkinter as tk

# ---------------------------------------------------------------------------
# Paths & scan plan
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent.resolve()
_BUILD_PY = _HERE / 'build.py'

sys.path.insert(0, str(_HERE))
from builder_common import project_root as _detect_root
from builders import scan

_ROOT = _detect_root()
_PLAN = scan.build_plan(_ROOT)


# ---------------------------------------------------------------------------
# Background build runner
# ---------------------------------------------------------------------------

def _run_build(extra_args: list, out_queue: queue.Queue) -> None:
    """Run build.py in a thread; post each output line to out_queue.

    Sentinel None is posted when the process finishes.
    """
    cmd = [sys.executable, str(_BUILD_PY)] + extra_args
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            out_queue.put(line)
        proc.wait()
        out_queue.put(f'\n[exit {proc.returncode}]\n')
    except Exception as exc:
        out_queue.put(f'\nERROR launching build: {exc}\n')
    finally:
        out_queue.put(None)  # sentinel: done


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class BuildUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('JL Site Builder')
        self.minsize(820, 500)
        self._queue: queue.Queue = queue.Queue()
        self._building = False
        self._setup_ui()
        self._poll_queue()

    # ── layout ───────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Left panel: unit list + buttons
        left = tk.Frame(self, padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left, text='Build units', anchor='w',
                 font=('', 11, 'bold')).pack(fill=tk.X, pady=(0, 4))

        list_frame = tk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)

        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(
            list_frame,
            yscrollcommand=vsb.set,
            selectmode=tk.SINGLE,
            width=28,
            font=('Courier', 11),
            activestyle='dotbox',
        )
        vsb.config(command=self._listbox.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for unit in _PLAN:
            self._listbox.insert(tk.END, unit.label())
        if _PLAN:
            self._listbox.selection_set(0)

        # Double-click triggers single-unit build
        self._listbox.bind('<Double-Button-1>', lambda _e: self._build_selected())

        btn_frame = tk.Frame(left, pady=8)
        btn_frame.pack(fill=tk.X)

        self._btn_one = tk.Button(btn_frame, text='Build Selected',
                                  command=self._build_selected)
        self._btn_one.pack(fill=tk.X, pady=(0, 4))

        self._btn_all = tk.Button(btn_frame, text='Build All',
                                  command=self._build_all)
        self._btn_all.pack(fill=tk.X)

        # Right panel: output
        right = tk.Frame(self, padx=10, pady=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hdr = tk.Frame(right)
        hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr, text='Output', anchor='w',
                 font=('', 11, 'bold')).pack(side=tk.LEFT)
        tk.Button(hdr, text='Clear', command=self._clear_output,
                  padx=6).pack(side=tk.RIGHT)

        self._output = scrolledtext.ScrolledText(
            right,
            state=tk.DISABLED,
            font=('Courier', 10),
            wrap=tk.WORD,
            bg='#111',
            fg='#d4cfca',
            insertbackground='white',
        )
        self._output.pack(fill=tk.BOTH, expand=True)

        self._status = tk.StringVar(value='Ready.')
        tk.Label(right, textvariable=self._status,
                 anchor='w', fg='#888').pack(fill=tk.X, pady=(4, 0))

    # ── output helpers ────────────────────────────────────────────────────────

    def _write(self, text: str) -> None:
        self._output.config(state=tk.NORMAL)
        self._output.insert(tk.END, text)
        self._output.see(tk.END)
        self._output.config(state=tk.DISABLED)

    def _clear_output(self) -> None:
        self._output.config(state=tk.NORMAL)
        self._output.delete('1.0', tk.END)
        self._output.config(state=tk.DISABLED)
        self._status.set('Ready.')

    # ── build coordination ────────────────────────────────────────────────────

    def _set_building(self, active: bool) -> None:
        self._building = active
        state = tk.DISABLED if active else tk.NORMAL
        self._btn_one.config(state=state)
        self._btn_all.config(state=state)

    def _start_build(self, extra_args: list, label: str) -> None:
        if self._building:
            return
        self._set_building(True)
        self._status.set(f'Building: {label} …')
        self._write(f'\n─── {label} ───\n')
        threading.Thread(
            target=_run_build,
            args=(extra_args, self._queue),
            daemon=True,
        ).start()

    def _build_selected(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        label = self._listbox.get(sel[0])
        self._start_build(['--only', label], label)

    def _build_all(self) -> None:
        self._start_build([], 'Build All')

    # ── queue poll (50 ms tick) ───────────────────────────────────────────────

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                if item is None:        # sentinel: subprocess finished
                    self._set_building(False)
                    self._status.set('Done.')
                else:
                    self._write(item)
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = BuildUI()
    app.mainloop()


if __name__ == '__main__':
    main()
