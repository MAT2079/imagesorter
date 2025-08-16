# requirements: pillow
# run: python main.py
import json, os, shutil, sys, time
from pathlib import Path
from tkinter import *
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageOps, ExifTags

PROJECTS_ROOT = Path.home() / "ImageSorterProjects"

def ensure_dir(p): p.mkdir(parents=True, exist_ok=True)

def load_exif(img):
    try:
        exif = img._getexif() or {}
        mapping = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        return mapping
    except Exception:
        return {}

def open_image(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # respect orientation
    return img

def unique_path(path: Path):
    if not path.exists(): return path
    stem, ext = path.stem, path.suffix
    i = 1
    while True:
        p = path.with_name(f"{stem}_{i}{ext}")
        if not p.exists(): return p
        i += 1

class Project:
    def __init__(self, root: Path):
        self.root = root
        self.meta_path = root / "project.json"
        self.name = root.name
        self.classes = []
        self.settings = {"thumbnail_max_px": 1024}
        self.load()

    def load(self):
        if self.meta_path.exists():
            d = json.loads(self.meta_path.read_text())
            self.name = d["name"]
            self.classes = d["classes"]
            self.settings = d.get("settings", self.settings)
        else:
            self.classes = ["unsorted", "class_1"]
            self.save()

    def save(self):
        d = {
            "name": self.name,
            "version": 1,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "classes": self.classes,
            "root": str(self.root),
            "settings": self.settings,
        }
        self.meta_path.write_text(json.dumps(d, indent=2))

    def init_folders(self):
        ensure_dir(self.root)
        for c in self.classes:
            ensure_dir(self.root / c)

    def unsorted_list(self):
        u = self.root / "unsorted"
        if not u.exists(): return []
        files = [p for p in sorted(u.iterdir()) if p.suffix.lower() in (".jpg",".jpeg",".png",".bmp",".webp",".tif",".tiff")]
        return files

class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Sorter")
        ensure_dir(PROJECTS_ROOT)
        self.project = None
        self.geometry("1100x800")
        self.show_home()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ---------- HOME ----------
    def show_home(self):
        self.clear()
        Label(self, text="Projects", font=("Segoe UI", 20, "bold")).pack(pady=10)
        listbox = Listbox(self, width=80, height=10)
        listbox.pack(pady=10)
        projects = []
        for p in sorted(PROJECTS_ROOT.iterdir()):
            if (p / "project.json").exists():
                projects.append(p)
                listbox.insert(END, p.name)
        def open_sel():
            sel = listbox.curselection()
            if not sel: return
            self.open_project(projects[sel[0]])
        Button(self, text="Open", command=open_sel).pack(pady=5)
        Button(self, text="New Project", command=self.show_new_project).pack(pady=5)

    # ---------- NEW PROJECT ----------
    def show_new_project(self):
        self.clear()
        frm = Frame(self); frm.pack(pady=20)
        Label(frm, text="New Project", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        Label(frm, text="Project name").grid(row=1, column=0, sticky="e")
        name_var = StringVar(value="my_project")
        Entry(frm, textvariable=name_var, width=40).grid(row=1, column=1, pady=5)

        classes = ["unsorted", "class_1"]
        classes_var = StringVar(value="\n".join(classes))
        Label(frm, text="Class names (one per line)").grid(row=2, column=0, sticky="ne")
        TextBox = Text(frm, width=40, height=8)
        TextBox.insert("1.0", "\n".join(classes))
        TextBox.grid(row=2, column=1, pady=5)

        def create():
            name = name_var.get().strip()
            if not name: 
                messagebox.showerror("Error","Project name required"); return
            cls = [c.strip() for c in TextBox.get("1.0", END).splitlines() if c.strip()]
            if "unsorted" not in [c.lower() for c in cls]:
                cls = ["unsorted"] + cls
            # dedupe, keep order
            seen=set(); final=[]
            for c in cls:
                if c.lower() not in seen:
                    final.append(c); seen.add(c.lower())
            root = PROJECTS_ROOT / name
            if root.exists() and (root / "project.json").exists():
                messagebox.showerror("Error","Project already exists"); return
            proj = Project(root)
            proj.name = name
            proj.classes = final
            proj.save()
            proj.init_folders()
            self.project = proj
            self.prompt_add_images()

        Button(frm, text="Create", command=create).grid(row=3, column=1, sticky="e", pady=10)
        Button(frm, text="Back", command=self.show_home).grid(row=3, column=0, sticky="w", pady=10)

    def open_project(self, root: Path):
        self.project = Project(root)
        self.show_preprocess()

    # ---------- ADD IMAGES ----------
    def prompt_add_images(self):
        if not self.project: return
        paths = filedialog.askopenfilenames(title="Add images to unsorted")
        if paths:
            ud = self.project.root / "unsorted"
            for p in paths:
                src = Path(p)
                dst = unique_path(ud / src.name)
                ensure_dir(ud)
                shutil.copy2(src, dst)
        self.show_preprocess()

    # ---------- PREPROCESS ----------
    def show_preprocess(self):
        self.clear()
        top = Frame(self); top.pack(fill=X)
        Label(top, text=f"Project: {self.project.name}", font=("Segoe UI", 16, "bold")).pack(side=LEFT, padx=10, pady=8)
        Button(top, text="Add Images", command=self.prompt_add_images).pack(side=RIGHT, padx=10)

        body = Frame(self); body.pack(fill=BOTH, expand=True)
        left = Frame(body); left.pack(side=LEFT, fill=BOTH, expand=True)
        right = Frame(body, width=300); right.pack(side=RIGHT, fill=Y)

        canvas = Canvas(left, bg="#222", highlightthickness=0)
        canvas.pack(fill=BOTH, expand=True)

        info = Text(right, width=40, height=20)
        info.pack(padx=10, pady=10)
        info.configure(state=DISABLED)

        rename_var = StringVar()
        Entry(right, textvariable=rename_var).pack(padx=10, pady=5)
        status = StringVar(value="")
        Label(right, textvariable=status).pack(padx=10, pady=5)

        btns = Frame(right); btns.pack(padx=10, pady=10)
        class_buttons = []
        for c in self.project.classes:
            def mk(cmdc=c):
                return lambda: send_to(cmdc)
            b = Button(btns, text=f"Send → {c}", command=mk())
            b.pack(fill=X, pady=2)
            class_buttons.append(b)

        Button(right, text="Back to unsorted", command=lambda: send_to("unsorted")).pack(fill=X, padx=10, pady=5)
        Button(right, text="Skip (Next)", command=lambda: next_image()).pack(fill=X, padx=10, pady=5)

        # Crop state
        crop_mode = {"on": False, "start": None, "rect": None, "box": None}

        current = {"path": None, "img": None, "disp": None, "scale": 1.0}

        def load_info(img, path):
            exif = load_exif(img)
            lines = [
                f"File: {path.name}",
                f"Size: {img.width} x {img.height}",
                f"Format: {img.format or path.suffix.upper()}",
            ]
            if exif.get("Model"):
                lines.append(f"Camera: {exif.get('Make','')} {exif.get('Model')}")
            if exif.get("DateTimeOriginal"):
                lines.append(f"Shot: {exif.get('DateTimeOriginal')}")
            info.configure(state=NORMAL); info.delete("1.0", END)
            info.insert("1.0", "\n".join(lines))
            info.configure(state=DISABLED)

        def fit_image(img, cw, ch):
            if cw<2 or ch<2: return img, 1.0
            scale = min(cw/img.width, ch/img.height, 1.0)
            if scale <= 0: scale=1.0
            disp = img.resize((int(img.width*scale), int(img.height*scale)))
            return disp, scale

        def draw_image():
            canvas.delete("all")
            if not current["img"]: return
            cw = canvas.winfo_width(); ch = canvas.winfo_height()
            disp, scale = fit_image(current["img"], cw, ch)
            current["disp"] = ImageTk.PhotoImage(disp)
            current["scale"] = scale
            canvas.create_image(cw//2, ch//2, image=current["disp"])
            # draw crop rect if any
            if crop_mode["rect"] and crop_mode["box"]:
                x1,y1,x2,y2 = crop_mode["box"]
                sx = (cw - disp.width)//2; sy = (ch - disp.height)//2
                canvas.coords(crop_mode["rect"],
                              sx + x1*scale, sy + y1*scale, sx + x2*scale, sy + y2*scale)

        def load_first():
            files = self.project.unsorted_list()
            if not files:
                status.set("No images in unsorted. Add images to begin.")
                current["path"]=None; current["img"]=None
                canvas.delete("all"); return
            path = files[0]
            img = open_image(path)
            current["path"]=path; current["img"]=img
            rename_var.set(path.stem)
            load_info(img, path)
            draw_image()

        def on_resize(event):
            if current["img"]:
                draw_image()
        canvas.bind("<Configure>", on_resize)

        def canvas_to_image_coords(cx, cy):
            # map canvas coords to image coords
            cw = canvas.winfo_width(); ch = canvas.winfo_height()
            disp_w = int(current["img"].width * current["scale"])
            disp_h = int(current["img"].height * current["scale"])
            sx = (cw - disp_w)//2; sy = (ch - disp_h)//2
            ix = (cx - sx) / current["scale"]
            iy = (cy - sy) / current["scale"]
            ix = max(0, min(current["img"].width, ix))
            iy = max(0, min(current["img"].height, iy))
            return int(ix), int(iy)

        def start_crop(event):
            if not current["img"]: return
            crop_mode["on"] = True
            crop_mode["start"] = canvas_to_image_coords(event.x, event.y)
            if crop_mode["rect"]:
                canvas.delete(crop_mode["rect"])
            crop_mode["rect"] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="white", width=2, dash=(4,2))

        def drag_crop(event):
            if not crop_mode["on"] or not current["img"]: return
            x1,y1 = crop_mode["start"]
            x2,y2 = canvas_to_image_coords(event.x, event.y)
            # normalize
            x1,x2 = sorted((x1,x2)); y1,y2 = sorted((y1,y2))
            crop_mode["box"] = (x1,y1,x2,y2)
            draw_image()

        def end_crop(event):
            crop_mode["on"] = False

        canvas.bind("<ButtonPress-1>", start_crop)
        canvas.bind("<B1-Motion>", drag_crop)
        canvas.bind("<ButtonRelease-1>", end_crop)

        def next_image():
            # simply reload first item after moving/deleting previous
            load_first()

        def apply_rename_and_crop(dst_dir: Path):
            src = current["path"]
            if not src: return None
            img = current["img"].copy()
            # apply crop if box set and valid
            if crop_mode["box"]:
                x1,y1,x2,y2 = crop_mode["box"]
                if x2-x1 >= 10 and y2-y1 >= 10:
                    img = img.crop((x1,y1,x2,y2))
            # decide filename
            new_stem = rename_var.get().strip() or src.stem
            ext = src.suffix.lower()
            dst = unique_path(dst_dir / f"{new_stem}{ext}")
            # atomic-ish save
            tmp = dst.with_suffix(dst.suffix + ".tmp")
            img.save(tmp)
            os.replace(tmp, dst)
            # remove original
            try:
                os.remove(src)
            except Exception:
                pass
            # reset crop
            crop_mode["box"]=None
            return dst

        def send_to(class_name: str):
            if not current["path"]: return
            if class_name not in self.project.classes:
                messagebox.showerror("Error","Unknown class"); return
            dst_dir = self.project.root / class_name
            ensure_dir(dst_dir)
            out = apply_rename_and_crop(dst_dir)
            status.set(f"Sent to '{class_name}': {out.name if out else ''}")
            next_image()

        # shortcuts
        def on_key(e):
            if e.char.isdigit():
                idx = int(e.char)
                # 0 → unsorted
                if idx == 0:
                    send_to("unsorted"); return
                # 1..9 map to classes excluding unsorted
                classes = [c for c in self.project.classes if c.lower()!="unsorted"]
                if 1 <= idx <= len(classes):
                    send_to(classes[idx-1]); return
            if e.keysym.lower() in ("space", "n"):
                next_image()
        self.bind("<Key>", on_key)

        load_first()

if __name__ == "__main__":
    App().mainloop()
