from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
OUTPUT_DIR = BASE / "outputs"
FIG_DIR = BASE / "Figures" / "WT" / "Standard"
DIAG_DIR = FIG_DIR / "Event_Typicality"
FINAL_DIR = FIG_DIR / "Final_References"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DIAG_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

MODALITY = "Standard"
METRIC = "total_seconds"
P_MIN = 10
P_MAX = 90
N_GRID = 100
N_ITERATIONS = 2
MIN_EVENT_RECORDS = 5

OUT_XLSX = OUTPUT_DIR / "WT_Standard_All_AgeGroup_Reference_Curves_Total_Time_1989_2025.xlsx"


def age_group_key(age_group: str) -> tuple[int, int]:
    text = str(age_group)
    if text == "All":
        return (-1, -1)
    nums = [int(x) for x in text.replace("+", "").split("-") if x.isdigit()]
    if not nums:
        return (999, 999)
    return (nums[0], nums[1] if len(nums) > 1 else 999)


def seconds_to_hmm(seconds: float) -> str:
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h}:{m:02d}"


def empirical_curve_from_times(times: np.ndarray, label: str) -> pd.DataFrame:
    values = np.sort(np.asarray(times, dtype=float))
    values = values[np.isfinite(values) & (values > 0)]
    n = len(values)
    return pd.DataFrame(
        {
            "reference": label,
            "rank_fast_to_slow": np.arange(1, n + 1),
            "total_seconds": values,
            "log_total_seconds": np.log(values),
            "performance_percentile": 100 * (1 - (np.arange(1, n + 1) - 0.5) / n),
        }
    )


def quantile_time_at_performance(times: np.ndarray, performance_percentiles: np.ndarray) -> np.ndarray:
    q = 100 - np.asarray(performance_percentiles, dtype=float)
    return np.percentile(times, q)


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


def add_time_axis(ax, seconds_min: float, seconds_max: float) -> None:
    xmin = np.floor(seconds_min / 600) * 10
    xmax = np.ceil(seconds_max / 600) * 10
    ticks = np.arange(xmin, xmax + 1, 10)
    ax.set_xticks(ticks)
    ax.set_xticklabels([seconds_to_hmm(t * 60) for t in ticks])


def sex_label(sex: str) -> str:
    return "Open" if sex == "M" else "F"


def plot_typicality(source: pd.DataFrame, initial_ref: pd.DataFrame, sex: str, age_group: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    cmap = plt.get_cmap("tab20")
    for idx, (year, g) in enumerate(source.groupby("year")):
        event_curve = empirical_curve_from_times(g[METRIC].to_numpy(dtype=float), str(year))
        ax.plot(
            event_curve["total_seconds"] / 60,
            event_curve["performance_percentile"],
            linewidth=1.6,
            alpha=0.76,
            label=f"WT_{int(year)}_{sex_label(sex)}",
            color=cmap(idx % 20),
        )

    ax.plot(
        initial_ref["total_seconds"] / 60,
        initial_ref["performance_percentile"],
        linewidth=4.0,
        color="#0b2239",
        label="Initial pooled reference",
        zorder=5,
    )
    ax.set_title(f"WT {MODALITY} empirical curves through 2025 - {sex_label(sex)} {age_group}", fontsize=18)
    ax.set_xlabel("Total time (h:mm)")
    ax.set_ylabel("Performance percentile (higher = faster)")
    ax.set_ylim(0, 100)
    add_time_axis(ax, source[METRIC].min(), source[METRIC].max())
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(True, color="#d7dee7", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9, frameon=False)
    fig.tight_layout(rect=[0, 0, 0.82, 1])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def build_reference_for_group(source: pd.DataFrame, sex: str, age_group: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = source.copy()
    source["event_id"] = source["year"].astype(str)
    grid = np.linspace(P_MIN, P_MAX, N_GRID)
    references = [empirical_curve_from_times(source[METRIC].to_numpy(dtype=float), "Initial raw pool")]
    current_times_by_event = {
        str(event): g[METRIC].to_numpy(dtype=float)
        for event, g in source.groupby("event_id")
        if len(g) >= MIN_EVENT_RECORDS
    }
    params = []
    iteration_summary = []

    for iteration in range(1, N_ITERATIONS + 1):
        ref_times = np.concatenate(list(current_times_by_event.values()))
        transformed_by_event = {}
        for event, event_times in current_times_by_event.items():
            fit = fit_event_to_reference(event_times, ref_times, grid)
            params.append(
                {
                    "modality": MODALITY,
                    "sex": sex,
                    "age_group": age_group,
                    "iteration": iteration,
                    "event_id": event,
                    "year": int(event),
                    "records": len(event_times),
                    **fit,
                }
            )
            transformed_by_event[event] = transform_times(event_times, fit["alpha"], fit["beta"])

        next_ref_times = np.concatenate(list(transformed_by_event.values()))
        references.append(empirical_curve_from_times(next_ref_times, f"Iteration {iteration}"))

        grid_eval = np.linspace(1, 99, 199)
        prev_q = quantile_time_at_performance(references[-2]["total_seconds"].to_numpy(), grid_eval)
        next_q = quantile_time_at_performance(next_ref_times, grid_eval)
        current_params = [p for p in params if p["iteration"] == iteration]
        iteration_summary.append(
            {
                "modality": MODALITY,
                "sex": sex,
                "age_group": age_group,
                "iteration": iteration,
                "records": len(source),
                "events": len(current_times_by_event),
                "mean_abs_reference_change_seconds": float(np.mean(np.abs(next_q - prev_q))),
                "max_abs_reference_change_seconds": float(np.max(np.abs(next_q - prev_q))),
                "mean_event_rmse_log": float(np.mean([p["rmse_log"] for p in current_params])),
                "mean_event_r2": float(np.mean([p["r2"] for p in current_params])),
            }
        )
        current_times_by_event = transformed_by_event

    reference_curves = pd.concat(references, ignore_index=True)
    reference_curves.insert(0, "age_group", age_group)
    reference_curves.insert(0, "sex", sex)
    reference_curves.insert(0, "modality", MODALITY)
    return reference_curves, pd.DataFrame(params), pd.DataFrame(iteration_summary)


def plot_final_references(final_refs: pd.DataFrame, sex: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(16, 9))
    age_groups = sorted(final_refs["age_group"].unique(), key=age_group_key)
    cmap = plt.get_cmap("turbo")
    for idx, age_group in enumerate(age_groups):
        g = final_refs[(final_refs["age_group"] == age_group) & (final_refs["reference"] == f"Iteration {N_ITERATIONS}")]
        if g.empty:
            continue
        ax.plot(
            g["total_seconds"] / 60,
            g["performance_percentile"],
            linewidth=2.2,
            alpha=0.92,
            label=age_group,
            color=cmap(idx / max(1, len(age_groups) - 1)),
        )

    ax.set_title(f"WT {MODALITY} final reference curves through 2025 - {sex_label(sex)}", fontsize=18)
    ax.set_xlabel("Total time (h:mm)")
    ax.set_ylabel("Performance percentile (higher = faster)")
    ax.set_ylim(0, 100)
    final = final_refs[final_refs["reference"] == f"Iteration {N_ITERATIONS}"]
    add_time_axis(ax, final["total_seconds"].min(), final["total_seconds"].max())
    ax.set_yticks(np.arange(0, 101, 20))
    ax.grid(True, color="#d7dee7", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=10, frameon=False, title="Age group")
    fig.tight_layout(rect=[0, 0, 0.84, 1])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    df = pd.read_excel(INPUT_FILE, sheet_name="Canonical_Results")
    base = df[(df["modality"] == MODALITY) & df[METRIC].notna() & (df[METRIC] > 0)].copy()
    base["age_group"] = base["age_group"].astype(str)
    base["age_group"] = base["age_group"].replace({"70+": "70-74"})

    all_refs = []
    all_params = []
    all_summary = []
    group_summary = []

    for sex in ["F", "M"]:
        age_groups = ["All"] + sorted(base.loc[base["sex"] == sex, "age_group"].unique(), key=age_group_key)
        for age_group in age_groups:
            if age_group == "All":
                source = base[base["sex"] == sex].copy()
            else:
                source = base[(base["sex"] == sex) & (base["age_group"] == age_group)].copy()
            event_counts = source.groupby("year").size()
            if len(source) < 20 or (event_counts >= MIN_EVENT_RECORDS).sum() < 2:
                group_summary.append(
                    {
                        "modality": MODALITY,
                        "sex": sex,
                        "age_group": age_group,
                        "records": len(source),
                        "events": int((event_counts >= MIN_EVENT_RECORDS).sum()),
                        "status": "Skipped: insufficient data",
                    }
                )
                continue

            references, params, summary = build_reference_for_group(source, sex, age_group)
            all_refs.append(references)
            all_params.append(params)
            all_summary.append(summary)
            group_summary.append(
                {
                    "modality": MODALITY,
                    "sex": sex,
                    "age_group": age_group,
                    "records": len(source),
                    "events": int((event_counts >= MIN_EVENT_RECORDS).sum()),
                    "status": "Built",
                }
            )

            initial_ref = references[references["reference"] == "Initial raw pool"]
            plot_typicality(
                source,
                initial_ref,
                sex,
                age_group,
                DIAG_DIR / f"WT_{MODALITY}_{sex}_{age_group}_Event_Curves_Initial_Reference.png",
            )

    reference_curves = pd.concat(all_refs, ignore_index=True)
    params = pd.concat(all_params, ignore_index=True)
    iteration_summary = pd.concat(all_summary, ignore_index=True)
    group_summary_df = pd.DataFrame(group_summary)

    for sex in ["F", "M"]:
        plot_final_references(
            reference_curves[reference_curves["sex"] == sex],
            sex,
            FINAL_DIR / f"WT_{MODALITY}_{sex}_Final_Reference_Curves_All_Age_Groups.png",
        )

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        reference_curves.to_excel(writer, index=False, sheet_name="Reference_Curves")
        params.to_excel(writer, index=False, sheet_name="Event_Transform_Params")
        iteration_summary.to_excel(writer, index=False, sheet_name="Iteration_Summary")
        group_summary_df.to_excel(writer, index=False, sheet_name="Group_Summary")

    print(f"workbook={OUT_XLSX}")
    print(group_summary_df.to_string(index=False))
    print("\nIteration 2 summary")
    print(iteration_summary[iteration_summary["iteration"] == N_ITERATIONS][["sex", "age_group", "records", "events", "mean_abs_reference_change_seconds", "mean_event_r2"]].to_string(index=False))
    print(f"diagnostic_figures={DIAG_DIR}")
    print(f"final_figures={FINAL_DIR}")


if __name__ == "__main__":
    main()
