# Operations decision brief

**Decision:** how much review capacity should be allocated to orders ranked by late-delivery risk?

This is a retrospective batch evaluation on Jan–Aug 2018 orders, not a deployed intervention.
Training uses only orders purchased and delivered before 2018; all smoothed history features use prior delivered outcomes.

| Review capacity | Orders reviewed | Late orders found | Late share in queue | Share of all late orders | Random selection: expected late orders |
|---|---:|---:|---:|---:|---:|
| 5% | 2,638 | 498 | 18.9% | 12.2% | 203.8 |
| 10% | 5,277 | 892 | 16.9% | 21.9% | 407.7 |
| 20% | 10,555 | 1,479 | 14.0% | 36.3% | 815.6 |

Random-selection counts are expectations, not simulated or observed interventions.

## Equal-capacity model comparison

| Method | PR-AUC | Late orders found in top 10% |
|---|---:|---:|
| seller_history_only | 0.072 | 346 |
| logistic_regression | 0.131 | 777 |
| gradient_boosting | 0.132 | 892 |

## Recommendation and limits

Pilot a human-reviewed risk queue before choosing an intervention. Keep logistic regression as a serious simpler alternative: its overall ranking quality is close to gradient boosting.
The top-10% gradient-boosting queue misses most late orders and contains many orders that arrive on time. Risk is not proof of a delivery failure.
This batch ranking assumes the whole evaluation cohort is available; a live queue needs a daily capacity rule evaluated separately.
No measured reduction in delays, financial savings, business adoption, or causal effect is claimed.
The delivered-only cohort excludes unresolved/cancelled orders; late test months are subject to end-of-dataset censoring.
Monitor outcome calibration as well as input drift. Document reviewer feedback and measure an intervention prospectively before claiming operational impact.
