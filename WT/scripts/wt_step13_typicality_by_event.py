from __future__ import annotations

import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MultipleLocator


BASE = Path(__file__).resolve().parents[1]
INPUT_FILE = BASE / "outputs" / "WT_Triathlon_Sprint_Standard_Canonical_1989_2025.xlsx"
OUTPUT_DIR = BASE / "outputs"
FIG_DIR = BASE / "Figures" / "WT" / "Typicality_By_Event"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "WT_Typicality_By_Event_Modality_Sex_AgeGroup_1989_2025.xlsx"

PLOT_MIN_N = 8
QUANTILE_PROBS = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
CURVE_POINTS_MAX = 250


def safe_name(value: object) -> str:
    text = str(value)
    text = re.sub(r"[^\w\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:120]


def seconds_to_hms(seconds: float) -> str:
    if not np.isfinite(seconds):
        return ""
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}:{m:02d}:{s:02d}"


def minute_tick(value: float, _pos: int) -> str:
    total = int(round(value * 60))
    h = total // 3600
    m = (total % 3600) // 60
    return f"{h}:{m:02d}"


def empirical_curve(times_seconds: pd.Series) -> pd.DataFrame:
    values = np.sort(pd.to_numeric(times_seconds, errors="coerce").dropna().to_numpy(dtype=float))
    values = values[np.isfinite(values) & (values > 0)]
    n = len(values)
    if n == 0:
        return pd.DataFrame(columns=["total_seconds", "total_minutes", "competitive_percentile"])
    if n > CURVE_POINTS_MAX:
        idx = np.unique(np.round(np.linspace(0, n - 1, CURVE_POINTS_MAX)).astype(int))
        values = values[idx]
        ranks = idx + 1
    else:
        ranks = np.arange(1, n + 1)
    # Faster times correspond to higher competitive percentile.
    competitive_percentile = 100 * (1 - (ranks - 0.5) / n)
    return pd.DataFrame(
        {
            "total_seconds": values,
            "total_minutes": values / 60,
            "competitive_percentile": competitive_percentile,
        }
    )


def quantile_record(values: pd.Series) -> dict[str, float | str | int]:
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    if len(arr) == 0:
        return {}
    quantiles = np.quantile(arr, QUANTILE_PROBS)
    out: dict[str, float | str | int] = {"n": int(len(arr))}
    for p, q in zip(QUANTILE_PROBS, quantiles):
        label = f"p{int(round(p * 100)):02d}"
        out[f"{label}_seconds"] = float(q)
        out[f"{label}_time"] = seconds_to_hms(float(q))
        out[f"log_{label}"] = float(math.log(q))
    return out


def plot_group(group: pd.DataFrame, modality: str, sex: str, age_group: str) -> str | None:
    valid_years = [
        (year, data)
        for year, data in group.groupby("year")
        if len(data) >= PLOT_MIN_N
    ]
    if not valid_years:
        return None

    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=150)
    cmap = plt.get_cmap("viridis")
    years = [year for year, _ in valid_years]
    denom = max(1, len(years) - 1)
    for i, (year, data) in enumerate(valid_years):
        curve = empirical_curve(data["total_seconds"])
        alpha = 0.35 if len(valid_years) > 10 else 0.55
        lw = 1.1 if len(data) >= 30 else 0.8
        ax.plot(
            curve["total_minutes"],
            curve["competitive_percentile"],
            color=cmap(i / denom),
            alpha=alpha,
            linewidth=lw,
            label=str(year),
        )

    all_curve = empirical_curve(group["total_seconds"])
    ax.plot(
        all_curve["total_minutes"],
        all_curve["competitive_percentile"],
        color="black",
        linewidth=2.4,
        label="Pooled",
        zorder=10,
    )
    ax.set_title(f"WT {modality} {sex} {age_group}: empirical event curves by year")
    ax.set_xlabel("Total time (h:mm)")
    ax.set_ylabel("Competitive percentile")
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.grid(True, alpha=0.22)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_major_formatter(FuncFormatter(minute_tick))
    if len(valid_years) <= 14:
        ax.legend(ncol=2, fontsize=7, frameon=False)
    else:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(min(years), max(years)))
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, pad=0.02)
        cb.set_label("Year")
    fig.tight_layout()

    out_dir = FIG_DIR / modality / sex
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"WT_Typicality_{safe_name(modality)}_{safe_name(sex)}_{safe_name(age_group)}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def main() -> None:
    df = pd.read_excel(INPUT_FILE, sheet_name="Canonical_Results")
    df = df[df["total_seconds"].gt(0)].copy()
    df["total_seconds"] = pd.to_numeric(df["total_seconds"], errors="coerce")
    df = df[df["total_seconds"].gt(0)].copy()

    quantile_rows: list[dict] = []
    figure_rows: list[dict] = []

    group_cols = ["modality", "sex", "age_group"]
    event_cols = ["modality", "sex", "age_group", "year"]

    for keys, event in df.groupby(event_cols, dropna=False):
        modality, sex, age_group, year = keys
        record = {
            "modality": modality,
            "sex": sex,
            "age_group": age_group,
            "year": int(year),
            "source_files": "; ".join(sorted(event["source_file"].dropna().astype(str).unique())),
        }
        record.update(quantile_record(event["total_seconds"]))
        quantile_rows.append(record)

    quantiles = pd.DataFrame(quantile_rows)
    quantile_cols = [f"log_p{int(round(p * 100)):02d}" for p in QUANTILE_PROBS]

    typicality_rows: list[dict] = []
    for keys, sub in quantiles.groupby(group_cols, dropna=False):
        modality, sex, age_group = keys
        if len(sub) < 2:
            med = sub.copy()
            for c in quantile_cols:
                med[f"{c}_diff"] = 0.0
            reference = {c: float(sub[c].iloc[0]) for c in quantile_cols if c in sub}
        else:
            reference = {c: float(sub[c].median()) for c in quantile_cols if c in sub}
        for _, row in sub.iterrows():
            diffs = []
            for c in quantile_cols:
                if c in row and np.isfinite(row[c]) and c in reference and np.isfinite(reference[c]):
                    diffs.append(float(row[c] - reference[c]))
            rms_log_diff = float(np.sqrt(np.mean(np.square(diffs)))) if diffs else np.nan
            median_shift_pct = float((math.exp(row["log_p50"] - reference["log_p50"]) - 1) * 100) if "log_p50" in reference else np.nan
            spread_shift_pct = (
                float(
                    (
                        (row["log_p90"] - row["log_p10"])
                        - (reference["log_p90"] - reference["log_p10"])
                    )
                    * 100
                )
                if {"log_p10", "log_p90"}.issubset(reference)
                else np.nan
            )
            typicality_rows.append(
                {
                    "modality": modality,
                    "sex": sex,
                    "age_group": age_group,
                    "year": int(row["year"]),
                    "n": int(row["n"]),
                    "p10_time": row["p10_time"],
                    "p50_time": row["p50_time"],
                    "p90_time": row["p90_time"],
                    "median_shift_pct_vs_group": median_shift_pct,
                    "log_spread_p10_p90_shift_x100": spread_shift_pct,
                    "rms_log_quantile_diff": rms_log_diff,
                    "review_note": (
                        "low n"
                        if row["n"] < 20
                        else "large median shift"
                        if abs(median_shift_pct) >= 8
                        else "large shape shift"
                        if rms_log_diff >= 0.06
                        else ""
                    ),
                    "source_files": row["source_files"],
                }
            )

    typicality = pd.DataFrame(typicality_rows).sort_values(
        ["modality", "sex", "age_group", "rms_log_quantile_diff"],
        ascending=[True, True, True, False],
    )

    group_summary = (
        df.groupby(group_cols, dropna=False)
        .agg(
            records=("athlete_id", "size"),
            years=("year", "nunique"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
        .sort_values(group_cols)
    )

    for keys, group in df.groupby(group_cols, dropna=False):
        modality, sex, age_group = keys
        path = plot_group(group, str(modality), str(sex), str(age_group))
        if path:
            figure_rows.append(
                {
                    "modality": modality,
                    "sex": sex,
                    "age_group": age_group,
                    "records": len(group),
                    "years": group["year"].nunique(),
                    "figure_path": path,
                }
            )

    figures = pd.DataFrame(figure_rows).sort_values(["modality", "sex", "age_group"])
    readme = pd.DataFrame(
        [
            ("competitive_percentile", "Higher percentile means faster performance; P90 beats roughly 90% of athletes."),
            ("figure curves", f"Each annual curve is drawn when n >= {PLOT_MIN_N}; black curve is the pooled empirical curve for that modality/sex/age group."),
            ("rms_log_quantile_diff", "RMS difference between annual log-quantiles P5/P10/P25/P50/P75/P90/P95 and the group median quantile vector."),
            ("median_shift_pct_vs_group", "Positive means the annual median is slower than the typical group median; negative means faster."),
            ("review_note", "Heuristic flag only; final typicality decision should remain manual."),
        ],
        columns=["field", "definition"],
    )

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        readme.to_excel(writer, index=False, sheet_name="Readme")
        group_summary.to_excel(writer, index=False, sheet_name="Group_Summary")
        typicality.to_excel(writer, index=False, sheet_name="Event_Typicality")
        quantiles.to_excel(writer, index=False, sheet_name="Event_Quantiles")
        figures.to_excel(writer, index=False, sheet_name="Figure_Index")
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                values = [str(cell.value) for cell in col[:200] if cell.value is not None]
                width = min(max([len(v) for v in values] + [10]) + 2, 52)
                ws.column_dimensions[col[0].column_letter].width = width

    flagged = typicality[typicality["review_note"].ne("")]
    print(f"written={OUTPUT_FILE}")
    print(f"figures={len(figures)} dir={FIG_DIR}")
    print(f"event_curves={len(typicality)}")
    print(f"flagged_for_review={len(flagged)}")
    print("\nTop review candidates:")
    cols = ["modality", "sex", "age_group", "year", "n", "p50_time", "median_shift_pct_vs_group", "rms_log_quantile_diff", "review_note"]
    print(flagged.sort_values("rms_log_quantile_diff", ascending=False)[cols].head(30).to_string(index=False))


if __name__ == "__main__":
    main()
