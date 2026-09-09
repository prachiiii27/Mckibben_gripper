"""
Automated F vs P Hysteresis Experiment
ESP32 (ITV1050) + FUTEK LCM300 load cell
"""

import serial
import requests
import time
import csv
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
ESP32_IP   = "192.168.0.200"
ESP32_PORT = 80
BASE_URL   = f"http://{ESP32_IP}:{ESP32_PORT}"

LOAD_CELL_PORT = "COM5"       # ← change this
BAUD           = 9600
LBS_TO_N       = 4.44822

STABILIZE_TIME = 40           # seconds to wait after setting pressure
SAMPLE_TIME    = 20           # seconds to collect load cell data

extension_steps  = [5, 20] + list(range(30, 230, 10))   # 5,20,30,40,...,220
retraction_steps = list(reversed(extension_steps))        # 220,...,30,20,5
# ============================================================
# HELPERS
# ============================================================
def parse_lbs(line):
    return float(line.replace('lbs', '').strip())

def set_pressure(kpa):
    """Send pressure setpoint to ESP32"""
    try:
        r = requests.post(f"{BASE_URL}/set", data=str(kpa), timeout=3)
        return r.status_code == 200
    except Exception as e:
        print(f"  [ESP32 ERROR] {e}")
        return False

def get_actual_pressure():
    """Poll actual pressure from ESP32"""
    try:
        r = requests.get(f"{BASE_URL}/status", timeout=2)
        if r.status_code == 200:
            return round(r.json().get("actual_kpa", 0), 1)
    except:
        pass
    return None

def countdown(label, seconds):
    """Visual countdown in terminal"""
    for remaining in range(seconds, 0, -1):
        actual = get_actual_pressure()
        actual_str = f"{actual} kPa" if actual is not None else "?"
        print(f"\r  {label} — {remaining:3d}s remaining | Actual: {actual_str}    ", end="")
        time.sleep(1)
    print()

def collect_force(ser, duration, zero_offset_lbs):
    readings = []
    t_end = time.time() + duration
    while time.time() < t_end:
        remaining = int(t_end - time.time())
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        try:
            val = parse_lbs(line)
            readings.append(val)
            force_N = (val - zero_offset_lbs) * LBS_TO_N
            print(f"\r  Collecting... {remaining:2d}s left | Force: {force_N:+.4f} N | n={len(readings)}", end="")
        except:
            pass
    print()
    if readings:
        avg_lbs = sum(readings) / len(readings)
        avg_N   = (avg_lbs - zero_offset_lbs) * LBS_TO_N
        std_N   = (sum((((x - zero_offset_lbs) * LBS_TO_N) - avg_N)**2 for x in readings) / len(readings))**0.5
        return avg_N, len(readings), std_N
    return None, 0, None

def countdown(label, seconds):
    for remaining in range(seconds, 0, -1):
        print(f"\r  {label} — {remaining:3d}s remaining    ", end="")
        time.sleep(1)
    print()

# ============================================================
# MAIN
# ============================================================
def run_experiment():
    # ── Serial init ──
    print("Connecting to load cell...")
    ser = serial.Serial(LOAD_CELL_PORT, baudrate=BAUD, timeout=2)
    time.sleep(2)
    print("✓ Load cell connected\n")

    # ── ESP32 check ──
    print("Checking ESP32 connection...")
    actual = get_actual_pressure()
    if actual is None:
        print("✗ ESP32 not reachable. Check WiFi connection to ESP32 AP.")
        ser.close()
        return
    print(f"✓ ESP32 connected | Actual pressure: {actual} kPa\n")

    # ── Zero calibration ──
    print("=" * 55)
    print("ZERO CALIBRATION")
    print("Setting pressure to 0 kPa...")
    set_pressure(0)
    time.sleep(3)
    print("Muscle fully slack. No load applied.")
    input("Press Enter when ready to tare → ")

    samples = []
    for _ in range(50):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        try:
            samples.append(parse_lbs(line))
        except:
            pass

    zero_offset_lbs = sum(samples) / len(samples)
    print(f"✓ Zero offset: {zero_offset_lbs:.5f} lbs = {zero_offset_lbs * LBS_TO_N:.4f} N\n")

    # ── CSV setup ──
    filename = f"FvsP_hysteresis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csvfile  = open(filename, 'w', newline='')
    writer   = csv.writer(csvfile)
    writer.writerow(["Phase", "Setpoint_kPa", "Force_N", "Std_N", "n_samples"])

    all_data = []

    # ── Run one phase ──
    def run_phase(steps, phase_name):
        print("\n" + "=" * 55)
        print(f"{phase_name} PHASE")
        print("=" * 55)

        for i, p in enumerate(steps):
            print(f"\n[{phase_name}] Step {i+1}/{len(steps)} → {p} kPa")

            # Set pressure
            ok = set_pressure(p)
            if not ok:
                print("  ✗ Failed to send setpoint, skipping...")
                continue

            # Stabilize
            countdown("Stabilizing", STABILIZE_TIME)

            # Collect
            avg_N, n, std_N = collect_force(ser, SAMPLE_TIME, zero_offset_lbs)
            actual_kpa = get_actual_pressure()

            if avg_N is not None:
                print(f"  ✓ Force: {avg_N:.4f} N ± {std_N:.4f} N | n={n}")
                writer.writerow([phase_name, p, round(avg_N,5), round(std_N,5), n])
                all_data.append((phase_name, p, avg_N))
                csvfile.flush()

    run_phase(extension_steps,  "Extension")
    run_phase(retraction_steps, "Retraction")

    # ── Shutdown ──
    set_pressure(0)
    csvfile.close()
    ser.close()

    print("\n" + "=" * 55)
    print(f"✓ EXPERIMENT COMPLETE")
    print(f"✓ Data saved to: {filename}")
    print("=" * 55)
    print(f"\n{'Phase':<12} {'Set(kPa)':>10} {'F(N)':>10}")
    print("-" * 35)
    for phase, sp, f in all_data:
        print(f"{phase:<12} {sp:>10.1f} {f:>10.4f}")

if __name__ == "__main__":
    run_experiment()