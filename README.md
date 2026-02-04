
# FedSDM-Project (VS Code Ready)

This repo contains a **ready-to-run Federated Learning pipeline** (Flower + Keras Autoencoder)
plus evaluation scripts and a minimal folder to host your iFogSim2 Java scenario.

## Quick Start (VS Code)

1. **Install Python 3.10/3.11** and **VS Code**.
2. Open this folder in VS Code.
3. Create & activate a **virtual environment**:

   ### macOS/Linux
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
   ### Windows (PowerShell)
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. **Install deps**:
   ```bash
   pip install -r requirements.txt
   ```
   > If TensorFlow GPU fails on your machine, comment `tensorflow==2.14.0` and use `tensorflow-cpu==2.14.0`.

5. **Prepare your ECG dataset**: place your CSV at `fl_model/data/ecg.csv` (140 feature columns + last label column {0,1}).
   If you don’t have a dataset yet, the scripts can generate synthetic data (see `config.py`).

6. **Run training (Flower + AE)**:
   ```bash
   python -m fl_model.train_fl
   ```

7. **Run evaluation & plots**:
   ```bash
   python -m fl_model.evaluate_fl
   ```

Generated files will appear under `fl_model/results/`:
- `autoencoder_fed_global.keras` (model)  
- `roc_curve.png`, `pr_curve.png` (figures)  
- `results_fedsdm.csv` (metrics)  

## iFogSim2 (Java) Integration
Use the `ifogsim` folder to store your Java class (e.g. `FedSDM_KPI_Batch.java`). Compile & run it separately in your Java IDE.
It will generate `pret_a_grapher.csv` with KPIs for Edge/Fog/Cloud scenarios.

## Structure
```
FedSDM-Project/
 ├─ requirements.txt
 ├─ fl_model/
 │   ├─ __init__.py
 │   ├─ config.py
 │   ├─ preprocess.py
 │   ├─ model_autoencoder.py
 │   ├─ client_flower.py
 │   ├─ server_strategy.py
 │   ├─ train_fl.py
 │   └─ evaluate_fl.py
 ├─ ifogsim/
 └─ presentation/
```

## Notes
- Flower version pinned to `1.3.0` to avoid protobuf API conflicts.
- TensorFlow pinned to `2.14.0` (use CPU-only build if needed).
- Evaluation optimizes anomaly threshold using F2-score, then generates ROC/PR.
