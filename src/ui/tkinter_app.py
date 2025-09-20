"""
Tkinter application module for the Soccer Coach Sideline Timekeeper.

This module contains the main Tkinter GUI application with all views and functionality.
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, List, Tuple, Optional

from ..models import Player, GameState
from ..services import PersistenceService, TimerService
from ..utils import (
    fmt_mmss, now_ts, APP_TITLE, POSITIONS, POS_SHORT_TO_FULL,
    EQUAL_TIME_TARGET_MIN, GAME_LENGTH_MIN
)


class SidelineApp(tk.Tk):
    """Main application window for the Sideline Timekeeper."""
    
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x680")
        self.state = GameState()
        self.timer_service = TimerService(self.state)
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
        self._show_frame("HomeView")

    def show_lineup(self):
        self._show_frame("LineupView")

    def show_game(self):
        self._show_frame("GameView")

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

    def adjust_elapsed(self):
        result = simpledialog.askinteger(APP_TITLE, "Adjust elapsed time by seconds (+/-):")
        if result is not None:
            self.timer_service.add_time_adjustment(result)
            self.refresh_tables()

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
        
        # Quick controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(pady=10)
        
        ttk.Button(controls_frame, text="Lineup", command=self.controller.show_lineup).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Game View", command=self.controller.show_game).pack(side="left", padx=5)
        
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
        if self.controller.state.game_start_ts:
            elapsed = self.controller.timer_service.get_game_elapsed_seconds()
            remaining = self.controller.timer_service.get_remaining_seconds()
            status = f"Game Time: {fmt_mmss(elapsed)} / Remaining: {fmt_mmss(remaining)}"
            if self.controller.state.paused:
                status += " (PAUSED)"
        else:
            status = "Game not started"
            
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
        
        # Control buttons
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Start", command=self.controller.start_game).pack(side="left", padx=2)
        ttk.Button(controls_frame, text="Pause", command=self.controller.pause_game).pack(side="left", padx=2)
        ttk.Button(controls_frame, text="Halftime", command=self.controller.start_halftime).pack(side="left", padx=2)
        
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
        if self.controller.state.game_start_ts:
            elapsed = self.controller.timer_service.get_game_elapsed_seconds()
            self.timer_label.config(text=fmt_mmss(elapsed))
        else:
            self.timer_label.config(text="00:00")
        
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
            
            if player.on_field:
                self.field_tree.insert("", "end", text=f"{player.name} #{player.number}", 
                                     values=(player.position or "", fmt_mmss(total_time)))
            else:
                # Color code based on fairness
                fairness_color = ""
                target_seconds = EQUAL_TIME_TARGET_MIN * 60
                if total_time >= target_seconds:
                    fairness_color = "green"
                elif total_time < (target_seconds * 0.8):
                    fairness_color = "red"
                else:
                    fairness_color = "orange"
                
                item = self.bench_tree.insert("", "end", text=f"{player.name} #{player.number}", 
                                            values=(fmt_mmss(total_time),))
                # Note: Tkinter treeview color tagging would be implemented here in full version


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