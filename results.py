import pandas as pd
import matplotlib.pyplot as plt

# Charger le CSV
df = pd.read_csv("figures/scenarios_aggregated.csv")

print(df.head())

plt.figure()
for scenario in df["scenario"].unique():
    subset = df[df["scenario"] == scenario]
    plt.plot(subset["variant"], subset["energy_j"], marker='o', label=scenario)

plt.xlabel("Variant")
plt.ylabel("Energy (J)")
plt.title("Energy consumption by scenario")
plt.xticks(rotation=90)
plt.legend()
plt.tight_layout()
plt.show()

plt.figure()
for scenario in df["scenario"].unique():
    subset = df[df["scenario"] == scenario]
    plt.plot(subset["variant"], subset["exec_time_ms"], marker='o', label=scenario)

plt.xlabel("Variant")
plt.ylabel("Execution Time (ms)")
plt.title("Execution time by scenario")
plt.xticks(rotation=90)
plt.legend()
plt.tight_layout()
plt.show()


variant_name = "LOAD_HIGH"
subset = df[df["variant"] == variant_name]

plt.figure()
plt.bar(subset["scenario"], subset["energy_j"])
plt.xlabel("Scenario")
plt.ylabel("Energy (J)")
plt.title(f"Energy comparison for {variant_name}")
plt.show()


pivot = df.pivot(index="variant", columns="scenario", values="energy_j")

pivot.plot()
plt.ylabel("Energy (J)")
plt.title("Energy comparison")
plt.xticks(rotation=90)
plt.tight_layout()
plt.show()
