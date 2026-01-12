import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import keyboard
import threading
import time
import sys
import ctypes
import json
import os
import winreg  # Do obsługi autostartu
from PIL import Image, ImageDraw, ImageTk # Requires: pip install Pillow
import pystray # Requires: pip install pystray

# =================================================================================
# GLOBAL PATH HELPERS
# =================================================================================

def get_app_path():
    """
    Returns the directory where the .exe or .py file is located.
    Critical for PyInstaller --onefile mode to save config next to the exe.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        return os.path.dirname(sys.executable)
    else:
        # Running as .py script
        return os.path.dirname(os.path.abspath(__file__))

APP_TITLE = "Mouse T9 Keypad"
GITHUB_LINK = "github.com/wiciu1000/mouse_t9keypad"
CONFIG_FILENAME = "mouse_t9keypad_config.json"
CONFIG_FILE_PATH = os.path.join(get_app_path(), CONFIG_FILENAME)

# Default English T9 mapping
DEFAULT_MAPPING = {
    'f13': ['.', ',', '?', '!', '1', '-', '@', ':'],  # Btn 1
    'f14': ['a', 'b', 'c', '2'],                      # Btn 2
    'f15': ['d', 'e', 'f', '3'],                      # Btn 3
    'f16': ['g', 'h', 'i', '4'],                      # Btn 4
    'f17': ['j', 'k', 'l', '5'],                      # Btn 5
    'f18': ['m', 'n', 'o', '6'],                      # Btn 6
    'f19': ['p', 'q', 'r', 's', '7'],                 # Btn 7
    'f20': ['t', 'u', 'v', '8'],                      # Btn 8
    'f21': ['w', 'x', 'y', 'z', '9'],                 # Btn 9
    'f22': ['ENTER'],                                 # Btn 10
    'f23': [' ', '0'],                                # Btn 11
    'f24': ['BACKSPACE', '(', ')', '[', ']', '{', '}', '<', '>', '/', '\\', '*', '#'] # Btn 12
}

DEFAULT_CONFIG = {
    "delay": 800,
    "minimize_to_tray_on_close": False,
    "start_minimized": False,
    "run_on_startup": False,
    "mapping": DEFAULT_MAPPING
}

# =================================================================================
# ICON GENERATOR (Procedural Pixel Art)
# =================================================================================

def create_app_icon():
    """Generates a retro phone icon programmatically using PIL."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)) # Transparent bg
    draw = ImageDraw.Draw(img)
    
    # Colors
    c_body = (50, 50, 60, 255)      # Dark Grey Body
    c_screen = (130, 160, 130, 255) # Nokia Green Screen
    c_btn = (200, 200, 200, 255)    # Light Grey Buttons
    c_outline = (20, 20, 20, 255)   # Black outline
    
    # 1. Body (Rounded look via overlapping rectangles)
    # Main block
    draw.rectangle([16, 4, 48, 60], fill=c_body, outline=c_outline)
    # Antenna stub
    draw.rectangle([40, 4, 44, 10], fill=(20, 20, 20, 255)) 

    # 2. Screen
    draw.rectangle([20, 10, 44, 28], fill=c_screen, outline=c_outline)
    # Text on screen "T9"
    # Drawing tiny pixel text manually for crispness
    # T
    draw.line([24, 14, 30, 14], fill=(0,0,0,255), width=1)
    draw.line([27, 14, 27, 24], fill=(0,0,0,255), width=1)
    # 9
    draw.rectangle([33, 14, 38, 19], outline=(0,0,0,255))
    draw.line([38, 14, 38, 24], fill=(0,0,0,255), width=1)
    draw.line([33, 24, 38, 24], fill=(0,0,0,255), width=1)

    # 3. Keypad (3x4 grid)
    start_y = 34
    start_x = 20
    btn_w = 6
    btn_h = 4
    gap = 2
    
    for row in range(4):
        for col in range(3):
            x = start_x + (btn_w + gap) * col
            y = start_y + (btn_h + gap) * row
            draw.rectangle([x, y, x+btn_w, y+btn_h], fill=c_btn)

    return img

# =================================================================================
# SYSTEM UTILS (Startup & CapsLock)
# =================================================================================

class SystemUtils:
    @staticmethod
    def is_caps_lock_on():
        """Returns True if Caps Lock is toggled on."""
        hllDll = ctypes.WinDLL("User32.dll")
        vk = 0x14
        return hllDll.GetKeyState(vk) & 0x0001

    @staticmethod
    def set_startup(enable=True):
        """Adds or removes the app from Windows Startup registry."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "MouseT9Keypad"
        
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            script_path = os.path.abspath(sys.argv[0])
            exe_path = f'"{python_exe}" "{script_path}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Registry error: {e}")
            return False

# =================================================================================
# CONFIG MANAGER
# =================================================================================

class ConfigManager:
    @staticmethod
    def load():
        if not os.path.exists(CONFIG_FILE_PATH):
            print("Config not found. Creating default.")
            ConfigManager.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, val in DEFAULT_CONFIG.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(data):
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

# =================================================================================
# OVERLAY CLASS
# =================================================================================

class OverlayWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)
        
        self.label = tk.Label(
            self, 
            text="", 
            font=("Roboto", 24, "bold"),
            bg="#f0f0f0", fg="#000000",
            padx=15, pady=5, borderwidth=2, relief="solid"
        )
        self.label.pack()
        self.withdraw()

    def show_char(self, char):
        self.label.config(text=char)
        try:
            x, y = self.master.winfo_pointerxy()
            self.geometry(f"+{x+20}+{y+20}")
            self.deiconify()
        except:
            pass

    def hide(self):
        self.withdraw()

# =================================================================================
# T9 ENGINE LOGIC
# =================================================================================

class T9Engine:
    def __init__(self, root, config_app):
        self.root = root
        self.config_app = config_app
        self.overlay = OverlayWindow(root)
        
        self.current_key = None
        self.char_index = 0
        self.timer_id = None
        
        self.mapping = self.config_app.config_data["mapping"]
        self.setup_hooks()

    def update_mapping(self, new_mapping):
        self.mapping = new_mapping

    def setup_hooks(self):
        print("Installing hooks...")
        try:
            for i in range(13, 25):
                key_name = f'f{i}'
                keyboard.on_press_key(key_name, self.on_key_press, suppress=True)
            print("Hooks active.")
        except Exception as e:
            self.config_app.update_status(f"HOOK ERROR: {e}")

    def should_capitalize(self):
        shift = keyboard.is_pressed('shift')
        caps = SystemUtils.is_caps_lock_on()
        return shift != caps 

    def commit_char(self):
        if self.current_key:
            char_list = self.mapping.get(self.current_key, [])
            if not char_list: return

            char_to_type = char_list[self.char_index]
            
            is_ctrl = keyboard.is_pressed('ctrl')
            is_shift = keyboard.is_pressed('shift')

            if char_to_type == 'ENTER':
                keyboard.send('enter')
            elif char_to_type == 'SPACE':
                keyboard.write(' ')
            elif char_to_type == 'BACKSPACE':
                keyboard.send('backspace')
            else:
                if is_ctrl:
                    keyboard.send(char_to_type.lower())
                    mods = "Ctrl+"
                    if is_shift: mods += "Shift+"
                    self.config_app.update_status(f"Shortcut: {mods}{char_to_type.upper()}")
                else:
                    if self.should_capitalize() and len(char_to_type) == 1 and char_to_type.isalpha():
                        char_to_type = char_to_type.upper()
                    keyboard.write(char_to_type)
                    self.config_app.update_status(f"Typed: {char_to_type}")
            
        self.current_key = None
        self.char_index = 0
        self.overlay.hide()
        self.timer_id = None

    def on_key_press(self, event):
        key_name = event.name.lower()
        self.root.after_idle(lambda: self.process_key_gui_thread(key_name))

    def process_key_gui_thread(self, key_name):
        self.config_app.update_status(f"Signal: {key_name.upper()}")
        
        if key_name not in self.mapping:
            return

        char_list = self.mapping[key_name]
        if not char_list: return

        if self.current_key == key_name and self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.char_index = (self.char_index + 1) % len(char_list)
        else:
            if self.current_key is not None:
                self.commit_char()
            self.current_key = key_name
            self.char_index = 0

        preview_char = char_list[self.char_index]
        
        display_text = preview_char
        
        is_ctrl = keyboard.is_pressed('ctrl')
        is_shift = keyboard.is_pressed('shift')

        if preview_char == 'BACKSPACE':
             display_text = "<<"
        elif preview_char != 'ENTER':
            if is_ctrl:
                mods = "Ctrl+"
                if is_shift: mods += "Shift+"
                display_text = f"{mods}{preview_char.upper()}"
            elif self.should_capitalize() and len(preview_char) == 1 and preview_char.isalpha():
                display_text = preview_char.upper()

        self.overlay.show_char(display_text)
        
        delay_ms = self.config_app.config_data["delay"]
        self.timer_id = self.root.after(delay_ms, self.commit_char)

# =================================================================================
# UI ELEMENTS
# =================================================================================

class PhoneKey(tk.Frame):
    def __init__(self, master, number, chars, command):
        super().__init__(master, relief="raised", borderwidth=2, bg="#e1e1e1")
        self.command = command
        self.bind("<Button-1>", self.on_click)
        
        container = tk.Frame(self, bg="#e1e1e1")
        container.pack(expand=True, fill="both", padx=2, pady=2)
        container.bind("<Button-1>", self.on_click)
        
        self.lbl_num = tk.Label(container, text=str(number), font=("Roboto", 16, "bold"), bg="#e1e1e1", fg="#333")
        self.lbl_num.pack(pady=(2, 0))
        self.lbl_num.bind("<Button-1>", self.on_click)
        
        clean_chars = "".join(chars[:3])
        if not chars: clean_chars = "..."
        if "ENTER" in chars: clean_chars = "Enter"
        if "BACKSPACE" in chars: clean_chars = "<<"
        
        self.lbl_chars = tk.Label(container, text=clean_chars, font=("Roboto", 10), bg="#e1e1e1", fg="#666")
        self.lbl_chars.pack()
        self.lbl_chars.bind("<Button-1>", self.on_click)
        
    def update_chars(self, chars):
        clean_chars = "".join(chars[:3])
        if not chars: clean_chars = "..."
        if "ENTER" in chars: clean_chars = "Enter"
        if "BACKSPACE" in chars: clean_chars = "<<"
        self.lbl_chars.config(text=clean_chars)

    def on_click(self, event):
        if self.command:
            self.command()

# =================================================================================
# MAIN CONFIGURATION WINDOW (GUI)
# =================================================================================

class SettingsApp(tk.Tk):
    def __init__(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass 

        super().__init__()
        self.title(APP_TITLE)
        
        # Generowanie i ustawianie ikony aplikacji
        self.app_icon_img = create_app_icon()
        self.tk_icon = ImageTk.PhotoImage(self.app_icon_img)
        self.iconphoto(False, self.tk_icon)
        
        self.geometry("400x600")
        self.minsize(300, 400)
        self.resizable(True, True) 
        
        style = ttk.Style()
        style.configure(".", font=("Roboto", 10))
        style.configure("TLabel", font=("Roboto", 10))
        style.configure("TButton", font=("Roboto", 10))
        
        self.config_data = ConfigManager.load()
        
        self.delay_var = tk.IntVar(value=self.config_data["delay"])
        self.minimize_tray_var = tk.BooleanVar(value=self.config_data["minimize_to_tray_on_close"])
        self.startup_var = tk.BooleanVar(value=self.config_data.get("run_on_startup", False))
        
        self.create_tray_icon()
        self.create_widgets()
        
        if not self.is_admin():
            self.show_admin_warning()
        
        self.engine = T9Engine(self, self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close_window)

        if self.config_data.get("start_minimized", False):
            self.withdraw()

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def show_admin_warning(self):
        tk.messagebox.showwarning("Admin Required", "Run as Administrator to enable key hooks!")

    def create_tray_icon(self):
        # Używamy tej samej ikony co dla okna, ale w formacie PIL
        image = self.app_icon_img
        
        def show_window(icon, item):
            self.after(0, self.deiconify)

        def quit_app(icon, item):
            icon.stop()
            self.after(0, self.force_quit)

        menu = pystray.Menu(
            pystray.MenuItem('Show Settings', show_window, default=True),
            pystray.MenuItem('Exit', quit_app)
        )
        
        self.tray_icon = pystray.Icon("MouseT9Keypad", image, "Mouse T9 Keypad", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # TAB 1: Info
        tab_info = ttk.Frame(notebook)
        notebook.add(tab_info, text='Info')
        self.build_info_tab(tab_info)

        # TAB 2: General
        tab_main = ttk.Frame(notebook)
        notebook.add(tab_main, text='Settings')
        self.build_main_tab(tab_main)

        # TAB 3: Mapping
        tab_map = ttk.Frame(notebook)
        notebook.add(tab_map, text='Keypad')
        self.build_mapping_tab(tab_map)

        # Footer
        ttk.Label(self, text=GITHUB_LINK, foreground="blue", cursor="hand2").pack(pady=5)
        self.lbl_status = ttk.Label(self, text="Ready", relief="sunken", anchor="w")
        self.lbl_status.pack(side="bottom", fill="x")

    def build_info_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        info_text = (
            "Make sure you mapped your mouse keys 1-12 to Keyboard Functions->F13-F24 respectively.\n\n"
            "Pro Tip: Map extra mouse buttons to Ctrl and Shift to use shortcuts (e.g. Ctrl+C) and type capital letters easily."
        )

        lbl = tk.Label(frame, text=info_text, justify="left", font=("Roboto", 11), bg="#f0f0f0", padx=10, pady=10)
        lbl.pack(fill="x", pady=10)
        
        lbl.bind('<Configure>', lambda e: lbl.config(wraplength=frame.winfo_width()-40))

    def build_main_tab(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        lf_time = ttk.LabelFrame(frame, text="Typing Speed (Delay)", padding=10)
        lf_time.pack(fill="x", pady=10)
        
        self.lbl_time_val = ttk.Label(lf_time, text=f"{self.delay_var.get()} ms")
        self.lbl_time_val.pack()
        
        scale = ttk.Scale(lf_time, from_=200, to=2000, variable=self.delay_var, command=self.on_delay_change)
        scale.pack(fill="x", pady=5)

        lf_sys = ttk.LabelFrame(frame, text="System & Startup", padding=10)
        lf_sys.pack(fill="x", pady=10)
        
        chk_tray = ttk.Checkbutton(
            lf_sys, 
            text="Minimize to tray on close (X)", 
            variable=self.minimize_tray_var,
            command=self.save_settings
        )
        chk_tray.pack(anchor="w", pady=2)

        chk_startup = ttk.Checkbutton(
            lf_sys, 
            text="Run on Windows Startup", 
            variable=self.startup_var,
            command=self.toggle_startup
        )
        chk_startup.pack(anchor="w", pady=2)

        btn_save = ttk.Button(frame, text="Save Configuration", command=self.save_settings)
        btn_save.pack(pady=20)

    def build_mapping_tab(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Click a key to edit characters.", font=("Roboto", 10, "italic")).pack(pady=(0, 15))

        grid_container = ttk.Frame(frame)
        grid_container.pack(expand=True, fill="both") 

        grid_container.columnconfigure(tuple(range(3)), weight=1, uniform="keys")
        grid_container.rowconfigure(tuple(range(4)), weight=1, uniform="keys")

        self.map_keys = {}

        layout = [
            ('f13', 0, 0, 1), ('f14', 0, 1, 2), ('f15', 0, 2, 3),
            ('f16', 1, 0, 4), ('f17', 1, 1, 5), ('f18', 1, 2, 6),
            ('f19', 2, 0, 7), ('f20', 2, 1, 8), ('f21', 2, 2, 9),
            ('f22', 3, 0, 10), ('f23', 3, 1, 11), ('f24', 3, 2, 12)
        ]

        for key_code, r, c, num in layout:
            chars = self.config_data["mapping"].get(key_code, [])
            key_widget = PhoneKey(
                grid_container, 
                number=num, 
                chars=chars, 
                command=lambda k=key_code, n=num: self.edit_mapping(k, n)
            )
            key_widget.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            self.map_keys[key_code] = key_widget

    def toggle_startup(self):
        state = self.startup_var.get()
        success = SystemUtils.set_startup(state)
        if success:
            self.config_data["run_on_startup"] = state
            ConfigManager.save(self.config_data)
        else:
            messagebox.showerror("Registry Error", "Could not update startup registry key.\nTry running as Administrator.")
            self.startup_var.set(not state)

    def edit_mapping(self, key, label_num):
        current_list = self.config_data["mapping"].get(key, [])
        current_str = ",".join(current_list)
        
        new_str = simpledialog.askstring(
            f"Edit Key {label_num}",
            "Enter characters separated by commas:\n(e.g., a,b,c)",
            initialvalue=current_str,
            parent=self
        )
        
        if new_str is not None:
            new_list = [x.strip() for x in new_str.split(',') if x.strip()]
            self.config_data["mapping"][key] = new_list
            self.save_settings()
            self.map_keys[key].update_chars(new_list)
            self.engine.update_mapping(self.config_data["mapping"])

    def on_delay_change(self, val):
        val = int(float(val))
        self.lbl_time_val.config(text=f"{val} ms")
        self.config_data["delay"] = val

    def save_settings(self):
        self.config_data["delay"] = self.delay_var.get()
        self.config_data["minimize_to_tray_on_close"] = self.minimize_tray_var.get()
        ConfigManager.save(self.config_data)
        self.update_status("Settings saved.")

    def update_status(self, text):
        self.lbl_status.config(text=text)

    def on_close_window(self):
        if self.minimize_tray_var.get():
            self.withdraw()
            self.tray_icon.notify("App is running in the background", "Mouse T9 Keypad")
        else:
            self.force_quit()

    def force_quit(self):
        try:
            keyboard.unhook_all()
        except: pass
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    # Single Instance Check
    mutex_name = "MouseT9Keypad_Mutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(0, "The application is already running.", "Mouse T9 Keypad", 0x30)
        sys.exit()

    app = SettingsApp()
    app.mainloop()
