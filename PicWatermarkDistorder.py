import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import math
import yaml
import numpy as np

class WatermarkDistorder:
    def __init__(self, root):
        self.root = root
        self.root.title("Watermark Distortion")
        self.root.geometry("1500x950")

        # --- IMAGE STATE ---
        self.background_image = None
        self.raw_watermark = None  
        self.distorted_wm = None   
        self.final_comp = None     
        self.tk_preview = None

        # --- PARAMETERS ---
        self.vars = {
            "wm_text": tk.StringVar(value="CONFIDENTIAL"),
            "wm_x": tk.IntVar(value=50),
            "wm_y": tk.IntVar(value=50),
            "wm_scale": tk.DoubleVar(value=1.0),
            "wm_rotation": tk.IntVar(value=0),
            "c_origin_x": tk.DoubleVar(value=0.5),
            "c_origin_y": tk.DoubleVar(value=0.5),
            "c_cycles": tk.DoubleVar(value=1.0),
            "alpha_min": tk.IntVar(value=100),
            "alpha_max": tk.IntVar(value=255),
            "a_origin_x": tk.DoubleVar(value=0.2),
            "a_origin_y": tk.DoubleVar(value=0.8),
            "a_cycles": tk.DoubleVar(value=1.0),
            "wave_amp": tk.DoubleVar(value=10.0),
            "wave_freq": tk.DoubleVar(value=2.0)
        }
        
        self.color_min = (0, 255, 255) 
        self.color_max = (255, 0, 255) 

        self.setup_ui()
        self.generate_text() 

    def setup_ui(self):
        self.sidebar_canvas = tk.Canvas(self.root, width=500, relief="ridge", bd=2)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar = tk.Frame(self.sidebar_canvas, padx=15, pady=10)
        
        self.sidebar.bind("<Configure>", lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar, anchor="nw", width=480)
        self.sidebar_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.sidebar_canvas.pack(side="left", fill="y")
        self.scrollbar.pack(side="left", fill="y")

        # --- SECTION 0: CONFIGURATION ---
        self.add_header("⚙ CONFIGURATION")
        cfg_frame = tk.Frame(self.sidebar)
        cfg_frame.pack(fill="x", pady=5)
        tk.Button(cfg_frame, text="Save YAML", command=self.save_config).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(cfg_frame, text="Load YAML", command=self.load_config).pack(side="left", expand=True, fill="x", padx=2)

        # --- SECTION 1: SOURCE FILES ---
        self.add_header("1. SOURCE FILES")
        tk.Button(self.sidebar, text="Load Background Photo", command=self.load_background, bg="#e1f5fe").pack(fill="x", pady=2)
        tk.Button(self.sidebar, text="Load Logo PNG", command=self.load_wm_file, bg="#fff9c4").pack(fill="x", pady=2)

        text_frame = tk.LabelFrame(self.sidebar, text="Text Watermark", padx=10, pady=5)
        text_frame.pack(fill="x", pady=10)
        tk.Entry(text_frame, textvariable=self.vars["wm_text"]).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(text_frame, text="Update", command=self.generate_text).pack(side="right")
        
        # --- PARAMETER GROUPS ---
        self.add_header("2. PLACEMENT")
        self.create_stepper_row("X Position", self.vars["wm_x"], 10)
        self.create_stepper_row("Y Position", self.vars["wm_y"], 10)
        self.create_stepper_row("Scale", self.vars["wm_scale"], 0.1)
        self.create_stepper_row("Rotation", self.vars["wm_rotation"], 5)

        self.add_header("3. COLOR GRADIENT")
        c_btn_frame = tk.Frame(self.sidebar)
        c_btn_frame.pack(fill="x", pady=5)
        self.btn_c1 = tk.Button(c_btn_frame, text="Color A", bg=self.rgb_to_hex(self.color_min), command=lambda: self.pick_color("min"))
        self.btn_c1.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_c2 = tk.Button(c_btn_frame, text="Color B", bg=self.rgb_to_hex(self.color_max), command=lambda: self.pick_color("max"))
        self.btn_c2.pack(side="left", expand=True, fill="x", padx=2)
        
        self.create_stepper_row("Center X", self.vars["c_origin_x"], 0.05)
        self.create_stepper_row("Center Y", self.vars["c_origin_y"], 0.05)
        self.create_stepper_row("Sine Rings", self.vars["c_cycles"], 0.5)

        self.add_header("4. TRANSPARENCY")
        self.create_stepper_row("Alpha Min", self.vars["alpha_min"], 5)
        self.create_stepper_row("Alpha Max", self.vars["alpha_max"], 5)
        self.create_stepper_row("Center X", self.vars["a_origin_x"], 0.05)
        self.create_stepper_row("Center Y", self.vars["a_origin_y"], 0.05)
        self.create_stepper_row("Sine Rings", self.vars["a_cycles"], 0.5)

        self.add_header("5. WAVE DISTORTION")
        self.create_stepper_row("Amplitude", self.vars["wave_amp"], 1.0)
        self.create_stepper_row("Frequency", self.vars["wave_freq"], 0.2)

        tk.Button(self.sidebar, text="SAVE FINAL IMAGE", bg="#308030", fg="white", font=("Arial", 12, "bold"), command=self.save_result, pady=12).pack(fill="x", pady=30)

        self.preview_label = tk.Label(self.root, bg="#111111")
        self.preview_label.pack(side="right", expand=True, fill="both")

    def create_stepper_row(self, label_text, var, step):
        """Creates a label, a minus button, a text entry, and a plus button."""
        frame = tk.Frame(self.sidebar)
        frame.pack(fill="x", pady=3)
        
        tk.Label(frame, text=label_text, width=14, anchor="w", font=("Arial", 9)).pack(side="left")
        
        # Helper to change value and render
        def change(delta):
            current = var.get()
            # Rounding to prevent floating point math errors (e.g., 0.30000000004)
            new_val = round(current + delta, 3)
            var.set(new_val)
            self.update_all()

        # Minus Button
        tk.Button(frame, text=" - ", command=lambda: change(-step), width=3).pack(side="left", padx=2)
        
        # Entry field
        entry = tk.Entry(frame, textvariable=var, width=10, justify='center', font=("Consolas", 10))
        entry.pack(side="left", padx=2)
        entry.bind("<Return>", lambda e: self.update_all()) # Render only on Enter
        
        # Plus Button
        tk.Button(frame, text=" + ", command=lambda: change(step), width=3).pack(side="left", padx=2)

    def add_header(self, text):
        tk.Label(self.sidebar, text=text, font=("Arial", 10, "bold"), fg="#2c3e50").pack(anchor="w", pady=(15, 2))

    # --- CORE PROCESSING ---
    def update_all(self, _=None):
        """The main render engine. Only called by explicit actions."""
        if not self.raw_watermark: return
        
        img = self.raw_watermark.copy()
        w, h = img.size
        data = np.array(img).astype(float)
        y_idx, x_idx = np.ogrid[:h, :w]
        max_dim = np.sqrt(w**2 + h**2)

        # Color Math
        cx, cy = w * self.vars["c_origin_x"].get(), h * self.vars["c_origin_y"].get()
        dist_c = np.sqrt((x_idx - cx)**2 + (y_idx - cy)**2)
        ratio_c = (1 - np.cos((dist_c / max_dim) * (np.pi * self.vars["c_cycles"].get()))) / 2
        for i in range(3):
            data[..., i] = self.color_min[i] + (self.color_max[i] - self.color_min[i]) * ratio_c
            
        # Alpha Math
        ax, ay = w * self.vars["a_origin_x"].get(), h * self.vars["a_origin_y"].get()
        dist_a = np.sqrt((x_idx - ax)**2 + (y_idx - ay)**2)
        ratio_a = (1 - np.cos((dist_a / max_dim) * (np.pi * self.vars["a_cycles"].get()))) / 2
        a_min, a_max = self.vars["alpha_min"].get(), self.vars["alpha_max"].get()
        data[..., 3] = (a_min + (a_max - a_min) * ratio_a) * (data[..., 3] / 255.0)

        processed = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))

        # Waves
        amp, freq = self.vars["wave_amp"].get(), self.vars["wave_freq"].get()
        if amp > 0:
            pad = int(amp * 2) + 10
            wave_img = Image.new("RGBA", (w, h + pad), (0,0,0,0))
            for x in range(w):
                offset = int(amp * math.sin(2 * math.pi * freq * (x / float(w))))
                col = processed.crop((x, 0, x + 1, h))
                wave_img.paste(col, (x, (pad // 2) + offset), col)
            processed = wave_img

        # Transform
        s = self.vars["wm_scale"].get()
        if s > 0:
            processed = processed.resize((max(1, int(processed.width*s)), max(1, int(processed.height*s))), Image.LANCZOS)
        self.distorted_wm = processed.rotate(self.vars["wm_rotation"].get(), expand=True)

        # Composite Preview
        if self.background_image:
            self.final_comp = self.background_image.copy()
            self.final_comp.paste(self.distorted_wm, (self.vars["wm_x"].get(), self.vars["wm_y"].get()), self.distorted_wm)
            preview_img = self.final_comp.copy()
        else:
            preview_img = Image.new("RGB", (1200, 800), (35, 35, 35))
            preview_img.paste(self.distorted_wm, (150, 150), self.distorted_wm)

        preview_img.thumbnail((1000, 800), Image.LANCZOS)
        self.tk_preview = ImageTk.PhotoImage(preview_img)
        self.preview_label.config(image=self.tk_preview)

    # --- OTHER HANDLERS ---
    def generate_text(self):
        text = self.vars["wm_text"].get() or "WATERMARK"
        try: font = ImageFont.truetype("arialbd.ttf", 140)
        except: font = ImageFont.load_default()
        bbox = font.getbbox(text)
        w, h = (bbox[2]-bbox[0])+100, (bbox[3]-bbox[1])+100
        img = Image.new("RGBA", (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), text, font=font, fill=(255, 255, 255, 255))
        self.raw_watermark = img
        self.update_all()

    def pick_color(self, target):
        color = colorchooser.askcolor()[0]
        if color:
            rgb = tuple(int(x) for x in color)
            if target == "min": 
                self.color_min = rgb
                self.btn_c1.config(bg=self.rgb_to_hex(rgb))
            else: 
                self.color_max = rgb
                self.btn_c2.config(bg=self.rgb_to_hex(rgb))
            self.update_all()

    def load_background(self):
        path = filedialog.askopenfilename()
        if path:
            self.background_image = Image.open(path).convert("RGBA")
            self.update_all()

    def load_wm_file(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            self.raw_watermark = Image.open(path).convert("RGBA")
            self.update_all()

    def save_config(self):
        data = {k: v.get() for k, v in self.vars.items()}
        data['color_min'], data['color_max'] = self.color_min, self.color_max
        path = filedialog.asksaveasfilename(defaultextension=".yaml")
        if path:
            with open(path, 'w') as f: yaml.dump(data, f)

    def load_config(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, 'r') as f: data = yaml.safe_load(f)
            for k, v in data.items():
                if k in self.vars: self.vars[k].set(v)
            self.color_min, self.color_max = tuple(data['color_min']), tuple(data['color_max'])
            self.btn_c1.config(bg=self.rgb_to_hex(self.color_min))
            self.btn_c2.config(bg=self.rgb_to_hex(self.color_max))
            self.update_all()

    def save_result(self):
        if self.final_comp:
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path: self.final_comp.save(path)

    def rgb_to_hex(self, rgb): return "#%02x%02x%02x" % rgb

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkDistorder(root)
    root.mainloop()
    
