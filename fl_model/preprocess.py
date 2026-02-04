
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
from .config import (
    CSV_PATH, USE_SYNTHETIC_IF_MISSING, N_SAMPLES_SYNTH,
    N_FEATURES, TEST_RATIO, RANDOM_SEED, SCALER_PKL, OUTPUT_DIR
)

np.random.seed(RANDOM_SEED)


def _generate_synthetic_ecg(n_samples: int, n_features: int):
    X, y = [], []
    for _ in range(n_samples):
        t = np.linspace(0, 2*np.pi, n_features)
        base = np.sin(3*t) + 0.1*np.random.randn(n_features)
        p   = np.exp(-((t-0.8)**2)/(2*0.03)) * 0.5
        qrs = np.exp(-((t-1.2)**2)/(2*0.02)) * -1.5
        s   = np.exp(-((t-1.35)**2)/(2*0.01)) * 0.8
        ecg = base + p + qrs + s
        is_anom = np.random.rand() < 0.35
        if is_anom:
            idx = np.random.choice(n_features, size=np.random.randint(3,8), replace=False)
            ecg[idx] += np.random.uniform(1.2,2.0,size=idx.shape)
            y.append(1)
        else:
            y.append(0)
        X.append(ecg)
    X = np.array(X).astype(np.float32)
    y = np.array(y).astype(np.int32)
    return X, y


def load_dataset():
    # Decide between CSV or synthetic
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        X = df.iloc[:, :N_FEATURES].values.astype(np.float32)
        y = df.iloc[:, -1].values.astype(np.int32)
        print(f"Dataset loaded from {CSV_PATH} → X: {X.shape}, y: {y.shape}")
    else:
        if USE_SYNTHETIC_IF_MISSING:
            X, y = _generate_synthetic_ecg(N_SAMPLES_SYNTH, N_FEATURES)
            print(f"Synthetic dataset generated → X: {X.shape}, y: {y.shape}")
        else:
            raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    # MinMax scaling
    scaler = MinMaxScaler()
    X_norm = scaler.fit_transform(X)

    # Save scaler for later reproducibility
    try:
        import joblib
        joblib.dump(scaler, SCALER_PKL)
    except Exception as e:
        print(f"[WARN] Could not save scaler: {e}")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_norm, y, test_size=TEST_RATIO, stratify=y, random_state=RANDOM_SEED
    )
    return X_train, X_test, y_train, y_test


def make_noniid_clients(X_train, y_train, clients: int):
    indices = np.arange(len(X_train))
    np.random.shuffle(indices)
    shards = np.array_split(indices, clients)
    client_data = {}
    for cid, shard in enumerate(shards):
        Xc = X_train[shard]
        yc = y_train[shard]
        # Non-IID bias
        if cid % 2 == 0:
            mask = (yc == 0) | (np.random.rand(len(yc)) < 0.2)
        else:
            mask = (yc == 1) | (np.random.rand(len(yc)) < 0.2)
        Xc = Xc[mask]
        yc = yc[mask]
        client_data[cid] = (Xc, yc)
    return client_data
