from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
OUTPUT_DIR = BASE / "outputs"
FIG_DIR = BASE / "Figures" / "WT" / "Segment_References_1989_2025"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "WT_Segment_Reference_Curves_1989_2025.xlsx"

MODALITIES = ["Standard", "Sprint"]
SEXES = ["F", "M"]
SEGMENTS = [
    ("swim_seconds", "Swim"),
    ("t1_seconds", "T1"),
    ("bike_seconds", "Bike"),
    ("t2_seconds", "T2"),
    ("run_seconds", "Run"),
]

P_MIN = 10
P_MAX = 90
FIT_GRID_N = 100
N_ITERATIONS = 2
MIN_GROUP_RECORDS = 20
MIN_EVENT_RECORDS = 5
MIN_EVENTS = 2


def safe_name(value: object) -> str:
    text = re.sub(r"[^\w\-]+", "_", str(value))
    return re.sub(r"_+", "_", text).strip("_")[:120]


def age_group_key(age_group: str) -> tuple[int, int]:
    text = str(age_group)
    nums = [int(x) for x in text.replace("+", "").split("-") if x.isdigit()]
    if not nums:
        return (999, 999)
    return (nums[0], nums[1] if len(nums) > 1 else 999)


def seconds_to_label(seconds: float) -> str:
    if not np.isfinite(seconds):
        return ""
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def curve_resolution(n: int) -> int:
    return int(min(1000, max(50, math.ceil(0.10 * n))))


def quantile_time_at_performance(times: np.ndarray, performance_percentiles: np.ndarray) -> np.ndarray:
    values = np.asarray(times, dtype=float)
    values = values[np.isfinite(values) & (values > 0)]
    return np.percentile(values, 100 - np.asarray(performance_percentiles, dtype=float))


def reference_curve_from_times(times: np.ndarray, label: str, n_points: int) -> pd.DataFrame:
    grid = np.linspace(0.5, 99.5, n_points)
    q = quantile_time_at_performance(times, grid)
    return pd.DataFrame(
        {
            "reference": label,
            "performance_percentile": grid,
            "seconds": q,
            "time_label": [seconds_to_label(x) for x in q],
            "log_seconds": np.log(q),
        }
    )


def fit_event_to_reference(event_times: np.ndarray, ref_times: np.ndarray, grid: np.ndarray) -> dict:
    event_q = quantile_time_at_performance(event_times, grid)
    ref_q = quantile_time_at_performance(ref_times, grid)
    x = np.log(event_q)
    y = np.log(ref_q)
    beta, alpha = np.polyfit(x, y, 1)
    y_hat = alpha + beta * x
    residuals = y - y_hat
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {
        "alpha": float(alpha),
        "beta": float(beta),
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan,
        "correlation_r": float(np.sqrt(max(0, 1 - ss_res / ss_tot))) if ss_tot > 0 else np.nan,
        "rmse_log": float(np.sqrt(np.mean(residuals**2))),
        "mae_seconds_on_grid": float(np.mean(np.abs(np.exp(y_hat) - ref_q))),
    }


def transform_times(times: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    values = np.asarray(times, dtype=float)
    return np.exp(alpha + beta * np.log(values))


def build_segment_reference(
    group: pd.DataFrame,
    metric: str,
    segment: str,
    modality: str,
    sex: str,
    age_group: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    source = group[group[metric].notna() & (group[metric] > 0)].copy()
    event_counts = source.groupby("year").size()
    valid_events = event_counts[event_counts >= MIN_EVENT_RECORDS]
    meta = {
        "modality": modality,
        "sex": sex,
        "age_group": age_group,
        "metric": metric,
        "segment": segment,
        "records": int(len(source)),
        "events": int(len(valid_events)),
    }

    if len(source) < MIN_GROUP_RECORDS or len(valid_events) < MIN_EVENTS:
        empty = pd.DataFrame()
        return empty, empty, empty, {**meta, "status": "Skipped: insufficient data"}

    n_points = curve_resolution(len(source))
    fit_grid = np.linspace(P_MIN, P_MAX, FIT_GRID_N)
    references = [
        reference_curve_from_times(source[metric].to_numpy(dtype=float), "Initial raw pool", n_points)
    ]
    current_by_event = {
        str(year): g[metric].to_numpy(dtype=float)
        for year, g in source.groupby("year")
        if len(g) >= MIN_EVENT_RECORDS
    }
    params_rows = []
    iteration_rows = []

    for iteration in range(1, N_ITERATIONS + 1):
        ref_times = np.concatenate(list(current_by_event.values()))
        transformed_by_event = {}
        for event, event_times in current_by_event.items():
            fit = fit_event_to_reference(event_times, ref_times, fit_grid)
            params_rows.append(
                {
                    **meta,
                    "iteration": iteration,
                    "year": int(event),
                    "event_records": int(len(event_times)),
                    **fit,
                }
            )
            transformed_by_event[event] = transform_times(event_times, fit["alpha"], fit["beta"])

        next_times = np.concatenate(list(transformed_by_event.values()))
        references.append(reference_curve_from_times(next_times, f"Iteration {iteration}", n_points))
        eval_grid = np.linspace(1, 99, 199)
        prev_q = quantile_time_at_performance(references[-2]["seconds"].to_numpy(), eval_grid)
        next_q = quantile_time_at_performance(next_times, eval_grid)
        current_params = [p for p in params_rows if p["iteration"] == iteration]
        iteration_rows.append(
            {
                **meta,
                "iteration": iteration,
                "mean_abs_reference_change_seconds": float(np.mean(np.abs(next_q - prev_q))),
                "max_abs_reference_change_seconds": float(np.max(np.abs(next_q - prev_q))),
                "mean_event_r": float(np.nanmean([p["correlation_r"] for p in current_params])),
                "mean_event_r2": float(np.nanmean([p["r2"] for p in current_params])),
                "mean_event_rmse_log": float(np.nanmean([p["rmse_log"] for p in current_params])),
                "mean_event_mae_seconds": float(np.nanmean([p["mae_seconds_on_grid"] for p in current_params])),
            }
        )
        current_by_event = transformed_by_event

    ref = pd.concat(references, ignore_index=True)
    for key, value in reversed(list(meta.items())):
        ref.insert(0, key, value)
    return ref, pd.DataFrame(params_rows), pd.DataFrame(iteration_rows), {**meta, "status": "Built", "curve_points": n_points}


def plot_group(reference_curves: pd.DataFrame, modality: str, sex: str, age_group: str, out_path: Path) -> None:
    final = reference_curves[reference_curves["reference"] == f"Iteration {N_ITERATIONS}"].copy()
    if final.empty:
        return
    present_segments = [s for _, s in SEGMENTS if s in set(final["segment"])]
    n = len(present_segments)
    cols = 3
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.8 * cols, 4.5 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, segment in zip(axes.ravel(), present_segments):
        ax.axis("on")
        g = final[final["segment"] == segment]
        ax.plot(g["seconds"] / 60, g["performance_percentile"], color="#0b2239", linewidth=2.5)
        ax.invert_yaxis()
        ax.set_ylim(100, 0)
        ax.grid(True, color="#d7dee7", linewidth=0.8, alpha=0.7)
        ax.set_title(segment)
        ax.set_xlabel("Time")
        ax.set_ylabel("Competitive percentile")
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([seconds_to_label(t * 60) for t in ticks], fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(f"WT {modality} {sex} {age_group}: marginal segment reference curves", fontsize=16)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def main() -> None:
    df = pd.read_excel(INPUT_FILE, sheet_name="Canonical_Results")
    df["age_group"] = df["age_group"].astype(str).replace({"70+": "70-74"})
    for metric, _ in SEGMENTS:
        df[metric] = pd.to_numeric(df[metric], errors="coerce")

    all_refs = []
    all_params = []
    all_iterations = []
    group_rows = []
    figure_rows = []

    for modality in MODALITIES:
        for sex in SEXES:
            age_groups = sorted(
                df.loc[(df["modality"] == modality) & (df["sex"] == sex), "age_group"].dropna().unique(),
                key=age_group_key,
            )
            for age_group in age_groups:
                group = df[
                    (df["modality"] == modality)
                    & (df["sex"] == sex)
                    & (df["age_group"] == age_group)
                ].copy()
                group_ref_parts = []
                for metric, segment in SEGMENTS:
                    refs, params, iterations, meta = build_segment_reference(
                        group, metric, segment, modality, sex, age_group
                    )
                    group_rows.append(meta)
                    if not refs.empty:
                        all_refs.append(refs)
                        all_params.append(params)
                        all_iterations.append(iterations)
                        group_ref_parts.append(refs)
                if group_ref_parts:
                    group_refs = pd.concat(group_ref_parts, ignore_index=True)
                    out_dir = FIG_DIR / modality / sex
                    out_dir.mkdir(parents=True, exist_ok=True)
                    fig_path = out_dir / f"WT_{safe_name(modality)}_{safe_name(sex)}_{safe_name(age_group)}_Segment_References.png"
                    plot_group(group_refs, modality, sex, age_group, fig_path)
                    figure_rows.append(
                        {
                            "modality": modality,
                            "sex": sex,
                            "age_group": age_group,
                            "figure_path": str(fig_path),
                        }
                    )

    refs_df = pd.concat(all_refs, ignore_index=True)
    params_df = pd.concat(all_params, ignore_index=True)
    iterations_df = pd.concat(all_iterations, ignore_index=True)
    groups_df = pd.DataFrame(group_rows)
    figures_df = pd.DataFrame(figure_rows)
    iter2 = iterations_df[iterations_df["iteration"] == N_ITERATIONS].copy()

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        refs_df.to_excel(writer, index=False, sheet_name="Reference_Curves")
        groups_df.to_excel(writer, index=False, sheet_name="Group_Segment_Summary")
        iter2.to_excel(writer, index=False, sheet_name="Iteration2_Summary")
        iterations_df.to_excel(writer, index=False, sheet_name="All_Iterations")
        params_df.to_excel(writer, index=False, sheet_name="Event_Transform_Params")
        figures_df.to_excel(writer, index=False, sheet_name="Figure_Index")
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                vals = [str(cell.value) for cell in col[:200] if cell.value is not None]
                ws.column_dimensions[col[0].column_letter].width = min(max([len(v) for v in vals] + [10]) + 2, 52)

    print(f"written={OUTPUT_FILE}")
    print(f"figures={len(figures_df)} dir={FIG_DIR}")
    print("\nBuilt segment groups by modality/sex/segment")
    built = groups_df[groups_df["status"].eq("Built")]
    print(
        built.groupby(["modality", "sex", "segment"])
        .agg(groups=("age_group", "count"), records=("records", "sum"), mean_events=("events", "mean"))
        .reset_index()
        .to_string(index=False)
    )
    print("\nIteration 2 mean correlations")
    print(
        iter2.groupby(["modality", "sex", "segment"])
        .agg(groups=("age_group", "count"), mean_r=("mean_event_r", "mean"), mean_mae_seconds=("mean_event_mae_seconds", "mean"))
        .reset_index()
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
