import matplotlib.pyplot as plt

def plot_traffic(metrics: dict, output_path: str):
    """
    metrics["samples"] = [
        {
            "endpoint": "/stats",
            "params": {"ticker": "AAPL", "start": "...", "end": "..."},
            "latency_ms": 123.4,
            "status": 200
        },
        ...
    ]
    """

    samples = metrics["samples"]
    latencies = [s["latency_ms"] for s in samples]
    count = metrics["count"]
    status_counts = metrics["status_counts"]

    plt.figure(figsize=(12, 7))

    # Plot latency curve
    plt.plot(latencies, marker="o", label="Latency (ms)")
    plt.title("API Traffic Metrics")
    plt.xlabel("Request #")
    plt.ylabel("Latency (ms)")
    plt.grid(True)

    # Annotate each point with endpoint + params
    for idx, sample in enumerate(samples):
        label = f"{sample['endpoint']} {sample['params']}"
        plt.text(
            idx,
            sample["latency_ms"],
            label,
            fontsize=8,
            rotation=45,
            ha="left",
            va="bottom"
        )

    # Summary box
    summary = f"Total requests: {count}\n"
    summary += "\n".join([f"Status {code}: {cnt}" for code, cnt in status_counts.items()])

    plt.text(
        0.02, 0.95, summary,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(facecolor="white", alpha=0.7)
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Saved plot to {output_path}")
