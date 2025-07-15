import customtkinter as ctk
import threading
import time
from pynput import mouse, keyboard
import pydirectinput

# Pengaturan Global
pydirectinput.PAUSE = 0
pydirectinput.FAILSAFE = False

events = []
is_recording = False
is_playing = False
mouse_listener = None
keyboard_listener = None

# --- FUNGSI PEREKAMAN (High-Fidelity) ---

def record_event(event_type, details):
    if is_recording:
        last_time = events[-1][2] if events else time.time()
        events.append((event_type, details, time.time()))

def on_move(x, y):
    record_event('mouse_move', (x, y))

def on_click(x, y, button, pressed):
    action = 'pressed' if pressed else 'released'
    record_event('mouse_click', (x, y, button, action))

def on_scroll(x, y, dx, dy):
    record_event('mouse_scroll', (x, y, dx, dy))

def on_press(key):
    record_event('key_press', key)

def on_release(key):
    record_event('key_release', key)

def start_recording():
    global is_recording, events, mouse_listener, keyboard_listener
    if is_recording: return
    
    is_recording = True
    events = []
    app.status_label.configure(text="Status: Merekam...", text_color="red")
    events.append(('start', None, time.time()))
    
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    mouse_listener.start()
    keyboard_listener.start()

def stop_recording():
    global is_recording, mouse_listener, keyboard_listener
    if not is_recording: return
    
    is_recording = False
    if mouse_listener: mouse_listener.stop()
    if keyboard_listener: keyboard_listener.stop()
    app.status_label.configure(text=f"Status: Siap ({len(events)} aksi direkam)", text_color="green")

# --- FUNGSI PEMUTARAN ULANG (Dengan Fitur Baru) ---

def playback_thread():
    global is_playing
    
    # Fungsi inti untuk memutar satu siklus rekaman
    def play_one_cycle():
        try:
            speed_multiplier = float(app.speed_entry.get())
            if speed_multiplier <= 0: speed_multiplier = 1.0
        except ValueError:
            speed_multiplier = 1.0

        keyboard_controller = keyboard.Controller()
        start_playback_time = time.time()
        start_record_time = events[0][2]

        for i in range(1, len(events)):
            if not is_playing: break # Berhenti jika user menekan tombol stop

            event_type, details, record_time = events[i]
            time_since_start_record = record_time - start_record_time
            target_playback_time = start_playback_time + (time_since_start_record / speed_multiplier)
            
            sleep_duration = target_playback_time - time.time()
            if sleep_duration > 0:
                time.sleep(sleep_duration)
            
            if not is_playing: break # Cek lagi setelah sleep

            if event_type == 'mouse_move':
                pydirectinput.moveTo(details[0], details[1])
            elif event_type == 'mouse_click':
                x, y, button, action = details
                button_str = 'left' if button == mouse.Button.left else 'right' if button == mouse.Button.right else 'middle'
                pydirectinput.moveTo(x, y)
                if action == 'pressed': pydirectinput.mouseDown(button=button_str)
                else: pydirectinput.mouseUp(button=button_str)
            elif event_type == 'mouse_scroll':
                x, y, dx, dy = details
                pydirectinput.moveTo(x, y)
                pydirectinput.scroll(dy * -1)
            elif event_type == 'key_press':
                keyboard_controller.press(details)
            elif event_type == 'key_release':
                keyboard_controller.release(details)
    
    # Logika utama: periksa apakah continuous playback aktif
    is_continuous = app.continuous_playback_checkbox.get() == 1
    
    if is_continuous:
        while is_playing: # Loop akan berjalan terus selama is_playing True
            app.status_label.configure(text="Status: Memutar (Berulang)...", text_color="cyan")
            play_one_cycle()
            if not is_playing: break # Berhenti jika user stop di tengah siklus
    else:
        app.status_label.configure(text="Status: Memutar (Satu Kali)...", text_color="cyan")
        play_one_cycle()

    # Setelah selesai (baik karena selesai atau dihentikan)
    is_playing = False
    app.status_label.configure(text="Status: Siap", text_color="green")

def start_playback():
    global is_playing
    if is_playing or not events: return
    is_playing = True
    threading.Thread(target=playback_thread, daemon=True).start()

def stop_playback():
    global is_playing
    is_playing = False # Ini akan menghentikan loop di playback_thread

# --- KELAS ANTARMUKA APLIKASI (GUI) ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("High-Fidelity Macro")
        self.geometry("380x330") # Sedikit lebih tinggi untuk checkbox baru
        ctk.set_appearance_mode("dark")

        self.grid_columnconfigure(0, weight=1)
        
        self.record_button = ctk.CTkButton(self, text="🎙️ Rekam/Berhenti (F8)", command=self.toggle_recording)
        self.record_button.grid(row=0, column=0, padx=20, pady=5, sticky="ew")
        
        # **PERUBAHAN DISINI**
        self.play_button = ctk.CTkButton(self, text="▶️ Putar/Berhenti (Ctrl+Shift+Alt+P)", command=self.toggle_playback)
        self.play_button.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        speed_frame = ctk.CTkFrame(self)
        speed_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        speed_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(speed_frame, text="Kecepatan:").grid(row=0, column=0, padx=10, pady=5)
        self.speed_entry = ctk.CTkEntry(speed_frame, placeholder_text="Contoh: 1.0, 1.25")
        self.speed_entry.insert(0, "1.0")
        self.speed_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")
        
        # **FITUR BARU: CONTINUOUS PLAYBACK**
        self.continuous_playback_checkbox = ctk.CTkCheckBox(self, text="Pemutaran Berulang (Continuous)")
        self.continuous_playback_checkbox.grid(row=3, column=0, padx=20, pady=5, sticky="w")

        self.always_on_top_checkbox = ctk.CTkCheckBox(self, text="Selalu di Atas (Always on Top)", command=self.toggle_always_on_top)
        self.always_on_top_checkbox.grid(row=4, column=0, padx=20, pady=5, sticky="w")
        
        self.status_label = ctk.CTkLabel(self, text="Status: Siap", text_color="green", font=("Arial", 14))
        self.status_label.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        self.setup_hotkeys()

    def toggle_recording(self):
        if is_recording: stop_recording()
        else: start_recording()
    
    # **FUNGSI BARU: TOGGLE PLAYBACK**
    def toggle_playback(self):
        if is_playing:
            stop_playback()
        else:
            start_playback()
            
    def toggle_always_on_top(self):
        self.attributes("-topmost", self.always_on_top_checkbox.get())

    def setup_hotkeys(self):
        # **PERUBAHAN DISINI**
        hotkeys = {
            '<f8>': self.toggle_recording,
            '<ctrl>+<shift>+<alt>+p': self.toggle_playback, # Hotkey sekarang memanggil fungsi toggle
            '<f12>': self.stop_all
        }
        threading.Thread(target=lambda: keyboard.GlobalHotKeys(hotkeys).run(), daemon=True).start()

    def stop_all(self):
        stop_recording()
        stop_playback()

if __name__ == "__main__":
    app = App()
    app.mainloop()