
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn.metrics import (
    roc_curve, precision_recall_curve, auc,
    fbeta_score, accuracy_score, precision_score, recall_score,
    confusion_matrix, classification_report,
)
from pathlib import Path

from .config import (
    OUTPUT_DIR, MODEL_KERAS, CSV_RESULTS, FIG_ROC, FIG_PR,
    RANDOM_SEED, N_FEATURES, CLIENTS,
)
from .preprocess import load_dataset
from .model_autoencoder import build_autoencoder

np.random.seed(RANDOM_SEED)


def main():
    # Load data and model
    X_train, X_test, y_train, y_test = load_dataset()
    input_dim = X_train.shape[1]

    model = tf.keras.models.load_model(MODEL_KERAS.as_posix())

    # Train normals MSE for threshold
    train_norm = X_train[y_train == 0]
    recon_train = model.predict(train_norm, verbose=0)
    train_mse = np.mean((train_norm - recon_train)**2, axis=1)

    # Test MSE
    recon_test = model.predict(X_test, verbose=0)
    err_test   = np.mean((X_test - recon_test)**2, axis=1)

    # Find best threshold by maximizing F2
    quantiles = np.linspace(0.80, 0.99, 40)
    best = None
    for q in quantiles:
        thr = np.quantile(train_mse, q)
        y_pred_tmp = (err_test > thr).astype(int)
        f2 = fbeta_score(y_test, y_pred_tmp, beta=2)
        if best is None or f2 > best[1]:
            best = (q, thr, f2)

    seuil_opt = best[1]
    y_pred = (err_test > seuil_opt).astype(int)

    # ROC/PR
    fpr, tpr, _ = roc_curve(y_test, err_test)
    precision, recall, _ = precision_recall_curve(y_test, err_test)
    roc_auc = auc(fpr, tpr)
    pr_auc  = auc(recall, precision)

    acc  = accuracy_score(y_test, y_pred)
    rec  = recall_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    f2   = fbeta_score(y_test, y_pred, beta=2)

    print(f"Seuil optimal: {seuil_opt:.6f} | F2={f2:.4f}")
    print(f"Accuracy={acc:.4f} Recall={rec:.4f} Precision={prec:.4f} ROC-AUC={roc_auc:.4f} PR-AUC={pr_auc:.4f}")
    print(confusion_matrix(y_test, y_pred))
    print(classification_report(y_test, y_pred, target_names=["Normal","Anormal"]))

    # Save results CSV
    out_csv = OUTPUT_DIR / 'results_eval.csv'
    pd.DataFrame({
        'seuil_opt':[seuil_opt], 'F2':[f2], 'Accuracy':[acc], 'Recall':[rec], 'Precision':[prec],
        'ROC_AUC':[roc_auc], 'PR_AUC':[pr_auc]
    }).to_csv(out_csv.as_posix(), index=False)

    # Save figures
    plt.figure(figsize=(6,4))
    plt.plot(fpr, tpr, label=f"ROC AUC={roc_auc:.3f}")
    plt.plot([0,1],[0,1],'k--',alpha=0.3)
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.title("Courbe ROC"); plt.legend(); plt.tight_layout(); plt.savefig(FIG_ROC.as_posix(), dpi=200)

    plt.figure(figsize=(6,4))
    plt.plot(recall, precision, label=f"PR AUC={pr_auc:.3f}")
    plt.xlabel("Recall"); plt.ylabel("Precision")
    plt.title("Courbe Precision–Recall"); plt.legend(); plt.tight_layout(); plt.savefig(FIG_PR.as_posix(), dpi=200)

    print(f"Saved: {out_csv}")
    print(f"Saved: {FIG_ROC}")
    print(f"Saved: {FIG_PR}")


if __name__ == "__main__":
    main()
