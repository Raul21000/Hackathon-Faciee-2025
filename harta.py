import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os
import sys

# --- IMPORT GAMES AS MODULES ---
try:
    import electronica
except ImportError:
    print("Warning: electronica.py not found.")
    electronica = None

try:
    import calculatoare_joc
except ImportError:
    print("Warning: calculatoare_joc.py not found.")
    calculatoare_joc = None

try:
    import automatica
except ImportError:
    print("Warning: automatica.py not found.")
    automatica = None


class JourneyApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("RPi Journey App")
        self.configure(bg="black")

        # --- WINDOW SETUP ---
        window_width = 800
        window_height = 480

        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x_c = int((screen_width / 2) - (window_width / 2))
        y_c = int((screen_height / 2) - (window_height / 2))

        self.geometry(f"{window_width}x{window_height}+{x_c}+{y_c}")
        self.overrideredirect(True)

        self.bind("<Escape>", lambda event: self.destroy())

        # --- PATH FINDING ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.possible_paths = [script_dir, os.path.join(script_dir, "images")]

        self.main_menu_image_name = "harta.jpg"
        self.journey_image_names = [
            "Corp y.jpg",
            "Corp_g.jpg",
            "Corp_J.jpg",
        ]

        self.game_map = {
            "Corp y.jpg": electronica,
            "Corp_g.jpg": calculatoare_joc,
            "Corp_J.jpg": automatica
        }

        self.current_index = 0
        self.images_cache = {}
        self.button_images = {}  # To keep references to transparent button images

        # --- UI Setup ---
        self.canvas = tk.Canvas(self, width=800, height=480, highlightthickness=0, bg="#111111")
        self.canvas.pack(fill="both", expand=True)

        # LOAD IMAGES WITH ZOOM
        self.load_images()
        self.show_main_menu()

    def find_file(self, filename):
        for path in self.possible_paths:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                return full_path
        return None

    def load_images(self):
        all_names = [self.main_menu_image_name] + self.journey_image_names

        # --- ZOOM SETTINGS ---
        zoom_factor = 1.15

        target_w = 800
        target_h = 480

        scaled_w = int(target_w * zoom_factor)
        scaled_h = int(target_h * zoom_factor)

        for name in all_names:
            found_path = self.find_file(name)

            if found_path:
                try:
                    img = Image.open(found_path)
                    img = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                    img = img.crop((0, 0, target_w, target_h))

                    self.images_cache[name] = ImageTk.PhotoImage(img)
                    print(f"Loaded & Cropped: {name}")
                except Exception as e:
                    print(f"Error loading {name}: {e}")
                    self.images_cache[name] = None
            else:
                print(f"MISSING FILE: {name}")
                self.images_cache[name] = None

    def create_transparent_button(self, x, y, width, height, text, color, command, alpha=180):
        """
        Creates a custom button using a semi-transparent image on the canvas.
        alpha: 0 (invisible) to 255 (opaque). 180 is a good "glass" look.
        """

        # 1. Create a PIL Image with Alpha Channel (RGBA)
        # Parse hex color (e.g., #39FF14) to RGB tuple
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

        # Create rectangle image
        img = Image.new('RGBA', (width, height), (*rgb, alpha))

        # Add a border to the image (optional, makes it pop)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255, 200), width=2)

        # Convert to PhotoImage
        tk_img = ImageTk.PhotoImage(img)

        # Store reference so it doesn't get garbage collected
        btn_id_str = f"btn_{x}_{y}_{text}"
        self.button_images[btn_id_str] = tk_img

        # 2. Draw Image on Canvas
        img_item = self.canvas.create_image(x, y, image=tk_img, anchor="center", tags="ui_controls")

        # 3. Draw Text on top
        text_item = self.canvas.create_text(x, y, text=text, font=("Courier", 18, "bold"), fill="white",
                                            tags="ui_controls")

        # 4. Bind Click Events to both Image and Text
        def on_click(event):
            # Visual feedback (optional: shrink slightly or change alpha)
            command()

        self.canvas.tag_bind(img_item, "<Button-1>", on_click)
        self.canvas.tag_bind(text_item, "<Button-1>", on_click)

        return img_item, text_item

    def draw_neon_border(self):
        self.canvas.delete("neon_border")
        w, h = 800, 480

        colors = ["#4B0082", "#9D00FF", "#FF00FF", "#FFFFFF"]
        widths = [24, 14, 8, 2]

        for i in range(4):
            self.canvas.create_rectangle(
                2, 2, w - 2, h - 2,
                outline=colors[i],
                width=widths[i],
                tags="neon_border"
            )

    def set_background(self, image_name):
        self.canvas.delete("bg")
        self.canvas.delete("error_text")

        img = self.images_cache.get(image_name)

        if img:
            self.canvas.create_image(0, 0, image=img, anchor="nw", tags="bg")
        else:
            self.canvas.create_rectangle(0, 0, 800, 480, fill="#220022", tags="bg")
            self.canvas.create_text(400, 240, text=f"MISSING:\n{image_name}",
                                    fill="red", font=("Arial", 30), tags="error_text")

        self.canvas.tag_lower("bg")
        self.draw_neon_border()

    def show_main_menu(self):
        self.set_background(self.main_menu_image_name)
        self.canvas.delete("ui_controls")
        self.button_images.clear()  # Clear old button references

        # Start Button (Green Glass)
        self.create_transparent_button(
            x=400, y=400,
            width=280, height=60,
            text="START JOURNEY",
            color="#39FF14",
            command=self.start_journey,
            alpha=120  # Semi-transparent
        )

    def start_journey(self):
        self.current_index = 0
        self.update_journey_view()

    def update_journey_view(self):
        current_image = self.journey_image_names[self.current_index]
        self.set_background(current_image)
        self.canvas.delete("ui_controls")
        self.button_images.clear()

        # Navigation Buttons (Cyan Glass)
        # Prev Button
        self.create_transparent_button(
            x=60, y=240,
            width=80, height=80,
            text="<",
            color="#00FFFF",
            command=self.prev_image,
            alpha=100
        )

        # Next Button
        self.create_transparent_button(
            x=740, y=240,
            width=80, height=80,
            text=">",
            color="#00FFFF",
            command=self.next_image,
            alpha=100
        )

        # Select Button (Magenta Glass)
        self.create_transparent_button(
            x=400, y=400,
            width=280, height=60,
            text="ENTER BUILDING",
            color="#FF00FF",
            command=self.select_building_action,
            alpha=140
        )

    def select_building_action(self):
        current_building = self.journey_image_names[self.current_index]
        if current_building in self.game_map:
            game_module = self.game_map[current_building]
            if game_module:
                self.destroy()
                if hasattr(game_module, 'main'):
                    game_module.main()
                elif hasattr(game_module, 'run_game'):
                    game_module.run_game()
            else:
                print("Game module not loaded.")
        else:
            print("No game assigned.")

    def next_image(self):
        self.current_index = (self.current_index + 1) % len(self.journey_image_names)
        self.update_journey_view()

    def prev_image(self):
        self.current_index = (self.current_index - 1) % len(self.journey_image_names)
        self.update_journey_view()


if __name__ == "__main__":
    app = JourneyApp()
    app.mainloop()