import json
import matplotlib.pyplot as plt
import os

# Paths
DATA_PATH = "/LAB/@thesis/layra/docs/thesis/evaluation/data/eval-run-full.json"
FIGURE_PATH = (
    "/LAB/@thesis/layra/docs/thesis/evaluation/figures/fig-metrics-summary.png"
)

# Load data
with open(DATA_PATH, "r") as f:
    data = json.load(f)

metrics = data["metrics"]

# Prepare data for plotting
labels = ["MRR", "NDCG@5", "Precision@5", "Recall@5"]
values = [metrics["mrr"], metrics["ndcg"], metrics["precision"], metrics["recall"]]

# Set plot style and figure size
plt.rcParams.update({"font.size": 12})
fig, ax = plt.subplots(figsize=(8, 6))

# Create bar chart
bars = ax.bar(
    labels, values, color=["#2c3e50", "#3498db", "#95a5a6", "#e74c3c"], width=0.6
)

# Add grid lines
ax.set_axisbelow(True)
ax.yaxis.grid(color="gray", linestyle="dashed", alpha=0.7)

# Labeling
ax.set_ylabel("Score", fontweight="bold")
ax.set_title("Aggregate Retrieval Performance Metrics", fontweight="bold", pad=20)
ax.set_ylim(0, 1.1)  # Buffer for labels

# Add value labels on top of bars
for bar in bars:
    height = bar.get_height()
    ax.annotate(
        f"{height:.2f}",
        xy=(bar.get_x() + bar.get_width() / 2, height),
        xytext=(0, 3),  # 3 points vertical offset
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontweight="bold",
    )

# Ensure output directory exists
os.makedirs(os.path.dirname(FIGURE_PATH), exist_ok=True)

# Save figure
plt.tight_layout()
plt.savefig(FIGURE_PATH, dpi=300)
print(f"Figure saved to {FIGURE_PATH}")
