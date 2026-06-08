"""Tkinter manager for the F1 Season Calculator.

Three buttons:
  1. Load race        → runs `f1 fetch-race --season S --round N`
  2. Build data       → runs `f1 process-data` then `f1 compute-stats` for season S
  3. Run website      → boots/stops uvicorn and opens it in the default browser

The output log streams subprocess stdout/stderr in real time. All commands are
invoked as `python -m app.cli <command>` so the script works without the `f1`
entry point being on PATH — only requirement is `pip install -e .` from the
project root.

Launch from project root:  python tools/manage_ui.py
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import scrolledtext, ttk

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8000


def _resolve_default_season() -> int:
    """Read the highest seasons/{year}.json so the UI default matches the app."""
    seasons_dir = PROJECT_ROOT / "data" / "seasons"
    if not seasons_dir.exists():
        return 2026
    years = []
    for f in seasons_dir.iterdir():
        if f.suffix == ".json":
            try:
                years.append(int(f.stem))
            except ValueError:
                continue
    return max(years) if years else 2026


class ManagerUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.season = _resolve_default_season()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.busy = False               # blocks Load Race / Build Data while one is running
        self.web_proc: subprocess.Popen | None = None

        root.title(f"F1 Season Calculator · Manager (season {self.season})")
        root.geometry("720x520")
        root.minsize(600, 400)

        self._build_layout()
        self._poll_log()

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- layout ----------------------------------------------------------

    def _build_layout(self) -> None:
        pad = {"padx": 12, "pady": 8}

        header = ttk.Label(
            self.root,
            text=f"Season {self.season}",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(anchor="w", **pad)

        # --- Row 1: Load race ---
        load_frame = ttk.LabelFrame(self.root, text="Load race")
        load_frame.pack(fill="x", padx=12, pady=4)

        ttk.Label(load_frame, text="Round number:").pack(side="left", padx=(8, 4), pady=8)
        self.round_var = tk.StringVar()
        self.round_entry = ttk.Entry(load_frame, textvariable=self.round_var, width=6)
        self.round_entry.pack(side="left", padx=4, pady=8)

        self.load_btn = ttk.Button(load_frame, text="Fetch from Jolpica", command=self._on_load)
        self.load_btn.pack(side="left", padx=8, pady=8)

        # --- Row 2: Build data ---
        build_frame = ttk.LabelFrame(self.root, text="Build data")
        build_frame.pack(fill="x", padx=12, pady=4)

        ttk.Label(
            build_frame,
            text="Regenerate every championship + constructor combination + recompute stats.",
        ).pack(side="left", padx=8, pady=8)

        self.build_btn = ttk.Button(build_frame, text="Build", command=self._on_build)
        self.build_btn.pack(side="right", padx=8, pady=8)

        # --- Row 3: Run website ---
        web_frame = ttk.LabelFrame(self.root, text="Run website")
        web_frame.pack(fill="x", padx=12, pady=4)

        ttk.Label(web_frame, text=f"http://{HOST}:{PORT}/").pack(side="left", padx=8, pady=8)

        self.web_btn = ttk.Button(web_frame, text="Start", command=self._on_toggle_web)
        self.web_btn.pack(side="right", padx=8, pady=8)

        # --- Log ---
        log_frame = ttk.LabelFrame(self.root, text="Output")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.log = scrolledtext.ScrolledText(
            log_frame, wrap="word", font=("Consolas", 9), state="disabled"
        )
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

    # ---- button handlers -------------------------------------------------

    def _on_load(self) -> None:
        if self.busy:
            self._log("Another command is already running — please wait.")
            return
        round_str = self.round_var.get().strip()
        if not round_str.isdigit():
            self._log(f"Round must be a number, got: {round_str!r}")
            return
        self._run_command(
            ["fetch-race", "--season", str(self.season), "--round", round_str],
            label=f"Load race (round {round_str})",
        )

    def _on_build(self) -> None:
        if self.busy:
            self._log("Another command is already running — please wait.")
            return
        self._run_command(
            ["process-data", "--season", str(self.season)],
            label="Build data: process-data",
            on_done=lambda code: self._after_process_data(code),
        )

    def _after_process_data(self, code: int) -> None:
        if code != 0:
            self._log(f"process-data failed (exit {code}) — skipping the rest of the build.")
            return
        # Chain compute-stats → process-constructors → compute-constructor-stats.
        # Each step waits for the previous to exit 0 before launching the next,
        # so the UI stays interactive and a failure short-circuits the chain.
        self._run_command(
            ["compute-stats", "--season", str(self.season)],
            label="Build data: compute-stats",
            on_done=lambda c: self._after_compute_stats(c),
        )

    def _after_compute_stats(self, code: int) -> None:
        if code != 0:
            self._log(f"compute-stats failed (exit {code}) — skipping WCC build.")
            return
        self._run_command(
            ["process-constructors", "--season", str(self.season)],
            label="Build data: process-constructors",
            on_done=lambda c: self._after_process_constructors(c),
        )

    def _after_process_constructors(self, code: int) -> None:
        if code != 0:
            self._log(
                f"process-constructors failed (exit {code}) — "
                "skipping compute-constructor-stats."
            )
            return
        self._run_command(
            ["compute-constructor-stats", "--season", str(self.season)],
            label="Build data: compute-constructor-stats",
            on_done=lambda c: self._after_compute_constructor_stats(c),
        )

    def _after_compute_constructor_stats(self, code: int) -> None:
        if code != 0:
            self._log(
                f"compute-constructor-stats failed (exit {code}) — skipping refresh-bio."
            )
            return
        self._run_command(
            ["refresh-bio", "--season", str(self.season)],
            label="Build data: refresh-bio",
        )

    def _on_toggle_web(self) -> None:
        if self.web_proc is None:
            self._start_web()
        else:
            self._stop_web()

    # ---- subprocess plumbing --------------------------------------------

    def _run_command(
        self,
        cli_args: list[str],
        *,
        label: str,
        on_done=None,
    ) -> None:
        self._set_busy(True)
        self._log(f"$ python -m app.cli {' '.join(cli_args)}")

        cmd = [sys.executable, "-m", "app.cli", *cli_args]

        def worker() -> None:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as e:
                self.log_queue.put(f"[ERR] could not launch: {e}")
                self._set_busy(False)
                return

            assert proc.stdout is not None
            for line in proc.stdout:
                self.log_queue.put(line.rstrip())
            proc.wait()
            self.log_queue.put(f"[{label}] exit {proc.returncode}")
            self._set_busy(False)
            if on_done is not None:
                # Hand the exit code back on the Tk thread.
                self.root.after(0, lambda c=proc.returncode: on_done(c))

        threading.Thread(target=worker, daemon=True).start()

    def _start_web(self) -> None:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ]
        self._log(f"$ {' '.join(cmd)}")
        try:
            self.web_proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as e:
            self._log(f"[ERR] could not launch uvicorn: {e}")
            self.web_proc = None
            return

        threading.Thread(target=self._pump_web_output, daemon=True).start()
        self.web_btn.configure(text="Stop")

        # Open the browser shortly after — uvicorn needs a moment to bind.
        self.root.after(1500, lambda: webbrowser.open(f"http://{HOST}:{PORT}/"))

    def _pump_web_output(self) -> None:
        proc = self.web_proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            self.log_queue.put(line.rstrip())
        proc.wait()
        self.log_queue.put(f"[uvicorn] exit {proc.returncode}")
        # If the server died on its own, reset the button.
        self.root.after(0, self._reset_web_button)

    def _stop_web(self) -> None:
        proc = self.web_proc
        if proc is None:
            return
        self._log("Stopping uvicorn…")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
        finally:
            self._reset_web_button()

    def _reset_web_button(self) -> None:
        self.web_proc = None
        self.web_btn.configure(text="Start")

    # ---- log + state -----------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        # Tk methods are only safe on the main thread; hop there.
        def apply() -> None:
            self.busy = busy
            state = "disabled" if busy else "normal"
            self.load_btn.configure(state=state)
            self.build_btn.configure(state=state)

        self.root.after(0, apply)

    def _log(self, line: str) -> None:
        self.log_queue.put(line)

    def _poll_log(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", line + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(80, self._poll_log)

    # ---- shutdown --------------------------------------------------------

    def _on_close(self) -> None:
        if self.web_proc is not None:
            try:
                self.web_proc.terminate()
                self.web_proc.wait(timeout=2)
            except (subprocess.TimeoutExpired, OSError):
                self.web_proc.kill()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ManagerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
