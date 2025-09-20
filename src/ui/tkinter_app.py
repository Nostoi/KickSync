"""
Tkinter application module for the Soccer Coach Sideline Timekeeper.

This module contains the main Tkinter GUI application with all views and functionality.
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, List, Tuple, Optional

from ..models import GameState, Player
from ..services import AnalyticsService, PersistenceService, TimerService
from ..utils import (
    fmt_mmss,
    now_ts,
    APP_TITLE,
    POSITIONS,
    POS_SHORT_TO_FULL,
    GAME_LENGTH_MIN,
    MIN_GAME_LENGTH_MIN,
    MAX_GAME_LENGTH_MIN,
    MIN_PERIOD_COUNT,
    MAX_PERIOD_COUNT,
    PERIOD_LABELS,
)


def fmt_signed_mmss(seconds: int) -> str:
    """Format seconds as signed MM:SS string."""

    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{fmt_mmss(abs(seconds))}"


def ordinal(n: int) -> str:
    """Return an ordinal string (1st, 2nd, …)."""

    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def describe_period(number: int, total: int) -> str:
    """Return a human-friendly period label based on total periods."""

    base = PERIOD_LABELS.get(total, "Period")
    if total <= 1:
        return base
    return f"{ordinal(number)} {base}"


class SidelineApp(tk.Tk):
    """Main application window for the Sideline Timekeeper."""
    
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x680")
        self.state = GameState()
        self.timer_service = TimerService(self.state)
        self.analytics_service = AnalyticsService(self.state, self.timer_service)
        self.sub_queue: List[Tuple[str, str]] = []  # (out_name, in_name) queued
        self.after_timer = None

        self._build_menu()
        self._build_routes()
        self.show_home()

    # ---------- UI Scaffolding ---------- #
    def _build_menu(self):
        mbar = tk.Menu(self)
        filem = tk.Menu(mbar, tearoff=0)
        filem.add_command(label="New Roster…", command=self.new_roster)
        filem.add_command(label="Save Game…", command=self.save_game)
        filem.add_command(label="Load Game…", command=self.load_game)
        filem.add_separator()
        filem.add_command(label="Quit", command=self.destroy)
        mbar.add_cascade(label="File", menu=filem)

        gamem = tk.Menu(mbar, tearoff=0)
        gamem.add_command(label="Configure Timer…", command=self.configure_timer)
        gamem.add_separator()
        gamem.add_command(label="Start / Resume", command=self.start_game)
        gamem.add_command(label="Pause", command=self.pause_game)
        gamem.add_command(label="Start Halftime (10.5m)", command=self.start_halftime)
        gamem.add_command(label="Force End Halftime", command=self.end_halftime)
        gamem.add_separator()
        gamem.add_command(label="Set Scheduled Start…", command=self.set_scheduled_start)
        gamem.add_command(label="Manual Time Tools…", command=self.open_time_tools)
        mbar.add_cascade(label="Game", menu=gamem)

        reportsm = tk.Menu(mbar, tearoff=0)
        reportsm.add_command(
            label="Playing Time Report", command=self.show_reports
        )
        mbar.add_cascade(label="Reports", menu=reportsm)

        self.config(menu=mbar)

    def _build_routes(self):
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.frames: Dict[str, tk.Frame] = {}

        for FrameClass in (HomeView, LineupView, GameView, ReportsView):
            frame = FrameClass(self.container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

    def show_home(self):
        self._show_frame("HomeView")

    def show_lineup(self):
        self._show_frame("LineupView")

    def show_game(self):
        self._show_frame("GameView")

    def show_reports(self):
        self._show_frame("ReportsView")

    def _show_frame(self, frame_name: str):
        frame = self.frames[frame_name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    # ---------- File Operations ---------- #
    def new_roster(self):
        dialog = RosterDialog(self)
        if dialog.result:
            self._apply_new_roster(dialog.result)

    def _apply_new_roster(self, players: List[Player]):
        self.state = GameState(roster={p.name: p for p in players})
        self.timer_service = TimerService(self.state)
        self.analytics_service = AnalyticsService(self.state, self.timer_service)
        self.sub_queue.clear()
        self.show_home()

    def save_game(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Save Game State"
        )
        if not path:
            return
        
        try:
            PersistenceService.save_game_to_file(self.state, path)
            messagebox.showinfo(APP_TITLE, "Game saved.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Failed to save: {e}")

    def load_game(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            title="Load Game State"
        )
        if not path:
            return
        
        try:
            self.state = PersistenceService.load_game_from_file(path)
            self.timer_service = TimerService(self.state)
            self.analytics_service = AnalyticsService(self.state, self.timer_service)
            self.sub_queue.clear()
            self.show_home()
            messagebox.showinfo(APP_TITLE, "Game loaded.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Failed to load: {e}")

    # ---------- Game Control ---------- #
    def start_game(self):
        self.timer_service.start_game()
        self.refresh_tables()

    def pause_game(self):
        self.timer_service.pause_game()
        self.refresh_tables()

    def start_halftime(self):
        self.timer_service.start_halftime()
        self.refresh_tables()

    def end_halftime(self):
        self.timer_service.end_halftime()
        self.refresh_tables()

    def set_scheduled_start(self):
        # Simple implementation - could be enhanced with date/time picker
        result = simpledialog.askstring(APP_TITLE, "Enter scheduled start time (Unix timestamp):")
        if result:
            try:
                self.state.scheduled_start_ts = float(result)
                self.refresh_tables()
            except ValueError:
                messagebox.showerror(APP_TITLE, "Invalid timestamp format")

    def configure_timer(self):
        config = self.timer_service.get_timer_configuration()
        dialog = TimerConfigDialog(self, config)
        if dialog.result:
            try:
                self.timer_service.configure_game(
                    game_length_minutes=dialog.result["minutes"],
                    period_count=dialog.result["periods"],
                )
                messagebox.showinfo(APP_TITLE, "Timer configuration updated.")
            except ValueError as exc:
                messagebox.showerror(APP_TITLE, str(exc))
        self.refresh_tables()

    def open_time_tools(self):
        dialog = TimeAdjustmentDialog(self, self.timer_service)
        result = dialog.result
        if not result:
            return

        try:
            if result["mode"] == "adjustment":
                self.timer_service.add_time_adjustment(
                    result["seconds"],
                    period_index=result["period_index"],
                    apply_to_all=result["apply_to_all"],
                )
            else:
                self.timer_service.add_stoppage_time(
                    result["seconds"], period_index=result["period_index"]
                )
            self.refresh_tables()
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    # ---------- Substitution Management ---------- #
    def queue_sub(self, out_name: str, in_name: str):
        # Remove any existing entries for these players
        self.sub_queue = [(o, i) for o, i in self.sub_queue if o != out_name and i != in_name]
        # Add new entry
        self.sub_queue.append((out_name, in_name))
        self.refresh_tables()

    def clear_queue(self):
        self.sub_queue.clear()
        self.refresh_tables()

    def execute_subs(self):
        if not self.sub_queue:
            return

        current_time = now_ts()
        for out_name, in_name in self.sub_queue:
            p_out = self.state.roster.get(out_name)
            p_in = self.state.roster.get(in_name)
            
            if not p_out or not p_in:
                continue
                
            if not p_out.on_field:
                continue  # Can't sub someone who's not on field

            # Remember the position
            out_pos = p_out.position

            # End OUT stint
            p_out.end_stint(current_time)

            if p_in.on_field:
                # Swap positions between two on-field players
                p_in.position = out_pos
            else:
                # Off-field to on-field replacement
                p_in.position = out_pos
                p_in.start_stint(current_time)

        self.clear_queue()
        self.refresh_tables()

    # ---------- UI Updates ---------- #
    def refresh_tables(self):
        """Refresh all tables in all views."""
        for frame in self.frames.values():
            if hasattr(frame, "refresh"):
                frame.refresh()

    def start_auto_refresh(self):
        """Start automatic refresh timer."""
        if self.after_timer:
            self.after_cancel(self.after_timer)
        self.after_timer = self.after(1000, self._auto_refresh_tick)  # 1 second

    def _auto_refresh_tick(self):
        """Auto-refresh callback."""
        self.refresh_tables()
        self.start_auto_refresh()  # Schedule next refresh


class RosterDialog(tk.Toplevel):
    """Dialog for creating/editing team roster."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.result: Optional[List[Player]] = None
        self.title("Team Roster")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        
    def _build_ui(self):
        # Simple implementation - could be enhanced with proper table editing
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Instructions
        ttk.Label(main_frame, text="Enter player information (one per line: Name,Number,Preferred_Positions)").pack(anchor="w")
        
        # Text area for player input
        self.text_area = tk.Text(main_frame, height=15)
        self.text_area.pack(fill="both", expand=True, pady=5)
        
        # Example text
        example = "Alice Smith,1,GK\nBob Jones,2,DF,MF\nCharlie Brown,3,ST"
        self.text_area.insert("1.0", example)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Cancel", command=self._cancel).pack(side="right", padx=5)
        ttk.Button(button_frame, text="OK", command=self._ok).pack(side="right")
        
    def _ok(self):
        try:
            text = self.text_area.get("1.0", "end-1c")
            players = []
            
            for line in text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                    
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 1:
                    continue
                    
                name = parts[0]
                number = parts[1] if len(parts) > 1 else ""
                preferred = ",".join(parts[2:]) if len(parts) > 2 else ""
                
                players.append(Player(name=name, number=number, preferred=preferred))
            
            if not players:
                messagebox.showerror("Error", "No valid players entered")
                return
                
            self.result = players
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse roster: {e}")

    def _cancel(self):
        self.destroy()


class TimerConfigDialog(simpledialog.Dialog):
    """Dialog for configuring regulation length and period count."""

    def __init__(self, parent: tk.Tk, config: Dict[str, object]):
        self.config = config
        minutes = int(config.get("game_length_minutes", GAME_LENGTH_MIN))
        periods = int(config.get("period_count", 2))
        self.minutes_var = tk.IntVar(value=max(MIN_GAME_LENGTH_MIN, minutes))
        self.periods_var = tk.IntVar(value=max(MIN_PERIOD_COUNT, periods))
        self.result: Optional[Dict[str, int]] = None
        super().__init__(parent, title="Configure Game Timer")

    def body(self, master):  # type: ignore[override]
        frame = ttk.Frame(master)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Regulation length (minutes):").grid(row=0, column=0, sticky="w")
        minutes_spin = ttk.Spinbox(
            frame,
            from_=MIN_GAME_LENGTH_MIN,
            to=MAX_GAME_LENGTH_MIN,
            textvariable=self.minutes_var,
            width=6,
            increment=5,
        )
        minutes_spin.grid(row=0, column=1, sticky="w")

        ttk.Label(frame, text="Number of periods:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        periods_spin = ttk.Spinbox(
            frame,
            from_=MIN_PERIOD_COUNT,
            to=MAX_PERIOD_COUNT,
            textvariable=self.periods_var,
            width=6,
        )
        periods_spin.grid(row=1, column=1, sticky="w", pady=(6, 0))

        self.summary_label = ttk.Label(frame, text="", padding=(0, 6, 0, 0))
        self.summary_label.grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(
            frame,
            text=(
                f"Allowed: {MIN_GAME_LENGTH_MIN}-{MAX_GAME_LENGTH_MIN} minutes, "
                f"{MIN_PERIOD_COUNT}-{MAX_PERIOD_COUNT} periods"
            ),
            foreground="gray",
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        frame.columnconfigure(1, weight=1)

        self.minutes_var.trace_add("write", lambda *_: self._update_preview())
        self.periods_var.trace_add("write", lambda *_: self._update_preview())
        self._update_preview()
        return frame

    def validate(self) -> bool:
        minutes = self.minutes_var.get()
        periods = self.periods_var.get()

        if not (MIN_GAME_LENGTH_MIN <= minutes <= MAX_GAME_LENGTH_MIN):
            messagebox.showerror(
                APP_TITLE,
                f"Minutes must be between {MIN_GAME_LENGTH_MIN} and {MAX_GAME_LENGTH_MIN}.",
            )
            return False

        if not (MIN_PERIOD_COUNT <= periods <= MAX_PERIOD_COUNT):
            messagebox.showerror(
                APP_TITLE,
                f"Periods must be between {MIN_PERIOD_COUNT} and {MAX_PERIOD_COUNT}.",
            )
            return False

        if minutes * 60 < periods * 60:
            messagebox.showerror(APP_TITLE, "Provide at least one minute per period.")
            return False

        self.result = {"minutes": minutes, "periods": periods}
        return True

    def apply(self) -> None:  # type: ignore[override]
        # Result already stored during validation
        pass

    def _update_preview(self) -> None:
        minutes = max(MIN_GAME_LENGTH_MIN, int(self.minutes_var.get() or MIN_GAME_LENGTH_MIN))
        periods = max(MIN_PERIOD_COUNT, int(self.periods_var.get() or MIN_PERIOD_COUNT))
        total_seconds = minutes * 60
        base, remainder = divmod(total_seconds, periods)
        lengths = [base + (1 if i < remainder else 0) for i in range(periods)]
        label = PERIOD_LABELS.get(periods, "Period")
        plural = label if periods == 1 else f"{label}s"
        segments = ", ".join(fmt_mmss(value) for value in lengths)
        self.summary_label.config(
            text=(
                f"Regulation total {fmt_mmss(total_seconds)} — {periods} {plural}: {segments}"
            )
        )


class TimeAdjustmentDialog(simpledialog.Dialog):
    """Dialog for manual adjustments and stoppage tracking."""

    MODE_LABELS = {
        "adjustment": "Manual Adjustment (+/-)",
        "stoppage": "Stoppage / Injury Time",
    }

    def __init__(self, parent: tk.Tk, timer_service: TimerService):
        self.timer_service = timer_service
        self.config = timer_service.get_timer_configuration()
        self.period_summaries = timer_service.get_period_summaries()
        current_period, _ = timer_service.get_half_info()
        self.mode_choice_var = tk.StringVar(value=self.MODE_LABELS["adjustment"])
        self.seconds_var = tk.StringVar(value="0")
        self.period_var = tk.StringVar()
        self.apply_all_var = tk.BooleanVar(value=False)
        self.result: Optional[Dict[str, object]] = None

        period_labels = [
            describe_period(summary["number"], self.config["period_count"])
            for summary in self.period_summaries
        ]
        if period_labels:
            default_idx = min(current_period - 1, len(period_labels) - 1)
            self.period_var.set(period_labels[default_idx])
        self._period_label_map = dict(zip(period_labels, [s["index"] for s in self.period_summaries]))

        super().__init__(parent, title="Manual Time Tools")

    def body(self, master):  # type: ignore[override]
        frame = ttk.Frame(master)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Current periods:").grid(row=0, column=0, columnspan=2, sticky="w")

        tree = ttk.Treeview(
            frame,
            columns=("Reg", "Elapsed", "Adj", "Stop"),
            show="headings",
            height=max(3, len(self.period_summaries)),
        )
        tree.heading("Reg", text="Reg")
        tree.heading("Elapsed", text="Elapsed")
        tree.heading("Adj", text="Adjust")
        tree.heading("Stop", text="Stoppage")
        tree.column("Reg", width=90, anchor="center")
        tree.column("Elapsed", width=90, anchor="center")
        tree.column("Adj", width=90, anchor="center")
        tree.column("Stop", width=90, anchor="center")
        tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 8))

        lengths = self.config.get("period_lengths", [])
        current_index = self.timer_service.game_state.current_period_index
        for summary in self.period_summaries:
            idx = summary["index"]
            values = (
                fmt_mmss(lengths[idx]) if idx < len(lengths) else fmt_mmss(0),
                fmt_mmss(summary["elapsed_seconds"]),
                fmt_signed_mmss(summary["adjustment_seconds"]),
                fmt_mmss(summary["stoppage_seconds"]),
            )
            tags = ("active",) if idx == current_index else ()
            tree.insert("", "end", values=values, tags=tags)
        tree.tag_configure("active", font=("Arial", 9, "bold"))

        ttk.Label(
            frame,
            text=(
                f"Total stoppage: {fmt_mmss(self.config['total_stoppage_seconds'])}    "
                f"Total adjustments: {fmt_signed_mmss(self.config['total_adjustment_seconds'])}"
            ),
            foreground="gray",
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(frame, text="Action:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.mode_combo = ttk.Combobox(
            frame,
            state="readonly",
            values=list(self.MODE_LABELS.values()),
            textvariable=self.mode_choice_var,
        )
        self.mode_combo.grid(row=3, column=1, sticky="we", pady=(8, 0))

        ttk.Label(frame, text="Seconds:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.seconds_entry = ttk.Entry(frame, textvariable=self.seconds_var)
        self.seconds_entry.grid(row=4, column=1, sticky="we", pady=(6, 0))

        ttk.Label(frame, text="Period:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.period_combo = ttk.Combobox(
            frame,
            state="readonly",
            values=list(self._period_label_map.keys()),
            textvariable=self.period_var,
        )
        self.period_combo.grid(row=5, column=1, sticky="we", pady=(6, 0))

        self.apply_all_check = ttk.Checkbutton(
            frame,
            text="Apply to all periods",
            variable=self.apply_all_var,
        )
        self.apply_all_check.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.hint_label = ttk.Label(frame, text="", foreground="gray")
        self.hint_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

        self.mode_combo.bind("<<ComboboxSelected>>", lambda *_: self._on_mode_change())
        self._on_mode_change()
        return frame

    def validate(self) -> bool:
        mode = self._selected_mode()
        try:
            seconds = int(self.seconds_var.get())
        except (TypeError, ValueError):
            messagebox.showerror(APP_TITLE, "Enter time in whole seconds.")
            return False

        if mode == "adjustment" and seconds == 0:
            messagebox.showerror(APP_TITLE, "Adjustment must be a non-zero value.")
            return False

        if mode == "stoppage" and seconds <= 0:
            messagebox.showerror(APP_TITLE, "Stoppage time must be positive seconds.")
            return False

        period_label = self.period_var.get()
        if period_label not in self._period_label_map:
            messagebox.showerror(APP_TITLE, "Select a period to update.")
            return False

        period_index = self._period_label_map[period_label]
        self.result = {
            "mode": mode,
            "seconds": seconds,
            "period_index": period_index,
            "apply_to_all": bool(self.apply_all_var.get()) if mode == "adjustment" else False,
        }
        return True

    def apply(self) -> None:  # type: ignore[override]
        # Result stored during validation
        pass

    def _selected_mode(self) -> str:
        for key, value in self.MODE_LABELS.items():
            if value == self.mode_choice_var.get():
                return key
        return "adjustment"

    def _on_mode_change(self) -> None:
        mode = self._selected_mode()
        if mode == "stoppage":
            self.apply_all_var.set(False)
            self.apply_all_check.state(["disabled"])
            self.hint_label.config(text="Stoppage time adds extra playable seconds (positive only).")
        else:
            self.apply_all_check.state(["!disabled"])
            self.hint_label.config(text="Adjustments can be positive or negative (affects elapsed clock).")

class HomeView(ttk.Frame):
    """Home/overview page showing game status and player summary."""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Sideline Timekeeper", font=("Arial", 18, "bold")).pack(pady=10)
        
        # Game status frame
        status_frame = ttk.LabelFrame(self, text="Game Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="Game not started")
        self.status_label.pack()
        self.detail_label = ttk.Label(status_frame, text="", foreground="gray")
        self.detail_label.pack()
        
        # Quick controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(pady=10)

        ttk.Button(controls_frame, text="Lineup", command=self.controller.show_lineup).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Game View", command=self.controller.show_game).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Reports", command=self.controller.show_reports).pack(side="left", padx=5)
        
        # Player summary
        summary_frame = ttk.LabelFrame(self, text="Player Summary", padding=10)
        summary_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for player summary
        self.tree = ttk.Treeview(summary_frame, columns=("Number", "Status", "Time"), show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("Number", text="Number")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Time", text="Playing Time")
        
        self.tree.column("#0", width=150)
        self.tree.column("Number", width=60)
        self.tree.column("Status", width=100)
        self.tree.column("Time", width=100)
        
        self.tree.pack(fill="both", expand=True)

    def on_show(self):
        self.refresh()
        self.controller.start_auto_refresh()

    def refresh(self):
        # Update status
        config = self.controller.timer_service.get_timer_configuration()
        target_seconds = config["game_length_seconds"] + config["total_stoppage_seconds"]

        if self.controller.state.game_start_ts:
            elapsed = self.controller.timer_service.get_game_elapsed_seconds()
            remaining = self.controller.timer_service.get_remaining_seconds()
            status = f"Elapsed {fmt_mmss(elapsed)} / Target {fmt_mmss(target_seconds)} (Remaining {fmt_mmss(remaining)})"
            if self.controller.state.paused:
                status += " (PAUSED)"
            period_number, in_break = self.controller.timer_service.get_half_info()
            period_text = describe_period(period_number, config["period_count"])
            detail = [f"{period_text} ({period_number}/{config['period_count']})"]
            if in_break:
                detail.append("Break in progress")
            detail.append(f"Stoppage {fmt_mmss(config['total_stoppage_seconds'])}")
            detail.append(f"Adjust {fmt_signed_mmss(config['total_adjustment_seconds'])}")
            self.detail_label.config(text=" • ".join(detail))
        else:
            status = "Game not started"
            lengths = config.get("period_lengths", [])
            if not lengths:
                lengths = [config["game_length_seconds"]]
            plural_label = PERIOD_LABELS.get(config["period_count"], "Period")
            plural = plural_label if config["period_count"] == 1 else f"{plural_label}s"
            periods_summary = ", ".join(fmt_mmss(value) for value in lengths)
            self.detail_label.config(
                text=f"Configured: {config['period_count']} {plural} ({periods_summary})"
            )

        self.status_label.config(text=status)
        
        # Update player summary
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        current_time = now_ts()
        for player in self.controller.state.roster.values():
            total_time = player.total_seconds + player.current_stint_seconds(current_time)
            status = "ON FIELD" if player.on_field else "BENCH"
            if player.on_field and player.position:
                status += f" ({player.position})"
                
            self.tree.insert("", "end", text=player.name, values=(
                player.number,
                status,
                fmt_mmss(total_time)
            ))


class LineupView(ttk.Frame):
    """View for managing field positions and substitutions."""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Field Lineup", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Back button
        ttk.Button(self, text="← Back to Home", command=self.controller.show_home).pack(anchor="w", padx=10)
        
        # Main content area
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Field positions (left side)
        field_frame = ttk.LabelFrame(content_frame, text="Field Positions", padding=10)
        field_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.position_vars = {}
        for i, position in enumerate(POSITIONS):
            frame = ttk.Frame(field_frame)
            frame.pack(fill="x", pady=2)
            
            ttk.Label(frame, text=f"{position}:", width=4).pack(side="left")
            
            var = tk.StringVar()
            self.position_vars[position + str(i)] = var
            combo = ttk.Combobox(frame, textvariable=var, state="readonly")
            combo.pack(side="left", fill="x", expand=True, padx=5)
        
        # Bench (right side)
        bench_frame = ttk.LabelFrame(content_frame, text="Bench", padding=10)
        bench_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        self.bench_listbox = tk.Listbox(bench_frame)
        self.bench_listbox.pack(fill="both", expand=True)

    def on_show(self):
        self.refresh()

    def refresh(self):
        # Update position dropdowns
        all_players = list(self.controller.state.roster.keys())
        
        for key, var in self.position_vars.items():
            var.set("")  # Clear current selection
            # Set available players for this combo
            # This is simplified - in full implementation, would populate combobox values
        
        # Update bench listbox
        self.bench_listbox.delete(0, tk.END)
        for player in self.controller.state.roster.values():
            if not player.on_field:
                self.bench_listbox.insert(tk.END, f"{player.name} #{player.number}")


class GameView(ttk.Frame):
    """Main game view with live timing and substitution management."""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        # Header with game controls
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(header_frame, text="← Back to Home", command=self.controller.show_home).pack(side="left")

        # Game timer display
        self.timer_label = ttk.Label(header_frame, text="00:00", font=("Arial", 20, "bold"))
        self.timer_label.pack(side="right")
        self.period_label = ttk.Label(header_frame, text="Not Started", font=("Arial", 12))
        self.period_label.pack(side="right", padx=(0, 12))

        # Control buttons
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(controls_frame, text="Start", command=self.controller.start_game).pack(side="left", padx=2)
        ttk.Button(controls_frame, text="Pause", command=self.controller.pause_game).pack(side="left", padx=2)
        ttk.Button(controls_frame, text="Halftime", command=self.controller.start_halftime).pack(side="left", padx=2)

        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.clock_meta_label = ttk.Label(status_frame, text="", foreground="gray")
        self.clock_meta_label.pack(side="left")

        period_frame = ttk.LabelFrame(self, text="Period Summary", padding=5)
        period_frame.pack(fill="x", padx=10, pady=5)
        self.period_tree = ttk.Treeview(
            period_frame,
            columns=("Period", "Reg", "Elapsed", "Adj", "Stop", "Remain"),
            show="headings",
            height=4,
        )
        headings = [
            ("Period", 140),
            ("Reg", 80),
            ("Elapsed", 80),
            ("Adj", 80),
            ("Stop", 80),
            ("Remain", 90),
        ]
        for name, width in headings:
            self.period_tree.heading(name, text=name)
            self.period_tree.column(name, width=width, anchor="center")
        self.period_tree.pack(fill="x", expand=False)
        self.period_tree.tag_configure("active", font=("Arial", 9, "bold"))

        # Substitution queue
        sub_frame = ttk.LabelFrame(self, text="Substitution Queue", padding=10)
        sub_frame.pack(fill="x", padx=10, pady=5)

        self.sub_label = ttk.Label(sub_frame, text="No substitutions queued")
        self.sub_label.pack(side="left")
        
        ttk.Button(sub_frame, text="Execute Subs", command=self.controller.execute_subs).pack(side="right", padx=5)
        ttk.Button(sub_frame, text="Clear Queue", command=self.controller.clear_queue).pack(side="right")
        
        # Player tables
        tables_frame = ttk.Frame(self)
        tables_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # On field table
        field_frame = ttk.LabelFrame(tables_frame, text="On Field", padding=5)
        field_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        self.field_tree = ttk.Treeview(field_frame, columns=("Pos", "Time"), show="tree headings", height=10)
        self.field_tree.heading("#0", text="Player")
        self.field_tree.heading("Pos", text="Position")
        self.field_tree.heading("Time", text="Time")
        self.field_tree.pack(fill="both", expand=True)
        
        # Bench table
        bench_frame = ttk.LabelFrame(tables_frame, text="Bench", padding=5)
        bench_frame.pack(side="right", fill="both", expand=True, padx=2)
        
        self.bench_tree = ttk.Treeview(bench_frame, columns=("Total",), show="tree headings", height=10)
        self.bench_tree.heading("#0", text="Player")
        self.bench_tree.heading("Total", text="Total Time")
        self.bench_tree.pack(fill="both", expand=True)

    def on_show(self):
        self.refresh()
        self.controller.start_auto_refresh()

    def refresh(self):
        # Update timer display
        config = self.controller.timer_service.get_timer_configuration()
        report = self.controller.analytics_service.generate_game_report()
        summary_lookup = {summary.name: summary for summary in report.players}
        if self.controller.state.game_start_ts:
            elapsed = self.controller.timer_service.get_game_elapsed_seconds()
            self.timer_label.config(text=fmt_mmss(elapsed))
        else:
            self.timer_label.config(text="00:00")

        target_seconds = config["game_length_seconds"] + config["total_stoppage_seconds"]
        remaining_seconds = self.controller.timer_service.get_remaining_seconds()
        meta_parts = [
            f"Target {fmt_mmss(target_seconds)}",
            f"Remaining {fmt_mmss(remaining_seconds)}",
            f"Stoppage {fmt_mmss(config['total_stoppage_seconds'])}",
            f"Adjust {fmt_signed_mmss(config['total_adjustment_seconds'])}",
        ]
        self.clock_meta_label.config(text=" • ".join(meta_parts))

        period_number, in_break = self.controller.timer_service.get_half_info()
        period_text = f"{describe_period(period_number, config['period_count'])} ({period_number}/{config['period_count']})"
        if in_break:
            period_text += " – Break"
        self.period_label.config(text=period_text)

        summaries = self.controller.timer_service.get_period_summaries()
        self.period_tree.delete(*self.period_tree.get_children())
        if summaries:
            self.period_tree.configure(height=max(3, len(summaries)))
        current_index = self.controller.timer_service.game_state.current_period_index
        for summary in summaries:
            target = (
                summary["length_seconds"]
                + summary["adjustment_seconds"]
                + summary["stoppage_seconds"]
            )
            remain = max(0, target - summary["elapsed_seconds"])
            values = (
                describe_period(summary["number"], config["period_count"]),
                fmt_mmss(summary["length_seconds"]),
                fmt_mmss(summary["elapsed_seconds"]),
                fmt_signed_mmss(summary["adjustment_seconds"]),
                fmt_mmss(summary["stoppage_seconds"]),
                fmt_mmss(remain),
            )
            tags = ("active",) if summary["index"] == current_index and not in_break else ()
            self.period_tree.insert("", "end", values=values, tags=tags)

        # Update substitution queue display
        if self.controller.sub_queue:
            subs_text = ", ".join([f"{out} → {in_}" for out, in_ in self.controller.sub_queue])
            self.sub_label.config(text=f"Queued: {subs_text}")
        else:
            self.sub_label.config(text="No substitutions queued")
        
        # Update player tables
        current_time = now_ts()
        
        # Clear existing items
        for item in self.field_tree.get_children():
            self.field_tree.delete(item)
        for item in self.bench_tree.get_children():
            self.bench_tree.delete(item)
        
        # Populate tables
        for player in self.controller.state.roster.values():
            total_time = player.total_seconds + player.current_stint_seconds(current_time)
            summary_data = summary_lookup.get(player.name)

            if player.on_field:
                self.field_tree.insert("", "end", text=f"{player.name} #{player.number}",
                                     values=(player.position or "", fmt_mmss(total_time)))
            else:
                # Color code based on fairness
                fairness_color = ""
                if summary_data:
                    if summary_data.fairness == "over":
                        fairness_color = "red"
                    elif summary_data.fairness == "under":
                        fairness_color = "orange"
                    else:
                        fairness_color = "green"

                item = self.bench_tree.insert("", "end", text=f"{player.name} #{player.number}",
                                            values=(fmt_mmss(total_time),))
                # Note: Tkinter treeview color tagging would be implemented here in full version


class ReportsView(ttk.Frame):
    """Analytics view showing playing time distribution."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=5)
        ttk.Button(header, text="← Back to Home", command=self.controller.show_home).pack(side="left")
        ttk.Label(header, text="Playing Time Analytics", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        ttk.Button(header, text="Go to Game", command=self.controller.show_game).pack(side="right")

        summary_frame = ttk.LabelFrame(self, text="Summary", padding=10)
        summary_frame.pack(fill="x", padx=10, pady=5)
        self.summary_label = ttk.Label(summary_frame, text="No roster loaded.")
        self.summary_label.pack(anchor="w")
        self.detail_label = ttk.Label(summary_frame, text="", foreground="gray")
        self.detail_label.pack(anchor="w")
        self.distribution_label = ttk.Label(summary_frame, text="", foreground="gray")
        self.distribution_label.pack(anchor="w")

        tree_frame = ttk.LabelFrame(self, text="Player Breakdown", padding=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("Number", "Preferred", "Status", "Played", "Target", "Delta", "Share")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.column("#0", width=180, anchor="w")
        col_specs = {
            "Number": (70, "center"),
            "Preferred": (120, "center"),
            "Status": (150, "center"),
            "Played": (110, "center"),
            "Target": (110, "center"),
            "Delta": (90, "center"),
            "Share": (80, "center"),
        }
        for column in columns:
            self.tree.heading(column, text=column)
            width, anchor = col_specs[column]
            self.tree.column(column, width=width, anchor=anchor)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("under", foreground="#ffb020")
        self.tree.tag_configure("over", foreground="#ff6b6b")
        self.tree.tag_configure("ok", foreground="#24c88b")

        self.hint_label = ttk.Label(
            self,
            text="Delta compares live totals against an equal share of regulation + stoppage + adjustments.",
            foreground="gray",
        )
        self.hint_label.pack(fill="x", padx=12, pady=(0, 10))

    def on_show(self):
        self.refresh()
        self.controller.start_auto_refresh()

    def refresh(self):
        report = self.controller.analytics_service.generate_game_report()
        if report.roster_size == 0:
            self.summary_label.config(text="Add players to see analytics.")
            self.detail_label.config(text="")
            self.distribution_label.config(text="")
            self.tree.delete(*self.tree.get_children())
            return

        summary_text = (
            f"Elapsed {fmt_mmss(report.elapsed_seconds)} of "
            f"{fmt_mmss(report.target_seconds_total)} target — {report.roster_size} players"
        )
        self.summary_label.config(text=summary_text)

        details = [
            f"Regulation {fmt_mmss(report.regulation_seconds)}",
            f"Stoppage {fmt_mmss(report.stoppage_seconds)}",
            f"Adjust {fmt_signed_mmss(report.adjustment_seconds)}",
            f"Per Player {fmt_mmss(report.target_seconds_per_player)}",
        ]
        self.detail_label.config(text=" • ".join(details))

        distribution = [
            f"Average {fmt_mmss(int(round(report.average_seconds)))}",
            f"Median {fmt_mmss(int(round(report.median_seconds)))}",
            f"Range {fmt_mmss(report.min_seconds)}–{fmt_mmss(report.max_seconds)}",
        ]
        self.distribution_label.config(text=" • ".join(distribution))

        self.tree.delete(*self.tree.get_children())
        for summary in report.players:
            status = "On Field" if summary.on_field else "Bench"
            if summary.on_field and summary.position:
                status += f" ({summary.position})"
            preferred = ", ".join(summary.preferred_positions) or "—"
            share = f"{summary.target_share * 100:.1f}%"
            self.tree.insert(
                "",
                "end",
                text=summary.name,
                values=(
                    summary.number or "",
                    preferred,
                    status,
                    fmt_mmss(summary.cumulative_seconds),
                    fmt_mmss(summary.target_seconds),
                    fmt_signed_mmss(summary.delta_seconds),
                    share,
                ),
                tags=(summary.fairness,),
            )


def create_tkinter_app() -> SidelineApp:
    """
    Create and return the main Tkinter application.
    
    Returns:
        Configured SidelineApp instance
    """
    return SidelineApp()


def run_tkinter_app() -> None:
    """Run the Tkinter application."""
    app = create_tkinter_app()
    app.mainloop()


if __name__ == "__main__":
    run_tkinter_app()