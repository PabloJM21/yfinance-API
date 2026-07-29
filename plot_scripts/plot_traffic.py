import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import colorsys


def _shade(rgb, factor):
    """Return a lighter/darker variant of an RGB color. factor in (0, 1], 1 = original."""
    h, l, s = colorsys.rgb_to_hls(*rgb)
    l = max(0.15, min(0.85, l * factor))
    return colorsys.hls_to_rgb(h, l, s)


def plot_traffic(metrics: dict, output_path: str, mem_mb = None, max_memory = None):

    print(f"metrics: {metrics}")
    print("plot_traffic called, saving to:", output_path)

    samples = metrics["samples"]

    # Group samples by endpoint
    endpoints = {}
    for s in samples:
        endpoints.setdefault(s["endpoint"], []).append(s)

    num_endpoints = len(endpoints)
    fig, axes = plt.subplots(1, num_endpoints, figsize=(6 * num_endpoints, 5), sharey=True)

    if num_endpoints == 1:
        axes = [axes]

    base_colors = plt.cm.tab10.colors

    # Compute global y-range across all endpoints, with extra headroom at the
    # top so the top-left legend doesn't overlap the curves.
    all_latencies = [s["latency_ms"] for s in samples]
    y_min, y_max = min(all_latencies), max(all_latencies)
    y_range = y_max - y_min if y_max > y_min else 1
    y_bottom = y_min - 0.05 * y_range
    y_top = y_max + 0.45 * y_range  # generous top padding for the legend

    for ep_idx, (ax, (endpoint, endpoint_samples)) in enumerate(zip(axes, endpoints.items())):
        latencies = [s["latency_ms"] for s in endpoint_samples]
        x_values = list(range(1, len(latencies) + 1))  # reindexed from 1 each subplot
        base_color = base_colors[ep_idx % len(base_colors)]

        # Base latency curve
        ax.plot(x_values, latencies, color="gray", alpha=0.5, zorder=1)

        # Group by label inside this endpoint
        groups = {}
        for idx, sample in enumerate(endpoint_samples):
            groups.setdefault(sample["label"], []).append(idx)

        num_groups = len(groups)
        for color_idx, (label, indices) in enumerate(groups.items()):
            factor = 1.3 - (color_idx / max(1, num_groups - 1)) * 0.8 if num_groups > 1 else 1.0
            shade = _shade(base_color, factor)
            ax.scatter(
                [x_values[i] for i in indices],
                [latencies[i] for i in indices],
                color=shade,
                label=label,
                zorder=2,
            )

        # Red points for non-successful requests
        bad_indices = [i for i, s in enumerate(endpoint_samples) if s["status"] != 200]
        if bad_indices:
            ax.scatter(
                [x_values[i] for i in bad_indices],
                [latencies[i] for i in bad_indices],
                color="red",
                label="Non-successful requests",
                zorder=3,
            )

        ax.set_title(f"endpoint: {endpoint}")
        ax.set_xlabel("Request #")
        if ep_idx == 0:
            ax.set_ylabel("Latency (ms)")
        ax.grid(True)

        ax.set_xlim(0.5, len(latencies) + 0.5)
        ax.xaxis.set_major_locator(mticker.MultipleLocator(1))

        # Deduplicate legend entries by label within this subplot
        handles, labels = ax.get_legend_handles_labels()
        seen = {}
        for h, l in zip(handles, labels):
            if l not in seen:
                seen[l] = h
        ax.legend(seen.values(), seen.keys(), loc="upper left", fontsize=9)

    # Apply shared, padded y-range once (sharey=True propagates it to all axes)
    axes[0].set_ylim(y_bottom, y_top)

    fig.suptitle("API Traffic Metrics")

    if max_memory:
        fig.text(
            0.5, 0.01,
            f"Memory used: {mem_mb:.2f} MB (below max memory of {max_memory:.2f} MB)",
            ha="center", va="bottom",
            fontsize=10,
        )

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    plt.savefig(output_path, dpi=150)
    print(f"Saved plot to {output_path}")