"""
ITV1050 5-Channel Pressure Controller — Python GUI
Connect to ESP32 WiFi server and control all 5 channels remotely
Install: pip install requests
(tkinter ships with standard Python on Windows/Mac; on Linux: sudo apt install python3-tk)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time

# ============================================================
# CONFIGURATION
# ============================================================
ESP32_IP   = "192.168.0.200"    # ESP32 static IP — matches esp32_bridge_5ch.ino
ESP32_PORT = 80
POLL_INTERVAL = 0.5             # seconds between status updates
NUM_CH = 5

BASE_URL = f"http://{ESP32_IP}:{ESP32_PORT}"

CHANNEL_COLORS = ["#00ff88", "#ffaa00", "#4488ff", "#ff44aa", "#aaff00"]

# ============================================================
# SINGLE CHANNEL PANEL (one per tab)
# ============================================================
class ChannelPanel:
    def __init__(self, parent, gui, ch):
        self.gui = gui
        self.ch = ch
        color = CHANNEL_COLORS[ch % len(CHANNEL_COLORS)]

        self.frame = tk.Frame(parent, bg="#0f1117")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.setpoint_kpa = tk.DoubleVar(value=0)

        tk.Label(self.frame, text=f"CHANNEL {ch}", font=("Courier", 18, "bold"),
                 bg="#0f1117", fg=color).pack(pady=(20, 10))

        tk.Label(self.frame, text="SET PRESSURE (kPa)", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack()

        self.slider = tk.Scale(self.frame, from_=5, to=900,
                                orient=tk.HORIZONTAL, length=420,
                                variable=self.setpoint_kpa,
                                bg="#0f1117", fg=color,
                                troughcolor="#1a1d26", highlightthickness=0,
                                font=("Courier", 9), resolution=1,
                                command=self._slider_moved)
        self.slider.pack(pady=5)

        input_frame = tk.Frame(self.frame, bg="#0f1117")
        input_frame.pack(pady=5)
        tk.Label(input_frame, text="Enter kPa (5-900):", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack(side=tk.LEFT, padx=5)
        self.kpa_entry = tk.Entry(input_frame, font=("Courier", 13), width=8,
                                   bg="#1a1d26", fg="#ffffff", insertbackground="white",
                                   relief=tk.FLAT, bd=4, justify=tk.CENTER)
        self.kpa_entry.pack(side=tk.LEFT, padx=5)
        self.kpa_entry.bind("<Return>", self._entry_submitted)

        tk.Button(self.frame, text="SEND SETPOINT", font=("Courier", 13, "bold"),
                  bg=color, fg="#000000", relief=tk.FLAT,
                  padx=20, pady=10, cursor="hand2",
                  command=self._send_setpoint).pack(pady=15)

        tk.Frame(self.frame, height=1, bg="#222233").pack(fill=tk.X, padx=30, pady=5)

        tk.Label(self.frame, text="LIVE DATA", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack(pady=(10, 5))

        data_frame = tk.Frame(self.frame, bg="#1a1d26", padx=20, pady=15)
        data_frame.pack(padx=30, fill=tk.X)

        self.actual_kpa = tk.StringVar(value="--")
        self.pwm_duty = tk.StringVar(value="--")

        tk.Label(data_frame, text="Actual Pressure:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=0, column=0, sticky=tk.W, pady=5)
        tk.Label(data_frame, textvariable=self.actual_kpa, font=("Courier", 16, "bold"),
                 bg="#1a1d26", fg=color).grid(row=0, column=1, padx=20)
        tk.Label(data_frame, text="kPa", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=0, column=2, sticky=tk.W)

        tk.Label(data_frame, text="PWM Duty:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=1, column=0, sticky=tk.W, pady=5)
        tk.Label(data_frame, textvariable=self.pwm_duty, font=("Courier", 16, "bold"),
                 bg="#1a1d26", fg="#ffaa00").grid(row=1, column=1, padx=20)
        tk.Label(data_frame, text="/ 255", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=1, column=2, sticky=tk.W)

        tk.Label(data_frame, text="Setpoint:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.setpoint_display = tk.Label(data_frame, text="0", font=("Courier", 16, "bold"),
                                          bg="#1a1d26", fg="#4488ff")
        self.setpoint_display.grid(row=2, column=1, padx=20)
        tk.Label(data_frame, text="kPa", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=2, column=2, sticky=tk.W)

        tk.Button(self.frame, text=f"STOP CH{ch} (0 kPa)", font=("Courier", 11, "bold"),
                  bg="#ff2244", fg="#ffffff", relief=tk.FLAT,
                  padx=15, pady=8, cursor="hand2",
                  command=self._emergency_stop).pack(pady=15)

    def _slider_moved(self, val):
        self.kpa_entry.delete(0, tk.END)
        self.kpa_entry.insert(0, str(int(float(val))))

    def _entry_submitted(self, event):
        self._send_setpoint()

    def _send_setpoint(self):
        try:
            val_str = self.kpa_entry.get().strip()
            val = float(val_str) if val_str else self.setpoint_kpa.get()

            if val < 5 or val > 900:
                messagebox.showerror("Invalid", "Pressure must be between 5 and 900 kPa")
                return

            self.setpoint_kpa.set(val)
            self.setpoint_display.config(text=str(int(val)))
            threading.Thread(target=self.gui.post_setpoint,
                              args=(self.ch, val), daemon=True).start()
        except ValueError:
            messagebox.showerror("Invalid", "Please enter a valid number")

    def _emergency_stop(self):
        self.setpoint_kpa.set(0)
        self.kpa_entry.delete(0, tk.END)
        self.kpa_entry.insert(0, "0")
        self.setpoint_display.config(text="0")
        threading.Thread(target=self.gui.post_setpoint,
                          args=(self.ch, 0), daemon=True).start()

    def update_live(self, actual, duty, setpoint):
        self.actual_kpa.set(str(actual))
        self.pwm_duty.set(str(duty))
        self.setpoint_display.config(text=str(setpoint))


# ============================================================
# MAIN GUI CLASS
# ============================================================
class PressureControlGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("ITV1050 5-Channel Pressure Controller")
        self.root.geometry("560x760")
        self.root.configure(bg="#0f1117")
        self.root.resizable(False, False)

        self.status_text = tk.StringVar(value="Disconnected")
        self.connected = False
        self.polling = False
        self.panels = []

        self._build_ui()
        self._start_polling()

    # --------------------------------------------------------
    def _build_ui(self):
        root = self.root

        tk.Label(root, text="ITV1050 x5", font=("Courier", 26, "bold"),
                 bg="#0f1117", fg="#00ff88").pack(pady=(20, 0))
        tk.Label(root, text="5-Channel Pressure Controller", font=("Courier", 12),
                 bg="#0f1117", fg="#555566").pack(pady=(0, 10))

        self.status_label = tk.Label(root, textvariable=self.status_text,
                                      font=("Courier", 11), bg="#0f1117", fg="#ff4444")
        self.status_label.pack(pady=(0, 5))

        ip_frame = tk.Frame(root, bg="#0f1117")
        ip_frame.pack(pady=5)
        tk.Label(ip_frame, text="ESP32 IP:", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(ip_frame, font=("Courier", 11), width=16,
                                  bg="#1a1d26", fg="#ffffff", insertbackground="white",
                                  relief=tk.FLAT, bd=4)
        self.ip_entry.insert(0, ESP32_IP)
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(ip_frame, text="Connect", font=("Courier", 10),
                  bg="#00ff88", fg="#000000", relief=tk.FLAT, padx=8,
                  command=self._update_ip).pack(side=tk.LEFT, padx=5)

        # Global emergency stop for ALL channels
        tk.Button(root, text="STOP ALL CHANNELS (0 kPa)", font=("Courier", 11, "bold"),
                  bg="#ff2244", fg="#ffffff", relief=tk.FLAT,
                  padx=15, pady=6, cursor="hand2",
                  command=self._stop_all).pack(pady=8)

        # Style the notebook to fit the dark theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background="#0f1117", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a1d26", foreground="#aaaaaa",
                         font=("Courier", 11, "bold"), padding=[14, 6])
        style.map("TNotebook.Tab", background=[("selected", "#0f1117")],
                   foreground=[("selected", "#00ff88")])

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for ch in range(NUM_CH):
            tab = tk.Frame(notebook, bg="#0f1117")
            notebook.add(tab, text=f" CH{ch} ")
            panel = ChannelPanel(tab, self, ch)
            self.panels.append(panel)

        tk.Label(root, text="ITV1050-312N2 x5 | 0.005-0.9 MPa | 0-10V",
                 font=("Courier", 9), bg="#0f1117", fg="#333344").pack(pady=5)

    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------
    def _update_ip(self):
        global BASE_URL
        new_ip = self.ip_entry.get().strip()
        BASE_URL = f"http://{new_ip}:{ESP32_PORT}"
        self.status_text.set(f"Trying {new_ip}...")
        self.status_label.config(fg="#ffaa00")

    def _stop_all(self):
        for ch in range(NUM_CH):
            self.panels[ch]._emergency_stop()

    def post_setpoint(self, ch, val):
        try:
            r = requests.post(f"{BASE_URL}/set/{ch}", data=str(val), timeout=3)
            if r.status_code == 200:
                self.root.after(0, lambda: self.status_text.set(
                    f"CH{ch} set {int(val)} kPa - OK"))
                self.root.after(0, lambda: self.status_label.config(fg="#00ff88"))
            else:
                self.root.after(0, lambda: self.status_text.set(f"CH{ch}: error from ESP32"))
                self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))
        except Exception:
            self.root.after(0, lambda: self.status_text.set("Connection failed"))
            self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))

    # --------------------------------------------------------
    # POLLING (single /status call updates all 5 tabs)
    # --------------------------------------------------------
    def _start_polling(self):
        self.polling = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while self.polling:
            try:
                r = requests.get(f"{BASE_URL}/status", timeout=2)
                if r.status_code == 200:
                    data = r.json()
                    channels = data.get("channels", [])
                    for ch, cdata in enumerate(channels):
                        if ch >= NUM_CH:
                            break
                        actual = round(cdata.get("actual_kpa", 0), 1)
                        duty = cdata.get("pwm_duty", 0)
                        setp = round(cdata.get("setpoint_kpa", 0), 1)
                        self.root.after(0, self.panels[ch].update_live, actual, duty, setp)

                    if not self.connected:
                        self.connected = True
                        self.root.after(0, lambda: self.status_text.set("Connected"))
                        self.root.after(0, lambda: self.status_label.config(fg="#00ff88"))
            except Exception:
                if self.connected:
                    self.connected = False
                    self.root.after(0, lambda: self.status_text.set("Disconnected"))
                    self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))
                    for p in self.panels:
                        self.root.after(0, p.update_live, "--", "--", "--")

            time.sleep(POLL_INTERVAL)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = PressureControlGUI(root)
    root.mainloop()