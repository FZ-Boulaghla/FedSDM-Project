import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.style.use("seaborn-v0_8-whitegrid")

FAMILIES = ["BASE", "NODES", "TRAFFIC", "LOAD", "MIPS"]
METRICS = [
    ("energy_j", "Energy Consumption (J)"),
    ("network_kb", "Network Traffic (KB)"),
    ("latency_ms", "Latency (ms)"), 
]


def thousand_fmt(x, pos=None):
    try:
        return f"{x:,.0f}".replace(",", " ").replace("\xa0", " ")
    except Exception:
        return str(x)

def parse_file_metadata(root, fullpath):
    rel = os.path.relpath(fullpath, root)
    parts = rel.split(os.sep)
    # parts[0] = family
    if len(parts) == 2:
        family = parts[0]               # ex. BASE
        level  = "BASE"
        layer  = os.path.splitext(parts[1])[0]  # EDGE/FOG/CLOUD
    else:
        family = parts[0]               # ex. NODES
        level  = parts[1]               # ex. SMALL
        layer  = os.path.splitext(parts[2])[0]
    return family, level, layer

def load_all_csv(root):
    rows = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith(".csv"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                df = pd.read_csv(full)
                if not set(["scenario","variant","energy_j","network_kb","latency_ms"]).issubset(df.columns):
                    print(f"[WARN] Colonnes manquantes dans {full}, ignoré.")
                    continue
                family, level, layer = parse_file_metadata(root, full)
                df["family"] = family
                df["level"] = level
                df["layer"] = layer
                rows.append(df)
            except Exception as e:
                print(f"[ERR] Lecture échouée {full}: {e}")
    if not rows:
        raise RuntimeError(f"Aucun CSV trouvé sous {root}")
    all_df = pd.concat(rows, ignore_index=True)
    # Types
    all_df["energy_j"] = pd.to_numeric(all_df["energy_j"], errors="coerce")
    all_df["network_kb"] = pd.to_numeric(all_df["network_kb"], errors="coerce")
    all_df["latency_ms"] = pd.to_numeric(all_df["latency_ms"], errors="coerce")
    return all_df

def plot_family_metric(df_family, family, metric, ylabel, outdir):
    """
    Barres groupées: x=layer (EDGE/FOG/CLOUD), couleurs = level
    """
    os.makedirs(outdir, exist_ok=True)
    pivot = df_family.pivot_table(index="layer", columns="level", values=metric, aggfunc="mean")
    pivot = pivot.reindex(index=["EDGE","FOG","CLOUD"])
    # ordonner colonnes si possible
    order_cols = None
    if family == "BASE":
        order_cols = ["BASE"]
    elif family == "NODES":
        order_cols = ["SMALL","MEDIUM","LARGE"]
    elif family in ("TRAFFIC","MIPS"):
        order_cols = ["LOW","MEDIUM","HIGH"]
    elif family == "LOAD":
        order_cols = ["LOW","NORMAL","HIGH"]
    if order_cols:
        existing = [c for c in order_cols if c in pivot.columns]
        pivot = pivot[existing]

    ax = pivot.plot(kind="bar", figsize=(7,4))
    ax.set_title(f"{family} — {ylabel}", fontsize=12, weight="bold")
    ax.set_xlabel("Layer")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.yaxis.set_major_formatter(FuncFormatter(thousand_fmt))

    # labels au-dessus des barres
    for p in ax.patches:
        height = p.get_height()
        if pd.notnull(height):
            ax.text(p.get_x() + p.get_width()/2, height, thousand_fmt(height), ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_png = os.path.join(outdir, f"{family.lower()}_{metric}.png")
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"[OK] Export: {out_png}")

def plot_family_dashboard(df_family, family, outdir):
    os.makedirs(outdir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12,4))
    for i, (metric, ylabel) in enumerate(METRICS):
        pivot = df_family.pivot_table(index="layer", columns="level", values=metric, aggfunc="mean")
        pivot = pivot.reindex(index=["EDGE","FOG","CLOUD"])
        # ordonner colonnes
        order_cols = None
        if family == "BASE":
            order_cols = ["BASE"]
        elif family == "NODES":
            order_cols = ["SMALL","MEDIUM","LARGE"]
        elif family in ("TRAFFIC","MIPS"):
            order_cols = ["LOW","MEDIUM","HIGH"]
        elif family == "LOAD":
            order_cols = ["LOW","NORMAL","HIGH"]
        if order_cols:
            existing = [c for c in order_cols if c in pivot.columns]
            pivot = pivot[existing]

        ax = pivot.plot(kind="bar", ax=axes[i], legend=(i==1))
        ax.set_title(ylabel, fontsize=11, weight="bold")
        ax.set_xlabel("Layer")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
        ax.yaxis.set_major_formatter(FuncFormatter(thousand_fmt))
    fig.suptitle(f"Dashboard — {family}", fontsize=13, weight="bold")
    plt.tight_layout()
    out_png = os.path.join(outdir, f"{family.lower()}_dashboard.png")
    plt.savefig(out_png, dpi=200)
    plt.close()
    print(f"[OK] Export: {out_png}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=False,
        default=r"C:\Users\fatima zehra\Downloads\FedSDM-Project\FedSDM-Project\scenarios",
        help="Dossier racine des scenarios")
    ap.add_argument("--out", required=False, default="figures", help="Dossier de sortie pour les PNG")
    args = ap.parse_args()

    root = args.root
    out = args.out
    os.makedirs(out, exist_ok=True)

    df = load_all_csv(root)
    # Nettoyage
    df["layer"] = df["layer"].str.upper()
    df["family"] = df["family"].str.upper()
    df["level"] = df["level"].str.upper()

    # Boucle par famille
    for family in FAMILIES:
        df_f = df[df["family"] == family]
        if df_f.empty:
            print(f"[WARN] Aucune donnée pour la famille {family}")
            continue
        fam_out = os.path.join(out, family.lower())
        os.makedirs(fam_out, exist_ok=True)

        # Dashboard famille
        plot_family_dashboard(df_f, family, fam_out)

        # Chaque métrique, barres groupées
        for metric, ylabel in METRICS:
            plot_family_metric(df_f, family, metric, ylabel, fam_out)

    # Export CSV agrégé si besoin
    agg_csv = os.path.join(out, "scenarios_aggregated.csv")
    df.to_csv(agg_csv, index=False)
    print(f"[OK] Agrégat CSV : {agg_csv}")

if __name__ == "__main__":
    main()