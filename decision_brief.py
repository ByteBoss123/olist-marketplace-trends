"""Build an operations decision brief from the historical test predictions."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent


def main():
    scores = pd.read_csv(ROOT / "results/test_order_scores.csv")
    metrics = json.loads((ROOT / "results/late_risk_metrics.json").read_text())
    ranked = scores.sort_values(["late_risk", "order_id"], ascending=[False, True])
    n, late = len(ranked), int(ranked.late.sum())
    lines = ["# Operations decision brief", "",
        "**Decision:** how much review capacity should be allocated to orders ranked by late-delivery risk?",
        "", "This is a retrospective batch evaluation on Jan–Aug 2018 orders, not a deployed intervention.",
        "Training uses only orders purchased and delivered before 2018; all smoothed history features use prior delivered outcomes.",
        "", "| Review capacity | Orders reviewed | Late orders found | Late share in queue | Share of all late orders | Random selection: expected late orders |",
        "|---|---:|---:|---:|---:|---:|"]
    for frac in (.05, .10, .20):
        k = max(1, int(n * frac))
        caught = int(ranked.head(k).late.sum())
        lines.append(f"| {frac:.0%} | {k:,} | {caught:,} | {caught/k:.1%} | {caught/late:.1%} | {k*late/n:.1f} |")
    lines += ["", "Random-selection counts are expectations, not simulated or observed interventions.", "",
        "## Equal-capacity model comparison", "",
        "| Method | PR-AUC | Late orders found in top 10% |",
        "|---|---:|---:|"]
    for name, result in metrics["test"].items():
        lines.append(f"| {name} | {result['pr_auc']:.3f} | {result['top10pct']['late_caught']} |")
    lines += ["", "## Recommendation and limits", "",
        "Pilot a human-reviewed risk queue before choosing an intervention. Keep logistic regression as a serious simpler alternative: its overall ranking quality is close to gradient boosting.",
        "The top-10% gradient-boosting queue misses most late orders and contains many orders that arrive on time. Risk is not proof of a delivery failure.",
        "This batch ranking assumes the whole evaluation cohort is available; a live queue needs a daily capacity rule evaluated separately.",
        "No measured reduction in delays, financial savings, business adoption, or causal effect is claimed.",
        "The delivered-only cohort excludes unresolved/cancelled orders; late test months are subject to end-of-dataset censoring.",
        "Monitor outcome calibration as well as input drift. Document reviewer feedback and measure an intervention prospectively before claiming operational impact.", ""]
    (ROOT / "results/decision_brief.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
