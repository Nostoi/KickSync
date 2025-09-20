#!/usr/bin/env python3
"""
Legacy entry point for the Soccer Coach Sideline Timekeeper desktop application.

This file maintains backward compatibility with the original implementation.
For new development, use run_desktop.py or the src.ui.tkinter_app module directly.

NOTE: This file contains the original monolithic implementation for reference
and backward compatibility. The new modular structure is in the src/ directory.
"""
import sys
import os

# Add the src directory to Python path for new modular structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Try using new modular structure
    from src.ui.tkinter_app import run_tkinter_app
    
    def main():
        """Main entry point using new modular structure."""
        run_tkinter_app()
    
    if __name__ == "__main__":
        main()
        
except ImportError:
    # Fallback to original implementation if new structure not available
    print("New modular structure not available, falling back to original implementation...")
    
    # Original implementation below (preserved for backward compatibility)
    # coach_timer.py
    # A no-deps Tkinter app for live soccer time tracking & subs management.
    # Field shape: 9 players (3x ST, 2x MF, 3x DF, 1x GK). Equal-time target: 30/60 min.

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

APP_TITLE = "Sideline Timekeeper"
GAME_LENGTH_MIN = 60
EQUAL_TIME_TARGET_MIN = 30
HALFTIME_PAUSE_MIN = 10.5

POSITIONS = ["GK", "DF", "DF", "DF", "MF", "MF", "ST", "ST", "ST"]  # required on-field slots
POS_SHORT_TO_FULL = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "ST": "Striker"}

# --- Data models --- #
@dataclass
class Player:
    name: str
    number: Optional[str] = ""
    preferred: Optional[str] = ""  # comma-separated e.g. "ST,MF"
    total_seconds: int = 0
    # runtime
    on_field: bool = False
    position: Optional[str] = None
    stint_start_ts: Optional[float] = None  # epoch seconds when last put on field

    def start_stint(self, now_ts: float):
        if not self.on_field:
            self.on_field = True
            self.stint_start_ts = now_ts

    def end_stint(self, now_ts: float):
        if self.on_field and self.stint_start_ts is not None:
            self.total_seconds += int(now_ts - self.stint_start_ts)
        self.on_field = False
        self.position = None
        self.stint_start_ts = None

    def current_stint_seconds(self, now_ts: float) -> int:
        if self.on_field and self.stint_start_ts is not None:
            return int(now_ts - self.stint_start_ts)
        return 0

    def preferred_list(self) -> List[str]:
        return [p.strip().upper() for p in (self.preferred or "").split(",") if p.strip()]

@dataclass
class GameState:
    roster: Dict[str, Player] = field(default_factory=dict)  # key by name (unique)
    # game timing
    scheduled_start_ts: Optional[float] = None
    game_start_ts: Optional[float] = None
    paused: bool = True
    halftime_started: bool = False
    halftime_end_ts: Optional[float] = None
    elapsed_adjustment: int = 0  # manual adjustments if needed

    def to_json(self) -> dict:
        return {
            "players": {k: asdict(v) for k, v in self.roster.items()},
            "scheduled_start_ts": self.scheduled_start_ts,
            "game_start_ts": self.game_start_ts,
            "paused": self.paused,
            "halftime_started": self.halftime_started,
            "halftime_end_ts": self.halftime_end_ts,
            "elapsed_adjustment": self.elapsed_adjustment,
        }

    @staticmethod
    def from_json(data: dict) -> "GameState":
        gs = GameState()
        for name, pdata in data.get("players", {}).items():
            p = Player(**{k: pdata.get(k) for k in Player.__dataclass_fields__.keys()})
            gs.roster[name] = p
        gs.scheduled_start_ts = data.get("scheduled_start_ts")
        gs.game_start_ts = data.get("game_start_ts")
        gs.paused = data.get("paused", True)
        gs.halftime_started = data.get("halftime_started", False)
        gs.halftime_end_ts = data.get("halftime_end_ts")
        gs.elapsed_adjustment = int(data.get("elapsed_adjustment", 0))
        return gs

# --- Utilities --- #
def fmt_mmss(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def now_ts() -> float:
    return time.time()

# --- Tk app --- #
class SidelineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x680")
        self.state = GameState()
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
        gamem.add_command(label="Start / Resume", command=self.start_game)
        gamem.add_command(label="Pause", command=self.pause_game)
        gamem.add_command(label="Start Halftime (10.5m)", command=self.start_halftime)
        gamem.add_command(label="Force End Halftime", command=self.end_halftime)
        gamem.add_separator()
        gamem.add_command(label="Set Scheduled Start…", command=self.set_scheduled_start)
        gamem.add_command(label="Adjust Elapsed (+/- sec)…", command=self.adjust_elapsed)
        mbar.add_cascade(label="Game", menu=gamem)

        self.config(menu=mbar)

    def _build_routes(self):
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.frames: Dict[str, tk.Frame] = {}

        for FrameClass in (HomeView, LineupView, GameView):
            frame = FrameClass(self.container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

    def show_home(self):
        self._show("HomeView")

    def show_lineup(self):
        self._show("LineupView")

    def show_game(self):
        self._show("GameView")

    def _show(self, name: str):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    # ---------- Menu actions ---------- #
    def new_roster(self):
        if not self._confirm_discard():
            return
        RosterDialog(self, on_submit=self._apply_new_roster)

    def _apply_new_roster(self, players: List[Player]):
        self.state = GameState(roster={p.name: p for p in players})
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
        # Roll current stint seconds into displayed values WITHOUT ending stints:
        snapshot = self._snapshot_state_for_save()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        messagebox.showinfo(APP_TITLE, "Game saved.")

    def _snapshot_state_for_save(self) -> dict:
        # Keep live stints, but capture current live totals so a reload is faithful.
        temp = GameState.from_json(self.state.to_json())
        n = now_ts()
        for p in temp.roster.values():
            p.total_seconds += p.current_stint_seconds(n)
            # do not zero out stint_start_ts; we keep it for live tracking after load
        return temp.to_json()

    def load_game(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            title="Load Game State"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.state = GameState.from_json(data)
            self.sub_queue.clear()
            self.show_home()
            messagebox.showinfo(APP_TITLE, "Game loaded.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Failed to load: {e}")

    def start_game(self):
        if self.state.game_start_ts is None:
            self.state.game_start_ts = now_ts()
        self.state.paused = False
        # resume all on-field stints if they were paused
        n = now_ts()
        for p in self.state.roster.values():
            if p.on_field and p.stint_start_ts is None:
                p.stint_start_ts = n
        self._kick_timer()
        self.show_game()

    def pause_game(self):
        if self.state.paused:
            return
        # freeze all stints
        n = now_ts()
        for p in self.state.roster.values():
            if p.on_field and p.stint_start_ts is not None:
                p.total_seconds += int(n - p.stint_start_ts)
                p.stint_start_ts = None
        self.state.paused = True
        if self.after_timer:
            self.after_cancel(self.after_timer)
            self.after_timer = None

    def start_halftime(self):
        if not self.state.halftime_started:
            self.pause_game()
            self.state.halftime_started = True
            self.state.halftime_end_ts = now_ts() + int(HALFTIME_PAUSE_MIN * 60)
            self._kick_timer()  # to update countdown label

    def end_halftime(self):
        if self.state.halftime_started:
            self.state.halftime_started = False
            self.state.halftime_end_ts = None
            # do not auto-resume; coach resumes explicitly

    def set_scheduled_start(self):
        t = simpledialog.askstring(
            APP_TITLE,
            "Enter scheduled start time (HH:MM, 24h today):"
        )
        if not t:
            return
        try:
            hh, mm = [int(x) for x in t.strip().split(":")]
            now_local = time.localtime()
            sched = time.struct_time((
                now_local.tm_year, now_local.tm_mon, now_local.tm_mday,
                hh, mm, 0, now_local.tm_wday, now_local.tm_yday, now_local.tm_isdst
            ))
            self.state.scheduled_start_ts = time.mktime(sched)
            messagebox.showinfo(APP_TITLE, f"Scheduled start set for {time.strftime('%H:%M', sched)}.")
            self._kick_timer()
        except Exception:
            messagebox.showerror(APP_TITLE, "Invalid time. Use HH:MM (24-hour).")

    def adjust_elapsed(self):
        val = simpledialog.askinteger(APP_TITLE, "Adjust elapsed seconds (+/-):", minvalue=-3600, maxvalue=3600)
        if val is None:
            return
        self.state.elapsed_adjustment += int(val)
        messagebox.showinfo(APP_TITLE, f"Elapsed adjusted by {val} seconds.")

    def _kick_timer(self):
        if self.after_timer:
            self.after_cancel(self.after_timer)
        self.after_timer = self.after(1000, self._tick)

    def _tick(self):
        # Handle scheduled start auto-begin
        n = now_ts()
        if self.state.scheduled_start_ts and self.state.game_start_ts is None:
            if n >= self.state.scheduled_start_ts:
                self.start_game()
        # Halftime auto-resume notice (we don't force resume)
        if self.state.halftime_started and self.state.halftime_end_ts:
            if n >= self.state.halftime_end_ts:
                self.state.halftime_started = False
                self.state.halftime_end_ts = None
                messagebox.showinfo(APP_TITLE, "Halftime complete. Press Start/Resume to continue.")
        # Live stint accrual (we don’t mutate totals here; we display live)
        # Refresh GameView if visible
        gv: GameView = self.frames["GameView"]
        if gv.winfo_ismapped():
            gv.refresh_tables()
        # Continue heartbeat if not paused (or to keep countdowns updating)
        if not self.state.paused or self.state.halftime_started or self.state.scheduled_start_ts:
            self._kick_timer()
        else:
            self.after_timer = None

    # ---------- Helpers for other views ---------- #
    def _confirm_discard(self) -> bool:
        if any(self.state.roster):
            return messagebox.askyesno(APP_TITLE, "Discard current data?")
        return True

# --- Dialogs & Views --- #
class RosterDialog(tk.Toplevel):
    def __init__(self, master: SidelineApp, on_submit):
        super().__init__(master)
        self.title("Enter Roster")
        self.on_submit = on_submit
        self.geometry("760x480")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text="Enter players (one per line): Name, Number (optional), Preferred positions e.g. 'ST,MF'").pack(anchor="w", padx=10, pady=(10,4))
        self.txt = tk.Text(self, height=16, width=90)
        self.txt.pack(fill="both", expand=True, padx=10, pady=4)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=8)
        ttk.Button(btns, text="Load From File…", command=self._load_file).pack(side="left")
        ttk.Button(btns, text="Use Example 17-Player Roster", command=self._example).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", command=self._save).pack(side="right", padx=8)

    def _load_file(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.csv"), ("All", "*.*")])
        if not p: return
        with open(p, "r", encoding="utf-8") as f:
            self.txt.delete("1.0", "end")
            self.txt.insert("1.0", f.read())

    def _example(self):
        sample = []
        # 17-player example; adjust as needed
        for i in range(1, 18):
            pref = "ST" if i <= 4 else "MF" if i <= 8 else "DF" if i <= 14 else "GK"
            sample.append(f"Player {i},{i:02d},{pref}")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(sample))

    def _save(self):
        lines = [ln.strip() for ln in self.txt.get("1.0", "end").strip().splitlines() if ln.strip()]
        players: List[Player] = []
        seen = set()
        for ln in lines:
            parts = [p.strip() for p in ln.split(",")]
            if not parts:
                continue
            name = parts[0]
            if name in seen:
                messagebox.showerror(APP_TITLE, f"Duplicate name: {name}")
                return
            seen.add(name)
            number = parts[1] if len(parts) >= 2 else ""
            preferred = parts[2] if len(parts) >= 3 else ""
            players.append(Player(name=name, number=number, preferred=preferred))
        if len(players) < 9:
            messagebox.showerror(APP_TITLE, "Need at least 9 players.")
            return
        self.on_submit(players)
        self.destroy()

class HomeView(ttk.Frame):
    def __init__(self, parent, app: SidelineApp):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        title = ttk.Label(self, text=APP_TITLE, font=("TkDefaultFont", 20, "bold"))
        title.pack(pady=14)

        btns = ttk.Frame(self)
        btns.pack(pady=6)
        ttk.Button(btns, text="Enter Roster / Edit", command=self.app.new_roster).grid(row=0, column=0, padx=6, pady=6)
        ttk.Button(btns, text="Start New Game", command=self._start_new_game).grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(btns, text="Resume Saved Game", command=self.app.load_game).grid(row=0, column=2, padx=6, pady=6)

        self.summary = ttk.Treeview(self, columns=("num","pref","total"), show="headings", height=16)
        for c, w in (("num", 80), ("pref", 160), ("total", 120)):
            self.summary.heading(c, text=c.upper())
            self.summary.column(c, width=w, anchor="center")
        self.summary.pack(fill="both", expand=True, padx=12, pady=12)
        self.summary.heading("num", text="NUMBER")
        self.summary.heading("pref", text="PREFERRED")
        self.summary.heading("total", text="TOTAL (mm:ss)")

    def on_show(self):
        self._refresh()

    def _refresh(self):
        self.summary.delete(*self.summary.get_children())
        for p in sorted(self.app.state.roster.values(), key=lambda x: (x.number or "999", x.name)):
            self.summary.insert("", "end", values=(p.number, ",".join(p.preferred_list()), fmt_mmss(p.total_seconds)))

    def _start_new_game(self):
        if len(self.app.state.roster) < 9:
            messagebox.showerror(APP_TITLE, "Enter a roster (at least 9 players) before starting.")
            return
        self.app.show_lineup()

class LineupView(ttk.Frame):
    def __init__(self, parent, app: SidelineApp):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="Pick Starting Lineup (positions on the left)", font=("TkDefaultFont", 14, "bold")).pack(anchor="w", padx=10, pady=10)
        body = ttk.Frame(self); body.pack(fill="both", expand=True)

        # Left: positions
        left = ttk.Frame(body); left.pack(side="left", fill="y", padx=10)
        self.pos_list = tk.Listbox(left, height=len(POSITIONS))
        for i, p in enumerate(POSITIONS):
            self.pos_list.insert("end", f"{i+1}. {p} – {POS_SHORT_TO_FULL[p]}")
        self.pos_list.pack()
        ttk.Label(left, text="Select a position, then assign a player.").pack(pady=6)

        # Middle: roster table
        mid = ttk.Frame(body); mid.pack(side="left", fill="both", expand=True, padx=10)
        cols = ("name","num","pref")
        self.roster_tv = ttk.Treeview(mid, columns=cols, show="headings", height=16)
        for c, w in (("name", 240), ("num", 80), ("pref", 160)):
            self.roster_tv.heading(c, text=c.upper()); self.roster_tv.column(c, width=w, anchor="center")
        self.roster_tv.pack(fill="both", expand=True)
        ttk.Button(mid, text="Assign to Selected Position", command=self.assign_player).pack(pady=6)

        # Right: current assignments
        right = ttk.Frame(body); right.pack(side="left", fill="y", padx=10)
        ttk.Label(right, text="Starting Assignments").pack()
        self.assign_tv = ttk.Treeview(right, columns=("slot","player"), show="headings", height=16)
        self.assign_tv.heading("slot", text="SLOT")
        self.assign_tv.heading("player", text="PLAYER")
        self.assign_tv.column("slot", width=120, anchor="center")
        self.assign_tv.column("player", width=220, anchor="w")
        self.assign_tv.pack()

        bottom = ttk.Frame(self); bottom.pack(fill="x", pady=10)
        ttk.Button(bottom, text="Clear All", command=self.clear_all).pack(side="left", padx=8)
        ttk.Button(bottom, text="Back", command=self.app.show_home).pack(side="left", padx=8)
        ttk.Button(bottom, text="Start Game", command=self.start_game).pack(side="right", padx=8)

    def on_show(self):
        self._refresh_roster()
        self.assign_tv.delete(*self.assign_tv.get_children())

    def _refresh_roster(self):
        self.roster_tv.delete(*self.roster_tv.get_children())
        for p in sorted(self.app.state.roster.values(), key=lambda x: (x.number or "999", x.name)):
            self.roster_tv.insert("", "end", iid=p.name, values=(p.name, p.number, ",".join(p.preferred_list())))

    def assign_player(self):
        sel_pos = self.pos_list.curselection()
        if not sel_pos:
            messagebox.showerror(APP_TITLE, "Select a position.")
            return
        sel_player = self.roster_tv.selection()
        if not sel_player:
            messagebox.showerror(APP_TITLE, "Select a player.")
            return
        p = self.app.state.roster[sel_player[0]]
        slot_idx = sel_pos[0]
        pos = POSITIONS[slot_idx]

        # prevent duplicates
        for iid in self.assign_tv.get_children():
            slot, player = self.assign_tv.item(iid, "values")
            if player == p.name:
                messagebox.showerror(APP_TITLE, f"{p.name} already assigned.")
                return
            if slot.startswith(f"{slot_idx+1}."):
                self.assign_tv.delete(iid)

        self.assign_tv.insert("", "end", values=(f"{slot_idx+1}. {pos}", p.name))

    def clear_all(self):
        self.assign_tv.delete(*self.assign_tv.get_children())

    def start_game(self):
        # apply assignments
        assigned = {}
        for iid in self.assign_tv.get_children():
            slot, player = self.assign_tv.item(iid, "values")
            pos = slot.split(".")[1].strip().split()[0]
            assigned[pos] = assigned.get(pos, []) + [player]

        # validate exact counts
        required_counts = {"GK":1, "DF":3, "MF":2, "ST":3}
        got = {k: len(assigned.get(k, [])) for k in required_counts.keys()}
        if got != required_counts:
            messagebox.showerror(APP_TITLE, f"Need exact counts {required_counts}, got {got}.")
            return

        # reset all players
        for p in self.app.state.roster.values():
            p.on_field = False
            p.position = None
            p.stint_start_ts = None

        n = now_ts()
        # mark on-field
        for pos, names in assigned.items():
            for nm in names:
                pl = self.app.state.roster[nm]
                pl.position = pos
                pl.start_stint(n)

        self.app.state.game_start_ts = self.app.state.game_start_ts or n
        self.app.state.paused = False
        self.app._kick_timer()
        self.app.show_game()

class GameView(ttk.Frame):
    def __init__(self, parent, app: SidelineApp):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        top = ttk.Frame(self); top.pack(fill="x", padx=10, pady=8)
        self.lbl_clock = ttk.Label(top, text="00:00 / 60:00", font=("TkDefaultFont", 14, "bold"))
        self.lbl_clock.pack(side="left")
        ttk.Button(top, text="Start/Resume", command=self.app.start_game).pack(side="left", padx=6)
        ttk.Button(top, text="Pause", command=self.app.pause_game).pack(side="left", padx=6)
        ttk.Button(top, text="Halftime (10.5m)", command=self.app.start_halftime).pack(side="left", padx=6)
        ttk.Button(top, text="Commit Subs", command=self.commit_subs).pack(side="right", padx=6)
        ttk.Button(top, text="Queue Clear", command=self.clear_queue).pack(side="right", padx=6)
        ttk.Button(top, text="Save", command=self.app.save_game).pack(side="right", padx=6)

        body = ttk.Frame(self); body.pack(fill="both", expand=True, padx=10, pady=6)

        # Left: on-field table
        left = ttk.Frame(body); left.pack(side="left", fill="both", expand=True, padx=6)
        ttk.Label(left, text="On Field").pack(anchor="w")
        cols = ("pos","name","num","stint","total","pref")
        self.on_tv = ttk.Treeview(left, columns=cols, show="headings", height=18)
        for c, w in (("pos", 70), ("name", 200), ("num", 60), ("stint", 90), ("total", 90), ("pref", 120)):
            self.on_tv.heading(c, text=c.upper()); self.on_tv.column(c, width=w, anchor="center")
        self.on_tv.pack(fill="both", expand=True)
        self.on_tv.bind("<<TreeviewSelect>>", self._on_select_on)

        # Right: substitution & roster
        right = ttk.Frame(body); right.pack(side="left", fill="both", expand=True, padx=6)
        ttk.Label(right, text="Roster / Choose Replacement").pack(anchor="w")
        rcols = ("name","num","status","pos","stint","total","pref")
        self.roster_tv = ttk.Treeview(right, columns=rcols, show="headings", height=12)
        for c, w in (("name", 180), ("num", 60), ("status", 80), ("pos", 70), ("stint", 90), ("total", 90), ("pref", 120)):
            self.roster_tv.heading(c, text=c.upper()); self.roster_tv.column(c, width=w, anchor="center")
        self.roster_tv.pack(fill="both", expand=True)
        self.roster_tv.bind("<<TreeviewSelect>>", self._on_select_replacement)

        qframe = ttk.Frame(right); qframe.pack(fill="x", pady=6)
        ttk.Label(qframe, text="Queued Subs (Out → In)").pack(anchor="w")
        self.queue_lb = tk.Listbox(qframe, height=6)
        self.queue_lb.pack(fill="x", expand=False)
        btns = ttk.Frame(qframe); btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="Queue Selected", command=self.queue_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove Selected", command=self.remove_selected_queue).pack(side="left", padx=4)

        # Legend
        legend = ttk.Frame(self); legend.pack(fill="x", padx=10, pady=6)
        ttk.Label(legend, text="Legend: status = IN/OUT; colors on TOTAL indicate under/over 30-min target").pack(anchor="w")

        # style tags via tag_configure? ttk.Treeview lacks per-row colors natively; we’ll mark with emoji arrows
        # (portable, no ttk style hacking on the sideline)

        # selections
        self.selected_out: Optional[str] = None
        self.selected_in: Optional[str] = None

    def on_show(self):
        self.refresh_tables()

    def _elapsed_seconds(self) -> int:
        if self.app.state.game_start_ts is None:
            return 0
        base = int(now_ts() - self.app.state.game_start_ts)
        return max(0, base + self.app.state.elapsed_adjustment)

    def refresh_tables(self):
        # clock label
        if self.app.state.halftime_started and self.app.state.halftime_end_ts:
            remaining = int(self.app.state.halftime_end_ts - now_ts())
            remaining = max(0, remaining)
            self.lbl_clock.config(text=f"HALFTIME {fmt_mmss(remaining)}")
        elif self.app.state.scheduled_start_ts and self.app.state.game_start_ts is None:
            delta = int(self.app.state.scheduled_start_ts - now_ts())
            if delta > 0:
                self.lbl_clock.config(text=f"Starts in {fmt_mmss(delta)}")
            else:
                self.lbl_clock.config(text="Starting…")
        else:
            elapsed = self._elapsed_seconds()
            self.lbl_clock.config(text=f"{fmt_mmss(elapsed)} / {fmt_mmss(GAME_LENGTH_MIN*60)}" + (" [PAUSED]" if self.app.state.paused else ""))

        # on-field view
        self.on_tv.delete(*self.on_tv.get_children())
        n = now_ts()
        on_field_players = [p for p in self.app.state.roster.values() if p.on_field]
        # sort by formation order
        pos_order = {"GK":0, "DF":1, "MF":2, "ST":3}
        on_field_players.sort(key=lambda p: (pos_order.get(p.position or "ZZ", 9), p.number or "999", p.name))
        for p in on_field_players:
            stint = p.current_stint_seconds(n)
            total_live = p.total_seconds + stint
            fairness = self._fairness_marker(total_live)
            self.on_tv.insert("", "end", iid=f"on:{p.name}",
                              values=(p.position, p.name, p.number, fmt_mmss(stint), f"{fmt_mmss(total_live)} {fairness}",
                                      ",".join(p.preferred_list())))

        # roster view
        self.roster_tv.delete(*self.roster_tv.get_children())
        for p in sorted(self.app.state.roster.values(), key=lambda x: (not x.on_field, x.number or "999", x.name)):
            stint = p.current_stint_seconds(n)
            total_live = p.total_seconds + stint
            status = "IN" if p.on_field else "OUT"
            self.roster_tv.insert("", "end", iid=p.name,
                                  values=(p.name, p.number, status, p.position or "-", fmt_mmss(stint), f"{fmt_mmss(total_live)} {self._fairness_marker(total_live)}",
                                          ",".join(p.preferred_list())))

    def _fairness_marker(self, total_sec: int) -> str:
        delta = total_sec - EQUAL_TIME_TARGET_MIN*60
        if delta < -180:  # >3 min under
            return "⬇"
        if delta > 180:   # >3 min over
            return "⬆"
        return "•"

    # --- Sub queue logic --- #
    def _on_select_on(self, _evt=None):
        sel = self.on_tv.selection()
        if sel:
            iid = sel[0]
            _, name = iid.split(":", 1)
            self.selected_out = name

    def _on_select_replacement(self, _evt=None):
        sel = self.roster_tv.selection()
        if sel:
            self.selected_in = sel[0]

    def queue_selected(self):
        if not self.selected_out:
            messagebox.showerror(APP_TITLE, "Select someone on the field to sub OUT.")
            return
        if not self.selected_in:
            messagebox.showerror(APP_TITLE, "Select a roster player to sub IN or swap.")
            return
        if self.selected_out == self.selected_in:
            # position swap request with same player? no-op
            messagebox.showerror(APP_TITLE, "Choose a different player for replacement, or do nothing.")
            return
        self.app.sub_queue.append((self.selected_out, self.selected_in))
        self.queue_lb.insert("end", f"{self.selected_out} → {self.selected_in}")

    def remove_selected_queue(self):
        idxs = list(self.queue_lb.curselection())
        if not idxs:
            return
        idxs.sort(reverse=True)
        for i in idxs:
            self.queue_lb.delete(i)
            del self.app.sub_queue[i]

    def clear_queue(self):
        self.app.sub_queue.clear()
        self.queue_lb.delete(0, "end")

    def commit_subs(self):
        if not self.app.sub_queue:
            messagebox.showinfo(APP_TITLE, "No subs queued.")
            return
        n = now_ts()
        # Apply all queued subs atomically: OUT players leave; IN players take OUT player’s position
        # If IN is currently on the field, this is a position swap.
        for out_name, in_name in self.app.sub_queue:
            if out_name not in self.app.state.roster or in_name not in self.app.state.roster:
                continue
            p_out = self.app.state.roster[out_name]
            p_in = self.app.state.roster[in_name]

            out_pos = p_out.position
            if not p_out.on_field or not out_pos:
                continue  # invalid (already off)

            # End OUT stint
            p_out.end_stint(n)

            if p_in.on_field:
                # swap positions between two on-field players
                prev_in_pos = p_in.position
                p_in.position = out_pos
                # Put OUT back in with IN's prior position? No—coach asked for replacing that slot.
                # If you want symmetric swap, uncomment next two lines:
                # p_out.position = prev_in_pos
                # p_out.start_stint(n)
            else:
                # off-field to on-field replacement
                p_in.position = out_pos
                p_in.start_stint(n)

        self.clear_queue()
        self.refresh_tables()

# --- App entrypoint --- #
def main():
    app = SidelineApp()
    app.mainloop()

if __name__ == "__main__":
    main()
