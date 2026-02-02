import json
import matplotlib.pyplot as plt
import os


def generate_boxplot(data_path, output_path):
    with open(data_path, "r") as f:
        data = json.load(f)

    results = data.get("results", [])

    mrr_scores = []
    ndcg_scores = []
    precision_scores = []
    recall_scores = []

    for res in results:
        metrics = res.get("metrics", {})
        mrr_scores.append(metrics.get("mrr", 0))
        ndcg_scores.append(metrics.get("ndcg", 0))
        precision_scores.append(metrics.get("precision", 0))
        recall_scores.append(metrics.get("recall", 0))

    metrics_data = [mrr_scores, ndcg_scores, precision_scores, recall_scores]
    labels = ["MRR", "NDCG@5", "Precision@5", "Recall@5"]

    plt.figure(figsize=(8, 6))

    # Create boxplot
    box = plt.boxplot(
        metrics_data,
        labels=labels,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5),
        flierprops=dict(marker="o", color="red", markersize=5),
    )

    # Style the boxes
    colors = ["#aec7e8", "#ffbb78", "#98df8a", "#ff9896"]
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)

    plt.title(
        "Distribution of Per-Query Retrieval Metrics",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    plt.ylabel("Score", fontsize=12)
    plt.xlabel("Metric", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Set tick font size
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)

    plt.tight_layout()

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.savefig(output_path, dpi=300)
    print(f"Successfully saved boxplot to {output_path}")


if __name__ == "__main__":
    DATA_FILE = "docs/thesis/evaluation/data/eval-run-full.json"
    OUTPUT_FILE = "docs/thesis/evaluation/figures/fig-metrics-distribution.png"
    generate_boxplot(DATA_FILE, OUTPUT_FILE)
