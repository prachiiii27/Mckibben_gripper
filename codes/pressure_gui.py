"""
ITV1050 Pressure Controller — Python GUI
Connect to ESP32 WiFi server and control pressure remotely
Install: pip install requests tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time

# ============================================================
# CONFIGURATION
# ============================================================
ESP32_IP   = "192.168.0.200"    # ESP32 Access Point fixed IP — always this address
ESP32_PORT = 80
POLL_INTERVAL = 0.5            # seconds between status updates

BASE_URL = f"http://{ESP32_IP}:{ESP32_PORT}"

# ============================================================
# GUI CLASS
# ============================================================
class PressureControlGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("ITV1050 Pressure Controller")
        self.root.geometry("520x620")
        self.root.configure(bg="#0f1117")
        self.root.resizable(False, False)

        self.setpoint_kpa = tk.DoubleVar(value=0)
        self.actual_kpa   = tk.StringVar(value="--")
        self.pwm_duty     = tk.StringVar(value="--")
        self.status_text  = tk.StringVar(value="Disconnected")
        self.connected    = False
        self.polling      = False

        self._build_ui()
        self._start_polling()

    # --------------------------------------------------------
    # UI BUILDER
    # --------------------------------------------------------
    def _build_ui(self):
        root = self.root

        # Title
        tk.Label(root, text="ITV1050", font=("Courier", 28, "bold"),
                 bg="#0f1117", fg="#00ff88").pack(pady=(30, 0))
        tk.Label(root, text="Pressure Controller", font=("Courier", 12),
                 bg="#0f1117", fg="#555566").pack(pady=(0, 20))

        # Status bar
        self.status_label = tk.Label(root, textvariable=self.status_text,
                                     font=("Courier", 11), bg="#0f1117", fg="#ff4444")
        self.status_label.pack(pady=(0, 10))

        # IP entry
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

        # Separator
        tk.Frame(root, height=1, bg="#222233").pack(fill=tk.X, padx=30, pady=15)

        # SETPOINT SECTION
        tk.Label(root, text="SET PRESSURE (kPa)", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack()

        # Slider
        self.slider = tk.Scale(root, from_=5, to=900,
                                orient=tk.HORIZONTAL, length=400,
                                variable=self.setpoint_kpa,
                                bg="#0f1117", fg="#00ff88",
                                troughcolor="#1a1d26", highlightthickness=0,
                                font=("Courier", 9), resolution=1,
                                command=self._slider_moved)
        self.slider.pack(pady=5)

        # Manual input
        input_frame = tk.Frame(root, bg="#0f1117")
        input_frame.pack(pady=5)
        tk.Label(input_frame, text="Enter kPa (5–900):", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack(side=tk.LEFT, padx=5)
        self.kpa_entry = tk.Entry(input_frame, font=("Courier", 13), width=8,
                                   bg="#1a1d26", fg="#ffffff", insertbackground="white",
                                   relief=tk.FLAT, bd=4, justify=tk.CENTER)
        self.kpa_entry.pack(side=tk.LEFT, padx=5)
        self.kpa_entry.bind("<Return>", self._entry_submitted)

        # Send button
        tk.Button(root, text="SEND SETPOINT", font=("Courier", 13, "bold"),
                  bg="#00ff88", fg="#000000", relief=tk.FLAT,
                  padx=20, pady=10, cursor="hand2",
                  command=self._send_setpoint).pack(pady=15)

        # Separator
        tk.Frame(root, height=1, bg="#222233").pack(fill=tk.X, padx=30, pady=5)

        # LIVE DATA SECTION
        tk.Label(root, text="LIVE DATA", font=("Courier", 11),
                 bg="#0f1117", fg="#aaaaaa").pack(pady=(10, 5))

        data_frame = tk.Frame(root, bg="#1a1d26", padx=20, pady=15)
        data_frame.pack(padx=30, fill=tk.X)

        # Actual pressure
        tk.Label(data_frame, text="Actual Pressure:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=0, column=0, sticky=tk.W, pady=5)
        tk.Label(data_frame, textvariable=self.actual_kpa, font=("Courier", 16, "bold"),
                 bg="#1a1d26", fg="#00ff88").grid(row=0, column=1, padx=20)
        tk.Label(data_frame, text="kPa", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=0, column=2, sticky=tk.W)

        # PWM duty
        tk.Label(data_frame, text="PWM Duty:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=1, column=0, sticky=tk.W, pady=5)
        tk.Label(data_frame, textvariable=self.pwm_duty, font=("Courier", 16, "bold"),
                 bg="#1a1d26", fg="#ffaa00").grid(row=1, column=1, padx=20)
        tk.Label(data_frame, text="/ 255", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=1, column=2, sticky=tk.W)

        # Setpoint display
        tk.Label(data_frame, text="Setpoint:", font=("Courier", 11),
                 bg="#1a1d26", fg="#aaaaaa").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.setpoint_display = tk.Label(data_frame, text="0", font=("Courier", 16, "bold"),
                                          bg="#1a1d26", fg="#4488ff")
        self.setpoint_display.grid(row=2, column=1, padx=20)
        tk.Label(data_frame, text="kPa", font=("Courier", 11),
                 bg="#1a1d26", fg="#555566").grid(row=2, column=2, sticky=tk.W)

        # Emergency stop
        tk.Button(root, text="EMERGENCY STOP (0 kPa)", font=("Courier", 11, "bold"),
                  bg="#ff2244", fg="#ffffff", relief=tk.FLAT,
                  padx=15, pady=8, cursor="hand2",
                  command=self._emergency_stop).pack(pady=15)

        # Footer
        tk.Label(root, text="ITV1050-312N2 | 0.005–0.9 MPa | 0–10V",
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

    def _slider_moved(self, val):
        self.kpa_entry.delete(0, tk.END)
        self.kpa_entry.insert(0, str(int(float(val))))

    def _entry_submitted(self, event):
        self._send_setpoint()

    def _send_setpoint(self):
        # get value from entry or slider
        try:
            val_str = self.kpa_entry.get().strip()
            if val_str:
                val = float(val_str)
            else:
                val = self.setpoint_kpa.get()

            if val < 5 or val > 900:
                messagebox.showerror("Invalid", "Pressure must be between 5 and 900 kPa")
                return

            # update slider
            self.setpoint_kpa.set(val)
            self.setpoint_display.config(text=str(int(val)))

            # send to ESP32 in background thread
            threading.Thread(target=self._post_setpoint,
                             args=(val,), daemon=True).start()

        except ValueError:
            messagebox.showerror("Invalid", "Please enter a valid number")

    def _post_setpoint(self, val):
        try:
            r = requests.post(f"{BASE_URL}/set",
                              data=str(val),
                              timeout=3)
            if r.status_code == 200:
                self.root.after(0, lambda: self.status_text.set(
                    f"Set {int(val)} kPa — OK"))
                self.root.after(0, lambda: self.status_label.config(fg="#00ff88"))
            else:
                self.root.after(0, lambda: self.status_text.set("Error from ESP32"))
                self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))
        except Exception as e:
            self.root.after(0, lambda: self.status_text.set("Connection failed"))
            self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))

    def _emergency_stop(self):
        self.setpoint_kpa.set(0)
        self.kpa_entry.delete(0, tk.END)
        self.kpa_entry.insert(0, "0")
        self.setpoint_display.config(text="0")
        threading.Thread(target=self._post_setpoint,
                         args=(0,), daemon=True).start()

    # --------------------------------------------------------
    # POLLING
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
                    actual  = round(data.get("actual_kpa", 0), 1)
                    duty    = data.get("pwm_duty", 0)
                    setp    = round(data.get("setpoint_kpa", 0), 1)
                    self.root.after(0, lambda a=actual: self.actual_kpa.set(str(a)))
                    self.root.after(0, lambda d=duty: self.pwm_duty.set(str(d)))
                    self.root.after(0, lambda s=setp: self.setpoint_display.config(text=str(s)))
                    if not self.connected:
                        self.connected = True
                        self.root.after(0, lambda: self.status_text.set("Connected"))
                        self.root.after(0, lambda: self.status_label.config(fg="#00ff88"))
            except:
                if self.connected:
                    self.connected = False
                    self.root.after(0, lambda: self.status_text.set("Disconnected"))
                    self.root.after(0, lambda: self.status_label.config(fg="#ff4444"))
                    self.root.after(0, lambda: self.actual_kpa.set("--"))
                    self.root.after(0, lambda: self.pwm_duty.set("--"))

            time.sleep(POLL_INTERVAL)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = PressureControlGUI(root)
    root.mainloop()
