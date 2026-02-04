
# -*- coding: utf-8 -*-
"""
plot_kpi.py — Lit pret_grapher.csv et génère 3 barplots (Énergie / Réseau / Temps),
puis exporte des PNG prêts à insérer dans une présentation.

Utilisation (terminal) :
    python plot_kpi.py --csv pret_grapher.csv --out .

Arguments :
    --csv : chemin vers le CSV (par défaut: pret_grapher.csv)
    --out : dossier de sortie pour les PNG (par défaut: .)

Pré‑requis :
    pip install pandas matplotlib
"""

import os
import argparse
import locale
import pandas as pd
import matplotlib.pyplot as plt

# --- pour un rendu lisible (tu peux changer le style si tu veux) ---
plt.style.use("seaborn-v0_8-whitegrid")

def read_csv_safely(csv_path: str) -> pd.DataFrame:
    """
    Lit le CSV en essayant d'être tolérant (virgules/décimales).
    Le fichier attendu contient : scenario,energy_j,network_kb,exec_time_ms
    """
    # Essai direct (séparateur virgule)
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        # Si ton système est FR et que tu as des décimales avec virgule, Panda sait généralement gérer,
        # mais si besoin tu peux forcer un parse pour remplacer des virgules décimales :
        with open(csv_path, "r", encoding="utf-8") as f:
            txt = f.read().replace(";", ",")
        from io import StringIO
        df = pd.read_csv(StringIO(txt))
    # Normalisation des colonnes attendues
    expected = ["scenario", "energy_j", "network_kb", "exec_time_ms"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans {csv_path} : {missing}\n"
                         f"Colonnes trouvées : {list(df.columns)}")
    return df

def thousand_fmt(x):
    """ Formate avec un séparateur de milliers, sans décimales superflues. """
    try:
        # format français : espace insécable pour les milliers
        return f"{x:,.0f}".replace(",", " ").replace("\xa0", " ")
    except Exception:
        return str(x)

def add_value_labels(ax, fmt="{:.0f}", y_offset=0.01):
    """
    Ajoute les valeurs au-dessus des barres.
    y_offset est une fraction de la hauteur max pour espacer le texte.
    """
    ymin, ymax = ax.get_ylim()
    dy = (ymax - ymin) * y_offset
    for p in ax.patches:
        height = p.get_height()
        if height is None:
            continue
        ax.text(
            p.get_x() + p.get_width() / 2.0,
            height + dy,
            fmt.format(height),
            ha="center", va="bottom", fontsize=9
        )

def plot_single_bar(df, col, title, ylabel, out_png):
    """
    Génère un barplot simple (scenario vs col) et l’enregistre en PNG.
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    x = df["scenario"]
    y = df[col].astype(float)

    bars = ax.bar(x, y, color=["#4C78A8", "#F58518", "#54A24B"])
    ax.set_title(title, fontsize=12, weight="bold")
    ax.set_xlabel("Scénario")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)

    # Jolis ticks (milliers)
    ax.set_yticklabels([thousand_fmt(t) for t in ax.get_yticks()])

    # Valeurs au-dessus des barres
    # Format : énergie -> entier ; réseau -> entier ; temps -> entier
    add_value_labels(ax, fmt="{:.0f}")

    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[OK] Export : {out_png}")

def plot_dashboard(df, out_png):
    """
    Génère un “dashboard” 3 sous‑graphiques (Énergie / Réseau / Temps) dans un seul PNG.
    """
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    specs = [
        ("energy_j", "Énergie totale (J)", "Énergie (J)"),
        ("network_kb", "Trafic (proxy) réseau", "Réseau (KB)"),
        ("exec_time_ms", "Temps d’exécution", "Temps (ms)")
    ]

    colors = ["#4C78A8", "#F58518", "#54A24B"]

    for i, (col, title, ylabel) in enumerate(specs):
        ax = axes[i]
        y = df[col].astype(float)
        ax.bar(df["scenario"], y, color=colors[i])
        ax.set_title(title, fontsize=12, weight="bold")
        ax.set_xlabel("Scénario")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.set_yticklabels([thousand_fmt(t) for t in ax.get_yticks()])
        add_value_labels(ax, fmt="{:.0f}", y_offset=0.015)

    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[OK] Export : {out_png}")

def main():
    parser = argparse.ArgumentParser(description="Tracer les KPI Edge/Fog/Cloud depuis pret_grapher.csv")
    parser.add_argument("--csv", default="pret_grapher.csv", help="Chemin vers le CSV (défaut: pret_grapher.csv)")
    parser.add_argument("--out", default=".", help="Dossier de sortie des PNG (défaut: .)")
    args = parser.parse_args()

    csv_path = args.csv
    out_dir = args.out

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Fichier introuvable : {csv_path}")

    os.makedirs(out_dir, exist_ok=True)

    df = read_csv_safely(csv_path)

    # Tri par ordre EDGE, FOG, CLOUD si besoin (au cas où l'ordre serait différent)
    order = ["EDGE", "FOG", "CLOUD"]
    try:
        df["scenario"] = pd.Categorical(df["scenario"], categories=order, ordered=True)
        df = df.sort_values("scenario")
    except Exception:
        pass

    # Exports unitaires
    plot_single_bar(df, "energy_j", "Énergie totale consommée", "Énergie (J)", os.path.join(out_dir, "energie.png"))
    plot_single_bar(df, "network_kb", "Trafic réseau (proxy)", "Réseau (KB)", os.path.join(out_dir, "reseau.png"))
    plot_single_bar(df, "exec_time_ms", "Temps d’exécution global", "Temps (ms)", os.path.join(out_dir, "temps.png"))

    # Export tableau de bord
    plot_dashboard(df, os.path.join(out_dir, "dashboard_kpi.png"))

if __name__ == "__main__":
    main()
