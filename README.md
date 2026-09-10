# McKibben Pneumatic Muscle Gripper 🦾

An experimental and computational research project on **Pneumatic Artificial Muscles (PAMs)** — specifically the McKibben actuator — focusing on empirical characterisation, mathematical modeling, and application in a soft robotic gripper.

---

## 📌 Project Overview

McKibben artificial muscles contract radially and expand axially when pressurized, delivering high power-to-weight ratios and natural compliance similar to biological skeletal muscles.

This project covers:
1. **Experimental characterisation** of force-pressure-contraction profiles under static and dynamic loading.
2. **Dataset acquisition** across multiple pressure regimes.
3. **Actuator modeling** correlating input pneumatic pressure to output grip force.
4. **Soft gripper prototyping** utilizing McKibben muscles as flexible finger actuators.

---

## 🗂️ Repository Structure

```
Mckibben_gripper/
├── codes/              # Python & MATLAB scripts for data processing, fitting, and plots
├── collected_datasets/ # Raw and processed experimental pressure-displacement-force logs
├── images/             # Experimental setup photos, test rigs, and characterisation graphs
├── Reports/            # Technical reports, seminar slides, and project documentation
└── resources/          # Reference research papers, CAD files, and technical datasheets
```

---

## 🔬 Experimental Methodology

```
[ Compressor / Regulator ] ──► [ McKibben PAM ] ──► [ Load Cell & Position Sensor ]
                                     │
                                     ▼
                      [ Data Acquisition System ]
                                     │
                                     ▼
                    [ Numerical Modeling & Analysis ]
```

1. **Test Rig Setup:** Mount McKibben muscle with pressure transducers, load cells, and displacement sensors.
2. **Data Collection:** Vary air pressure systematically (0–6 bar) and record tensile force and contraction length.
3. **Constitutive Modeling:** Fit geometric braid angle relations and energy conservation models.
4. **Gripper Synthesis:** Incorporate tested muscles into multi-finger soft gripping mechanisms.

---

## 📊 Outputs & Findings

- Force vs. Pressure response curves across varying rest lengths
- Strain vs. Pressure non-linear hysteresis curves
- Grasp strength estimation for delicate and irregular object manipulation

---

## 🛠️ Tools & Technologies

- **Software:** Python (NumPy, SciPy, Matplotlib), MATLAB
- **Hardware:** McKibben braided pneumatic actuators, pneumatic valves/regulators, digital load cell instrumentation

---

## 👤 Author

**Prachi Jindal**  
Junior Undergraduate, Mechanical Engineering  
Indian Institute of Technology Gandhinagar (IITGN)
