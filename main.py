import flet as ft
import sqlite3
from datetime import datetime
import os

# --- Database Manager ---
class DatabaseManager:
    def __init__(self, db_name="gym_data.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                routine TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER,
                weight REAL,
                reps INTEGER,
                sets INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises (id)
            )
        ''')
        self.conn.commit()

    def add_exercise(self, name, routine):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO exercises (name, routine) VALUES (?, ?)", (name, routine))
        self.conn.commit()
        return cursor.lastrowid

    def get_exercises(self, routine):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM exercises WHERE routine = ?", (routine,))
        return cursor.fetchall()

    def remove_exercise(self, exercise_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
        cursor.execute("DELETE FROM logs WHERE exercise_id = ?", (exercise_id,))
        self.conn.commit()

    def log_set(self, exercise_id, weight, reps, sets=1):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO logs (exercise_id, weight, reps, sets) VALUES (?, ?, ?, ?)", (exercise_id, weight, reps, sets))
        self.conn.commit()

    def get_history(self, exercise_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT weight, reps, sets, timestamp FROM logs WHERE exercise_id = ? ORDER BY timestamp DESC LIMIT 20", (exercise_id,))
        return cursor.fetchall()

# --- Exercise Card Component ---
class ExerciseCard(ft.Container):
    def __init__(self, exercise_id, name, db, onDelete, show_snackbar_fn):
        super().__init__()
        self.exercise_id = exercise_id
        self.exercise_name = name
        self.db = db
        self.onDelete = onDelete
        self.show_snackbar = show_snackbar_fn
        
        # Container styling
        self.padding = 15
        self.border_radius = 15
        self.bgcolor = ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.animate = ft.Animation(300, ft.AnimationCurve.EASE_OUT)

        # Styled Input fields
        self.txt_weight = ft.TextField(
            label="Weight", 
            width=100, 
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=14,
            dense=True,
            content_padding=10
        )
        self.txt_reps = ft.TextField(
            label="Reps", 
            width=70, 
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=14,
            dense=True,
             content_padding=10
        )
        self.txt_sets = ft.TextField(
            label="Sets",
            width=70,
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            text_size=14,
            dense=True,
             content_padding=10
        )
        
        self.btn_save = ft.ElevatedButton(
            "Log", 
            icon=ft.Icons.SAVE, 
            on_click=self.save_set,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=10
            )
        )

        # History View
        self.history_list = ft.Column(spacing=5) 

        self.details_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Divider(),
                    ft.Text("Log Set", size=14, weight="bold", color=ft.Colors.BLUE_200),
                    ft.Row([self.txt_weight, self.txt_reps, self.txt_sets, self.btn_save], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Text("History", size=14, weight="bold", color=ft.Colors.GREY_400),
                    self.history_list
                ],
                spacing=10
            ),
            visible=False,
            padding=ft.padding.only(top=10)
        )

        # Set content of the Container
        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FITNESS_CENTER, color=ft.Colors.PRIMARY),
                ft.Text(self.exercise_name, size=16, weight="bold", expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE, 
                    icon_color=ft.Colors.ERROR, 
                    tooltip="Remove",
                    on_click=self.delete_exercise
                ),
                ft.IconButton(
                    icon=ft.Icons.EXPAND_MORE, 
                    on_click=self.toggle_details,
                    tooltip="Details"
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.details_container
        ])

    def toggle_details(self, e):
        self.details_container.visible = not self.details_container.visible
        e.control.icon = ft.Icons.EXPAND_LESS if self.details_container.visible else ft.Icons.EXPAND_MORE
        if self.details_container.visible:
            self.load_history()
        self.update()

    def load_history(self):
        history = self.db.get_history(self.exercise_id)
        self.history_list.controls.clear()
        if not history:
             self.history_list.controls.append(ft.Text("No logs yet.", color=ft.Colors.GREY_500, size=12))
        else:
            for w, r, s, t in history:
                try:
                    dt = datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%b %d')
                except:
                    date_str = t 
                
                self.history_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{date_str}", size=12, color=ft.Colors.GREY_400, width=60),
                            ft.Text(f"{w}kg", size=13, weight="bold"),
                            ft.Text(f"x {r}", size=13),
                            ft.Text(f"({s} sets)", size=12, color=ft.Colors.GREY_400)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=5,
                        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_800))
                    )
                )
        self.update()

    def save_set(self, e):
        if not self.txt_weight.value or not self.txt_reps.value:
            return
            
        try:
            w = float(self.txt_weight.value)
            r = int(self.txt_reps.value)
            s = int(self.txt_sets.value) if self.txt_sets.value else 1
            
            self.db.log_set(self.exercise_id, w, r, s)
            
            self.load_history()
            self.show_snackbar(f"Logged: {w}kg x {r}")
        except ValueError:
            self.show_snackbar("Invalid numbers", is_error=True)

    def delete_exercise(self, e):
        print(f"Delete clicked for ID: {self.exercise_id}") # Console log
        try:
            self.onDelete(self.exercise_id)
        except Exception as ex:
            print(f"Error in delete_exercise: {ex}")
            try:
                self.show_snackbar(f"Error: {ex}", is_error=True)
            except:
                pass


# --- Main Application ---
def main(page: ft.Page):
    page.title = "Gym Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0 
    page.bgcolor = ft.Colors.BLACK
    
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.INDIGO,
        visual_density=ft.VisualDensity.ADAPTIVE_PLATFORM_DENSITY,
    )

    db = DatabaseManager()

    # --- Utilities ---
    def show_snackbar(msg, is_error=False):
        page.show_snack_bar(ft.SnackBar(
            content=ft.Text(str(msg)),
            bgcolor=ft.Colors.ERROR if is_error else ft.Colors.BLUE_600
        ))

    # --- Custom Dialog Overlay ---
    def show_custom_dialog(title, content_control, on_confirm, confirm_text="Save"):
        overlay = None # forward declaration

        def close(e=None):
            page.overlay.remove(overlay)
            page.update()
        
        def on_ok(e):
            on_confirm(e)
            close()

        card = ft.Container(
            content=ft.Column([
                ft.Text(title, size=20, weight="bold"),
                ft.Divider(),
                content_control,
                ft.Container(height=20),
                ft.Row([
                    ft.TextButton("Cancel", on_click=close),
                    ft.ElevatedButton(confirm_text, on_click=on_ok)
                ], alignment=ft.MainAxisAlignment.END)
            ], tight=True, width=300),
            padding=20,
            bgcolor=ft.Colors.SURFACE,
            border_radius=10,
            on_click=lambda e: None # prevent click through
        )

        overlay = ft.Container(
            content=card,
            alignment=ft.Alignment(0, 0),
            bgcolor="#B3000000", # 0.7 opacity black
            on_click=close, # Click outside to close
            padding=20,
        )
        
        page.overlay.append(overlay)
        page.update()

    # --- App Logic ---
    content_area = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=15)
    
    routines = ["Push", "Pull", "Legs"]
    routine_colors = [ft.Colors.BLUE_400, ft.Colors.RED_400, ft.Colors.GREEN_400]

    def refresh_exercises(routine):
        content_area.controls.clear()
        exercises = db.get_exercises(routine)
        
        if not exercises:
             content_area.controls.append(
                 ft.Container(
                     content=ft.Column([
                         ft.Icon(ft.Icons.FITNESS_CENTER_OUTLINED, size=50, color=ft.Colors.GREY_700),
                         ft.Text(f"No {routine} exercises", color=ft.Colors.GREY_600)
                     ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                     alignment=ft.Alignment(0, 0),
                     padding=40,
                     expand=True
                 )
             )
        else:
            for eid, name, _ in exercises:
                content_area.controls.append(
                    ExerciseCard(eid, name, db, lambda eid: confirm_delete_handler(eid), show_snackbar)
                )
        content_area.update()

    def confirm_delete_handler(eid):
        print(f"DEBUG: confirm_delete_handler called for {eid}")
        def do_delete(e):
            print(f"DEBUG: do_delete execution for {eid}")
            db.remove_exercise(eid)
            refresh_exercises(routines[page.navigation_bar.selected_index])
            print("DEBUG: Exercise removed and view refreshed")
            
        show_custom_dialog(
            "Confirm Delete",
            ft.Text("Are you sure you want to delete this exercise?"),
            do_delete,
            "Delete"
        )
        print("DEBUG: Delete dialog shown")

    def add_exercise_dialog(e):
        routine = routines[page.navigation_bar.selected_index]
        txt_name = ft.TextField(label="Exercise Name") # No autofocus to be safe
        
        def do_save(e):
            if txt_name.value:
                db.add_exercise(txt_name.value, routine)
                refresh_exercises(routine)
            else:
                show_snackbar("Name required", True)

        show_custom_dialog(
            f"Add {routine} Exercise",
            txt_name,
            do_save,
            "Add"
        )

    # FAB
    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=ft.Colors.BLUE_400,
        on_click=add_exercise_dialog
    )

    def on_nav_change(e):
        idx = e.control.selected_index
        routine = routines[idx]
        fab.bgcolor = routine_colors[idx]
        refresh_exercises(routine)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER, label="Push"),
            ft.NavigationBarDestination(icon=ft.Icons.ROWING, label="Pull"),
            ft.NavigationBarDestination(icon=ft.Icons.DIRECTIONS_WALK, label="Legs"),
        ]
    )

    page.add(
        ft.Container(
            content=ft.Stack([
                ft.Container(content_area, padding=ft.Padding(15, 15, 15, 80)),
                ft.Container(fab, alignment=ft.Alignment(1, 1), padding=20)
            ]),
            expand=True
        )
    )

    refresh_exercises("Push")

ft.app(target=main)
