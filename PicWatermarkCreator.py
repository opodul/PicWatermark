import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import yaml
import os
import random

def find_fonts():
    fonts = []
    
    if 0:
        # Common system paths for fonts as fallback
        font_paths = ["./fonts", "/usr/share/fonts", "C:\\Windows\\Fonts", "/Library/Fonts"]
    else:
        # or take only the ones in ./fonts
        font_paths = ["./fonts",]
    for path in font_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f.lower().endswith((".ttf", ".otf")):
                        fonts.append(os.path.join(root, f))
    return sorted(list(set(fonts)))

def random_params(img_width, img_height, fonts):
    return {
        "enabled": True,
        "text": "WATERMARK\nSECOND LINE",
        "x": random.randint(0, img_width // 2),
        "y": random.randint(0, img_height // 2),
        "rotation": random.randint(15, 65),
        "font": random.choice(fonts) if fonts else "Arial.ttf",
        "size": random.randint(20, 50)
    }

class WatermarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Watermark Creator")
        self.root.geometry("1500x900")

        self.image_path = None
        self.original_image = None
        self.watermark_rows = []
        self.font_list = find_fonts()

        self.main_container = tk.Frame(root)
        self.main_container.pack(fill="both", expand=True)

        # --- LEFT COLUMN ---
        self.left = tk.Frame(self.main_container)
        self.left.pack(side="left", fill="y", padx=10)

        controls_left = tk.Frame(self.left)
        controls_left.pack(fill="x", pady=5)

        tk.Button(controls_left, text="Load Image", command=self.load_image).pack(side="left", padx=5)

        # Preview Width with +/-
        tk.Label(controls_left, text="W:").pack(side="left", padx=(5, 0))
        self.prev_w_entry = tk.Entry(controls_left, width=5)
        self.prev_w_entry.pack(side="left")
        tk.Button(controls_left, text="-", command=lambda: self.adj_entry(self.prev_w_entry, -50)).pack(side="left")
        tk.Button(controls_left, text="+", command=lambda: self.adj_entry(self.prev_w_entry, 50)).pack(side="left")

        # Preview Height with +/-
        tk.Label(controls_left, text="H:").pack(side="left", padx=(5, 0))
        self.prev_h_entry = tk.Entry(controls_left, width=5)
        self.prev_h_entry.pack(side="left")
        tk.Button(controls_left, text="-", command=lambda: self.adj_entry(self.prev_h_entry, -50)).pack(side="left")
        tk.Button(controls_left, text="+", command=lambda: self.adj_entry(self.prev_h_entry, 50)).pack(side="left")

        self.preview_label = tk.Label(self.left, bg="gray")
        self.preview_label.pack(side="top", anchor="nw")

        # --- RIGHT COLUMN ---
        self.right = tk.Frame(self.main_container)
        self.right.pack(side="left", fill="both", expand=True, padx=10)

        btn_frame = tk.Frame(self.right)
        btn_frame.pack(fill="x")
        
        btns = [
            ("Add Watermark", self.add_row),
            ("Save YAML", self.save_yaml),
            ("Load YAML", self.load_yaml),
            ("Refresh Preview", self.update_preview),
            ("Export Final", self.export_final),
            ("Export WM Only", self.export_watermark_only)
        ]
        for text, cmd in btns:
            tk.Button(btn_frame, text=text, command=cmd).pack(side="left", padx=2, pady=5)

        glob_frame = tk.LabelFrame(self.right, text="Global Scale (X/Y Coef)", pady=5)
        glob_frame.pack(fill="x", pady=5)

        tk.Label(glob_frame, text="X Coef:").pack(side="left", padx=5)
        self.glob_x = tk.Entry(glob_frame, width=6)
        self.glob_x.insert(0, "1.0")
        self.glob_x.pack(side="left", padx=5)
        
        tk.Label(glob_frame, text="Y Coef:").pack(side="left", padx=5)
        self.glob_y = tk.Entry(glob_frame, width=6)
        self.glob_y.insert(0, "1.0")
        self.glob_y.pack(side="left", padx=5)

        # Binding global coefs for auto-update
        self.glob_x.bind("<KeyRelease>", lambda e: self.update_preview())
        self.glob_y.bind("<KeyRelease>", lambda e: self.update_preview())
        self.prev_w_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        self.prev_h_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        self.canvas_frame = tk.Frame(self.right)
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.rows_canvas = tk.Canvas(self.canvas_frame)
        self.rows_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.rows_canvas.yview)
        self.rows_scrollable_inner = tk.Frame(self.rows_canvas)

        self.rows_scrollable_inner.bind("<Configure>", lambda e: self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all")))
        self.rows_canvas.create_window((0,0), window=self.rows_scrollable_inner, anchor="nw")
        self.rows_canvas.configure(yscrollcommand=self.rows_scrollbar.set)

        self.rows_canvas.pack(side="left", fill="both", expand=True)
        self.rows_scrollbar.pack(side="right", fill="y")

    def adj_entry(self, entry, delta):
        try:
            val = int(float(entry.get()))
            entry.delete(0, tk.END)
            entry.insert(0, str(val + delta))
            self.update_preview()
        except: pass

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if not path: return
        self.image_path = path
        self.original_image = Image.open(path).convert("RGBA")
        
        self.root.update_idletasks()
        init_w = min(self.original_image.width, self.root.winfo_width() // 2)
        init_h = min(self.original_image.height, self.root.winfo_height() // 2)
        
        self.prev_w_entry.delete(0, tk.END); self.prev_w_entry.insert(0, str(init_w))
        self.prev_h_entry.delete(0, tk.END); self.prev_h_entry.insert(0, str(init_h))
        self.update_preview()

    def add_row(self, config=None):
        if config is None:
            if self.original_image is None: return
            config = random_params(self.original_image.width, self.original_image.height, self.font_list)

        row = {}
        # Using a higher row height for multiline text
        f = tk.Frame(self.rows_scrollable_inner, bd=1, relief="sunken", padx=5, pady=5)
        f.pack(pady=5, fill="x", anchor="w")

        row["enabled"] = tk.BooleanVar(value=config["enabled"])
        tk.Checkbutton(f, variable=row["enabled"], command=self.update_preview).grid(row=0, column=0, rowspan=2)
        
        # Use tk.Text for multiline support
        t_box = tk.Text(f, width=60, height=3)
        t_box.grid(row=0, column=1, rowspan=2, padx=5)
        t_box.insert("1.0", config["text"])
        t_box.bind("<KeyRelease>", lambda e: self.update_preview())
        row["text_widget"] = t_box

        # X, Y, R, S with buttons
        fields = [("x", "X"), ("y", "Y"), ("rotation", "R"), ("size", "S")]
        for i, (key, label) in enumerate(fields):
            base_col = 2 + (i * 4)
            tk.Label(f, text=label).grid(row=0, column=base_col)
            
            e = tk.Entry(f, width=5)
            e.grid(row=0, column=base_col + 1)
            e.insert(0, config[key])
            e.bind("<KeyRelease>", lambda event: self.update_preview())
            row[key] = e
            
            # Step size for buttons: Rot/Size step by 2, X/Y step by 10
            step = 5 if key in ["rotation", "size"] else 10
            tk.Button(f, text="-", command=lambda ent=e: self.adj_entry(ent, -step), width=1).grid(row=0, column=base_col + 2)
            tk.Button(f, text="+", command=lambda ent=e: self.adj_entry(ent, step), width=1).grid(row=0, column=base_col + 3)

        row["font"] = tk.StringVar(value=config["font"])
        cb = ttk.Combobox(f, textvariable=row["font"], values=self.font_list, width=15)
        cb.grid(row=1, column=2, columnspan=10, sticky="ew", padx=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        self.watermark_rows.append(row)

    def render_watermark_layer(self):
        if self.original_image is None: return None
        img = Image.new("RGBA", self.original_image.size, (0,0,0,0))
        try:
            gx, gy = float(self.glob_x.get()), float(self.glob_y.get())
        except: gx, gy = 1.0, 1.0

        for r in self.watermark_rows:
            if not r["enabled"].get(): continue
            try:
                x, y = int(int(r["x"].get()) * gx), int(int(r["y"].get()) * gy)
                fnt = ImageFont.truetype(r["font"].get(), int(r["size"].get()))
                
                # Get multiline text from widget
                content = r["text_widget"].get("1.0", "end-1c")
                
                # Create a temporary layer for this specific text to rotate it
                txt_layer = Image.new("RGBA", img.size, (0,0,0,0))
                draw = ImageDraw.Draw(txt_layer)
                
                # CHANGED: Use draw.multiline_text instead of draw.text
                draw.multiline_text((x, y), content, font=fnt, fill=(255, 0, 0, 120), align="left")
                
                rot = txt_layer.rotate(int(r["rotation"].get()), expand=True, resample=Image.BICUBIC)
                
                # Re-center the rotated layer back to original size
                left = (rot.width - img.width) // 2
                top = (rot.height - img.height) // 2
                rot = rot.crop((left, top, left + img.width, top + img.height))
                
                img = Image.alpha_composite(img, rot)
            except Exception as e:
                print(f"Render error: {e}")
        return img

    def update_preview(self):
        if self.original_image is None: return
        wm = self.render_watermark_layer()
        res = Image.alpha_composite(self.original_image, wm)
        try:
            tw, th = int(self.prev_w_entry.get()), int(self.prev_h_entry.get())
        except: tw, th = 400, 400
        res.thumbnail((tw, th))
        self.tk_p = ImageTk.PhotoImage(res)
        self.preview_label.config(image=self.tk_p)

    def export_final(self):
        if not self.original_image: return
        p = filedialog.asksaveasfilename(defaultextension=".png")
        if p: Image.alpha_composite(self.original_image, self.render_watermark_layer()).save(p)

    def export_watermark_only(self):
        wm = self.render_watermark_layer()
        p = filedialog.asksaveasfilename(defaultextension=".png")
        if p and wm: wm.save(p)

    def save_yaml(self):
        c = {"image": self.image_path, "gx": self.glob_x.get(), "gy": self.glob_y.get(), "watermarks": []}
        for r in self.watermark_rows:
            # We only save values from actual dictionary keys
            data = {
                "enabled": r["enabled"].get(),
                "text": r["text_widget"].get("1.0", "end-1c"),
                "x": r["x"].get(),
                "y": r["y"].get(),
                "rotation": r["rotation"].get(),
                "size": r["size"].get(),
                "font": r["font"].get()
            }
            c["watermarks"].append(data)
        p = filedialog.asksaveasfilename(defaultextension=".yaml")
        if p:
            with open(p, "w") as f: yaml.dump(c, f)

    def load_yaml(self):
        p = filedialog.askopenfilename(filetypes=[("YAML", "*.yaml")])
        if not p: return
        with open(p, "r") as f: c = yaml.safe_load(f)
        for w in self.rows_scrollable_inner.winfo_children(): w.destroy()
        self.watermark_rows = []
        if "image" in c and c["image"]:
            self.image_path = c["image"]
            if os.path.exists(self.image_path):
                self.original_image = Image.open(self.image_path).convert("RGBA")
        self.glob_x.delete(0, tk.END); self.glob_x.insert(0, c.get("gx", "1.0"))
        self.glob_y.delete(0, tk.END); self.glob_y.insert(0, c.get("gy", "1.0"))
        for wm in c.get("watermarks", []): self.add_row(wm)
        self.update_preview()

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkGUI(root)
    root.mainloop()
    
