from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
OUTPUT_DIR = BASE / "outputs"
FIG_DIR = BASE / "Figures" / "WT" / "Segments_All"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

OUT_XLSX = OUTPUT_DIR / "WT_All_Sprint_Standard_Segment_Percentiles.xlsx"

MODALITIES = ["Standard", "Sprint"]
SEXES = ["F", "M"]
P_MIN = 10
P_MAX = 90
N_GRID = 100
N_ITERATIONS = 2
MIN_GROUP_RECORDS = 20
MIN_EVENT_RECORDS = 5
MIN_EVENTS = 2

METRICS = [
    ("swim_seconds", "Swim"),
    ("t1_seconds", "T1"),
    ("bike_seconds", "Bike"),
    ("t2_seconds", "T2"),
    ("run_seconds", "Run"),
    ("total_seconds", "Total"),
]


def sex_label(sex: str) -> str:
    return "O" if sex == "M" else "F"


def age_group_key(age_group: str) -> tuple[int, int]:
    text = str(age_group)
    nums = [int(x) for x in text.replace("+", "").split("-") if x.isdigit()]
    if not nums:
        return (999, 999)
    return (nums[0], nums[1] if len(nums) > 1 else 999)


def seconds_to_hms(seconds: float) -> str:
    if not np.isfinite(seconds):
        return ""
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def empirical_curve_from_times(times: np.ndarray, label: str, metric: str, segment: str) -> pd.DataFrame:
    values = np.sort(np.asarray(times, dtype=float))
    values = values[np.isfinite(values) & (values > 0)]
    n = len(values)
    return pd.DataFrame(
        {
            "metric": metric,
            "segment": segment,
            "reference": label,
            "rank_fast_to_slow": np.arange(1, n + 1),
            "seconds": values,
            "log_seconds": np.log(values),
            "performance_percentile": 100 * (1 - (np.arange(1, n + 1) - 0.5) / n),
        }
    )


def quantile_time_at_performance(times: np.ndarray, performance_percentiles: np.ndarray) -> np.ndarray:
    return np.percentile(times, 100 - np.asarray(performance_percentiles, dtype=float))


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
        "rmse_log": float(np.sqrt(np.mean(residuals**2))),
        "mae_seconds_on_grid": float(np.mean(np.abs(np.exp(y_hat) - ref_q))),
    }


def transform_times(times: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    return np.exp(alpha + beta * np.log(times))


def percentile_from_reference(times: np.ndarray, reference_times: np.ndarray) -> np.ndarray:
    ref = np.sort(np.asarray(reference_times, dtype=float))
    slower_or_equal = len(ref) - np.searchsorted(ref, times, side="left")
    return 100 * slower_or_equal / len(ref)


def build_metric_reference(group: pd.DataFrame, metric: str, segment: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grid = np.linspace(P_MIN, P_MAX, N_GRID)
    references = [empirical_curve_from_times(group[metric].to_numpy(dtype=float), "Initial raw pool", metric, segment)]
    params = []
    summary = []
    current_times_by_event = {
        str(event): g[metric].to_numpy(dtype=float)
        for event, g in group.groupby("year")
        if len(g) >= MIN_EVENT_RECORDS
    }

    for iteration in range(1, N_ITERATIONS + 1):
        ref_times = np.concatenate(list(current_times_by_event.values()))
        transformed_by_event = {}
        for event, event_times in current_times_by_event.items():
            fit = fit_event_to_reference(event_times, ref_times, grid)
            params.append(
                {
                    "metric": metric,
                    "segment": segment,
                    "iteration": iteration,
                    "year": int(event),
                    "records": len(event_times),
                    **fit,
                }
            )
            transformed_by_event[event] = transform_times(event_times, fit["alpha"], fit["beta"])

        next_ref_times = np.concatenate(list(transformed_by_event.values()))
        references.append(empirical_curve_from_times(next_ref_times, f"Iteration {iteration}", metric, segment))

        eval_grid = np.linspace(1, 99, 199)
        prev_q = quantile_time_at_performance(references[-2]["seconds"].to_numpy(), eval_grid)
        next_q = quantile_time_at_performance(next_ref_times, eval_grid)
        current_params = [p for p in params if p["iteration"] == iteration]
        summary.append(
            {
                "metric": metric,
                "segment": segment,
                "iteration": iteration,
                "mean_abs_reference_change_seconds": float(np.mean(np.abs(next_q - prev_q))),
                "max_abs_reference_change_seconds": float(np.max(np.abs(next_q - prev_q))),
                "mean_event_r2": float(np.mean([p["r2"] for p in current_params])),
                "mean_event_rmse_log": float(np.mean([p["rmse_log"] for p in current_params])),
            }
        )
        current_times_by_event = transformed_by_event

    return pd.concat(references, ignore_index=True), pd.DataFrame(params), pd.DataFrame(summary)


def plot_group_reference_curves(group_key: dict, reference_curves: pd.DataFrame, out_path: Path) -> None:
    final = reference_curves[reference_curves["reference"] == f"Iteration {N_ITERATIONS}"].copy()
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    for ax, (metric, segment) in zip(axes.ravel(), METRICS):
        g = final[final["metric"] == metric]
        ax.plot(g["seconds"] / 60, g["performance_percentile"], color="#0b2239", linewidth=3.0)
        ax.set_title(segment)
        ax.set_ylim(0, 100)
        if len(g):
            x_low, x_high = np.percentile(g["seconds"], [0.5, 99.5])
            pad = 0.04 * (x_high - x_low) if x_high > x_low else 1
            ax.set_xlim((x_low - pad) / 60, (x_high + pad) / 60)
        ax.grid(True, color="#d7dee7", linewidth=0.8)
        ax.set_xlabel("Time")
        ax.set_ylabel("Performance percentile")
        ticks = ax.get_xticks()
        ax.set_xticks(ticks)
        ax.set_xticklabels([seconds_to_hms(t * 60) for t in ticks], fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle(
        f"WT {group_key['modality']} {group_key['sex_label']} {group_key['age_group']} - Segment Reference Curves",
        fontsize=18,
    )
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def plot_group_profile(group_key: dict, scored: pd.DataFrame, out_path: Path) -> None:
    percentile_cols = [f"{metric}_percentile" for metric, _ in METRICS]
    labels = [segment for _, segment in METRICS]
    values = scored[percentile_cols].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(14, 8))
    for row in values:
        ax.plot(labels, row, color="#6b7280", alpha=0.08, linewidth=0.8)
    med = np.nanmedian(values, axis=0)
    q25 = np.nanpercentile(values, 25, axis=0)
    q75 = np.nanpercentile(values, 75, axis=0)
    ax.fill_between(labels, q25, q75, color="#2a9d8f", alpha=0.22, label="IQR")
    ax.plot(labels, med, color="#0b2239", linewidth=3.2, marker="o", label="Median profile")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Performance percentile")
    ax.set_title(f"WT {group_key['modality']} {group_key['sex_label']} {group_key['age_group']} - Segment Profiles")
    ax.grid(True, axis="y", color="#d7dee7", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def main() -> None:
    df = pd.read_excel(INPUT_FILE, sheet_name="Canonical_Results")
    df["age_group"] = df["age_group"].astype(str)

    scored_rows = []
    reference_rows = []
    param_rows = []
    iteration_rows = []
    group_rows = []
    range_rows = []
    suspicious_rows = []

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
                for metric, _ in METRICS:
                    group = group[group[metric].notna() & (group[metric] > 0)]

                event_counts = group.groupby("year").size()
                valid_events = int((event_counts >= MIN_EVENT_RECORDS).sum())
                group_key = {
                    "modality": modality,
                    "sex": sex,
                    "sex_label": sex_label(sex),
                    "age_group": age_group,
                }

                if len(group) < MIN_GROUP_RECORDS or valid_events < MIN_EVENTS:
                    group_rows.append({**group_key, "records": len(group), "events": valid_events, "status": "Skipped: insufficient data"})
                    continue

                scored = group.copy()
                group_refs = []
                group_params = []
                group_summaries = []

                for metric, segment in METRICS:
                    refs, params, summary = build_metric_reference(group, metric, segment)
                    for frame in [refs, params, summary]:
                        frame.insert(0, "age_group", age_group)
                        frame.insert(0, "sex_label", sex_label(sex))
                        frame.insert(0, "sex", sex)
                        frame.insert(0, "modality", modality)
                    group_refs.append(refs)
                    group_params.append(params)
                    group_summaries.append(summary)

                    final_ref = refs[refs["reference"] == f"Iteration {N_ITERATIONS}"]["seconds"].to_numpy(dtype=float)
                    scored[f"{metric}_percentile"] = percentile_from_reference(group[metric].to_numpy(dtype=float), final_ref)

                    q = group[metric].quantile([0, 0.005, 0.01, 0.05, 0.5, 0.95, 0.99, 0.995, 1.0])
                    range_row = {**group_key, "metric": metric, "segment": segment}
                    for idx, value in q.items():
                        range_row[f"q{idx:g}_seconds"] = value
                        range_row[f"q{idx:g}_time"] = seconds_to_hms(value)
                    range_rows.append(range_row)

                references = pd.concat(group_refs, ignore_index=True)
                params = pd.concat(group_params, ignore_index=True)
                summaries = pd.concat(group_summaries, ignore_index=True)

                for col, value in reversed(list(group_key.items())):
                    if col not in scored.columns:
                        scored.insert(0, col, value)
                scored_rows.append(scored)
                reference_rows.append(references)
                param_rows.append(params)
                iteration_rows.append(summaries)

                group_rows.append({**group_key, "records": len(group), "events": valid_events, "status": "Built"})

                out_dir = FIG_DIR / modality / sex_label(sex)
                out_dir.mkdir(parents=True, exist_ok=True)
                stem = f"WT_{modality}_{sex_label(sex)}_{age_group}".replace("+", "plus")
                plot_group_reference_curves(group_key, references, out_dir / f"{stem}_Segment_Reference_Curves.png")
                plot_group_profile(group_key, scored, out_dir / f"{stem}_Segment_Profile_Distribution.png")

                suspicious = group[
                    (group["swim_seconds"] < group["swim_seconds"].quantile(0.005))
                    | (group["swim_seconds"] > group["swim_seconds"].quantile(0.995))
                    | (group["bike_seconds"] < group["bike_seconds"].quantile(0.005))
                    | (group["bike_seconds"] > group["bike_seconds"].quantile(0.995))
                    | (group["run_seconds"] < group["run_seconds"].quantile(0.005))
                    | (group["run_seconds"] > group["run_seconds"].quantile(0.995))
                    | (group["t1_seconds"] > group["t1_seconds"].quantile(0.995))
                    | (group["t2_seconds"] > group["t2_seconds"].quantile(0.995))
                ].copy()
                if not suspicious.empty:
                    for col, value in reversed(list(group_key.items())):
                        if col not in suspicious.columns:
                            suspicious.insert(0, col, value)
                        else:
                            suspicious[col] = value
                    suspicious_rows.append(suspicious)

    scored_all = pd.concat(scored_rows, ignore_index=True) if scored_rows else pd.DataFrame()
    references_all = pd.concat(reference_rows, ignore_index=True) if reference_rows else pd.DataFrame()
    params_all = pd.concat(param_rows, ignore_index=True) if param_rows else pd.DataFrame()
    iterations_all = pd.concat(iteration_rows, ignore_index=True) if iteration_rows else pd.DataFrame()
    group_summary = pd.DataFrame(group_rows)
    range_qc = pd.DataFrame(range_rows)
    suspicious_all = pd.concat(suspicious_rows, ignore_index=True) if suspicious_rows else pd.DataFrame()

    output_cols = [
        "modality",
        "sex_label",
        "age_group",
        "year",
        "program_id",
        "athlete_id",
        "first_name",
        "last_name",
        "country",
        "position",
        "swim_time",
        "t1_time",
        "bike_time",
        "t2_time",
        "run_time",
        "total_time",
    ] + [f"{metric}_percentile" for metric, _ in METRICS]
    output_cols = [c for c in output_cols if c in scored_all.columns]

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        scored_all[output_cols].to_excel(writer, index=False, sheet_name="Athlete_Segment_Percentiles")
        references_all.to_excel(writer, index=False, sheet_name="Segment_Reference_Curves")
        params_all.to_excel(writer, index=False, sheet_name="Event_Transform_Params")
        iterations_all.to_excel(writer, index=False, sheet_name="Iteration_Summary")
        group_summary.to_excel(writer, index=False, sheet_name="Group_Summary")
        range_qc.to_excel(writer, index=False, sheet_name="Segment_Range_QC")
        suspicious_all.to_excel(writer, index=False, sheet_name="Suspicious_Segment_Records")

    print(f"workbook={OUT_XLSX}")
    print(f"figures={FIG_DIR}")
    print(group_summary.to_string(index=False))
    print("\nBuilt records:", len(scored_all))
    print("Built groups:", int((group_summary["status"] == "Built").sum()))


if __name__ == "__main__":
    main()
