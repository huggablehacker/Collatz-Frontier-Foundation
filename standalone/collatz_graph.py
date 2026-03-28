"""
Collatz Conjecture — Results Grapher
--------------------------------------
Reads collatz_results.txt produced by collatz.py and generates
a multi-panel line chart showing:

  1. Steps to reach 1       — per starting number n
  2. Peak value reached     — per starting number n
  3. FAIL flags             — highlighted if any counterexamples exist

Usage:
    python3 collatz_graph.py                        # uses collatz_results.txt in current dir
    python3 collatz_graph.py --file my_results.txt  # custom file
    python3 collatz_graph.py --max 10000            # only graph first 10,000 numbers
    python3 collatz_graph.py --smooth 50            # apply a rolling average with window=50
"""

import re
import sys
import argparse
import time
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend — saves to file
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    from matplotlib.gridspec import GridSpec
except ImportError:
    print("ERROR: matplotlib is required.  Run:  pip install matplotlib")
    sys.exit(1)


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Graph Collatz Conjecture results")
    p.add_argument("--file",   default="collatz_results.txt", help="Input results file")
    p.add_argument("--out",    default="collatz_graph.png",   help="Output image file")
    p.add_argument("--max",    type=int, default=None,        help="Max numbers to graph (e.g. 10000)")
    p.add_argument("--smooth", type=int, default=0,           help="Rolling average window size (0 = off)")
    return p.parse_args()


# ── Parser ────────────────────────────────────────────────────────────────────

LINE_RE = re.compile(
    r"n=\s*(\d+)\s*\|\s*(PASS|FAIL[^\|]*?)\s*\|\s*steps=\s*(\d+)\s*\|\s*peak=(\d+)"
)

def parse_results(filepath, max_n=None):
    ns, steps, peaks, fails = [], [], [], []
    path = Path(filepath)

    if not path.exists():
        print(f"ERROR: File not found — {filepath}")
        sys.exit(1)

    print(f"Parsing {filepath} ...")
    t0 = time.time()

    with open(path, "r") as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue
            n       = int(m.group(1))
            status  = m.group(2).strip()
            s       = int(m.group(3))
            peak    = int(m.group(4))

            ns.append(n)
            steps.append(s)
            peaks.append(peak)
            fails.append(status != "PASS")

            if max_n and n >= max_n:
                break

    elapsed = time.time() - t0
    print(f"  Loaded {len(ns):,} records in {elapsed:.2f}s")
    if not ns:
        print("ERROR: No data rows found. Make sure the file was written by collatz.py")
        sys.exit(1)

    return ns, steps, peaks, fails


# ── Rolling average ───────────────────────────────────────────────────────────

def rolling_avg(data, window):
    if window < 2:
        return data
    result = []
    for i in range(len(data)):
        lo = max(0, i - window // 2)
        hi = min(len(data), i + window // 2 + 1)
        result.append(sum(data[lo:hi]) / (hi - lo))
    return result


# ── Chart ─────────────────────────────────────────────────────────────────────

def build_chart(ns, steps, peaks, fails, smooth, out_file):
    fail_indices = [i for i, f in enumerate(fails) if f]
    fail_ns      = [ns[i] for i in fail_indices]
    fail_steps   = [steps[i] for i in fail_indices]
    fail_peaks   = [peaks[i] for i in fail_indices]

    # Smoothed series
    steps_line = rolling_avg(steps, smooth) if smooth >= 2 else steps
    peaks_line = rolling_avg(peaks, smooth) if smooth >= 2 else peaks

    # ── Style ────────────────────────────────────────────────────────────────
    BG       = "#0d1117"
    PANEL    = "#161b22"
    GRID     = "#21262d"
    CYAN     = "#58a6ff"
    ORANGE   = "#f78166"
    YELLOW   = "#e3b341"
    RED      = "#ff4444"
    TEXT     = "#c9d1d9"
    SUBTEXT  = "#8b949e"

    plt.rcParams.update({
        "figure.facecolor":  BG,
        "axes.facecolor":    PANEL,
        "axes.edgecolor":    GRID,
        "axes.labelcolor":   TEXT,
        "axes.titlecolor":   TEXT,
        "xtick.color":       SUBTEXT,
        "ytick.color":       SUBTEXT,
        "grid.color":        GRID,
        "text.color":        TEXT,
        "font.family":       "monospace",
        "font.size":         10,
    })

    fig = plt.figure(figsize=(16, 11), facecolor=BG)
    fig.suptitle(
        "Collatz Conjecture  ·  Sequence Analysis",
        fontsize=18, fontweight="bold", color=TEXT, y=0.97
    )

    gs = GridSpec(
        3, 1,
        figure=fig,
        hspace=0.45,
        top=0.91, bottom=0.07,
        left=0.08, right=0.97
    )

    # ── Panel 1 — Steps to reach 1 ───────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(ns, steps, color=CYAN, linewidth=0.6, alpha=0.5, label="Steps (raw)")
    if smooth >= 2:
        ax1.plot(ns, steps_line, color=CYAN, linewidth=1.8, alpha=0.95,
                 label=f"Steps (rolling avg {smooth})")
    if fail_ns:
        ax1.scatter(fail_ns, fail_steps, color=RED, s=60, zorder=5,
                    label="FAIL ⚠", marker="X")

    ax1.set_title("Steps to reach 1", fontsize=12, pad=8)
    ax1.set_ylabel("Steps", color=TEXT)
    ax1.grid(True, linewidth=0.4, alpha=0.6)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax1.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax1.legend(loc="upper left", fontsize=8, facecolor=PANEL, edgecolor=GRID)

    # Annotate record-breaking step count
    max_step = max(steps)
    max_step_n = ns[steps.index(max_step)]
    ax1.annotate(
        f"peak: {max_step:,} steps\n(n={max_step_n:,})",
        xy=(max_step_n, max_step),
        xytext=(max_step_n, max_step * 0.75),
        color=YELLOW, fontsize=8,
        arrowprops=dict(arrowstyle="->", color=YELLOW, lw=1.2),
    )

    # ── Panel 2 — Peak value reached ─────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(ns, peaks, color=ORANGE, linewidth=0.6, alpha=0.5, label="Peak value (raw)")
    if smooth >= 2:
        ax2.plot(ns, peaks_line, color=ORANGE, linewidth=1.8, alpha=0.95,
                 label=f"Peak value (rolling avg {smooth})")
    if fail_ns:
        ax2.scatter(fail_ns, fail_peaks, color=RED, s=60, zorder=5,
                    label="FAIL ⚠", marker="X")

    ax2.set_title("Highest value reached during sequence", fontsize=12, pad=8)
    ax2.set_ylabel("Peak value", color=TEXT)
    ax2.grid(True, linewidth=0.4, alpha=0.6)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax2.legend(loc="upper left", fontsize=8, facecolor=PANEL, edgecolor=GRID)

    max_peak = max(peaks)
    max_peak_n = ns[peaks.index(max_peak)]
    ax2.annotate(
        f"peak: {max_peak:,}\n(n={max_peak_n:,})",
        xy=(max_peak_n, max_peak),
        xytext=(max_peak_n, max_peak * 0.72),
        color=YELLOW, fontsize=8,
        arrowprops=dict(arrowstyle="->", color=YELLOW, lw=1.2),
    )

    # ── Panel 3 — Steps histogram (distribution) ──────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    ax3.hist(steps, bins=80, color=CYAN, alpha=0.75, edgecolor=PANEL, linewidth=0.3)
    ax3.set_title("Distribution of step counts", fontsize=12, pad=8)
    ax3.set_xlabel("Steps to reach 1", color=TEXT)
    ax3.set_ylabel("Frequency", color=TEXT)
    ax3.grid(True, linewidth=0.4, alpha=0.6, axis="y")
    ax3.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax3.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    mean_steps = sum(steps) / len(steps)
    ax3.axvline(mean_steps, color=YELLOW, linewidth=1.5, linestyle="--",
                label=f"Mean: {mean_steps:.1f} steps")
    ax3.legend(loc="upper right", fontsize=8, facecolor=PANEL, edgecolor=GRID)

    # ── Footer stats ──────────────────────────────────────────────────────────
    total   = len(ns)
    n_fails = sum(fails)
    footer  = (
        f"Numbers tested: {total:,}  |  "
        f"Range: {ns[0]:,} → {ns[-1]:,}  |  "
        f"Avg steps: {mean_steps:.1f}  |  "
        f"Max steps: {max(steps):,}  |  "
        f"FAILs: {n_fails} {'← POTENTIAL MATHEMATICAL DISCOVERY' if n_fails else '(none — conjecture holds for all tested)'}"
    )
    fig.text(0.5, 0.01, footer, ha="center", fontsize=8.5,
             color=RED if n_fails else SUBTEXT)

    # ── Save ──────────────────────────────────────────────────────────────────
    plt.savefig(out_file, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"  Chart saved → {out_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("=" * 60)
    print(" Collatz Conjecture — Results Grapher")
    print("=" * 60)

    ns, steps, peaks, fails = parse_results(args.file, max_n=args.max)

    n_fails = sum(fails)
    print(f"  Numbers loaded : {len(ns):,}")
    print(f"  Range          : {ns[0]:,} → {ns[-1]:,}")
    print(f"  Avg steps      : {sum(steps)/len(steps):.1f}")
    print(f"  Max steps      : {max(steps):,}  (at n={ns[steps.index(max(steps))]:,})")
    print(f"  Max peak value : {max(peaks):,}  (at n={ns[peaks.index(max(peaks))]:,})")
    print(f"  FAILs          : {n_fails}")
    if n_fails:
        print(f"  *** POTENTIAL COUNTEREXAMPLES FOUND — check your results! ***")
    print()
    print(f"Building chart ...")
    if args.smooth >= 2:
        print(f"  Rolling average window: {args.smooth}")

    build_chart(ns, steps, peaks, fails, smooth=args.smooth, out_file=args.out)

    print()
    print("Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
