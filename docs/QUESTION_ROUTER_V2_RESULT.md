# Question Router v2 Result

## Summary

`question_router_risk_profile_baseline_v2` is the current best LoCoMo10
development result: F1 0.2447 +/- 0.0026, LLM Judge 0.3296 +/- 0.0060.

It improves over pruned bad3 (0.2309 / 0.3095) and the evolved checkpoint
(0.2377 / 0.3217). The result is a materialized question-text router assembled
from repeated baseline and evolved-checkpoint outputs, not a single-pass
end-to-end eval.

The corresponding true end-to-end router repeat is now available as
`question_router_risk_profile_baseline_v2_end2end`: F1 0.2424 +/- 0.0204,
LLM Judge 0.3530 +/- 0.0248. That is the formal method result; the table below
keeps the materialized diagnostic because it explains why the route was chosen.

A conservative v3 end-to-end repeat was also tested after pruning the harmful
`what kind of` and `would ... prefer` baseline routes. It scored F1
0.2350 +/- 0.0032 and LLM Judge 0.3471 +/- 0.0107 with only 17/314 questions
routed to the baseline. This is more conservative but weaker than v2, so v2
remains the current formal router.

The direct v3-minus-v2 comparison shows why v3 should stay an ablation:
Cat1 improves slightly (+0.0041 F1, +0.0193 Judge), but Cat2, Cat3, and Cat4
drop on F1, with Cat3 taking the largest hit (-0.0469 F1, -0.0750 Judge).
The next narrow ablation is `risk_profile_baseline_v4`: remove only
`what kind of`, but keep the v2 `would ... prefer` route.

That v4 ablation was tested twice and did not beat v2. The latest true
end-to-end repeat scored F1 0.2371 +/- 0.0183 and LLM Judge
0.3317 +/- 0.0190, with 19/314 questions routed to the baseline. Directly
against v2, v4 improves Cat2 F1 (+0.0253) but loses Cat1, Cat3, and Cat4;
the Cat3 loss (-0.0508 F1, -0.0667 Judge) is enough to reject it.

## Formal End-to-End Repeats

| Config | n | F1 Mean | F1 Std | Judge Mean | Judge Std | Baseline Rows |
| --- | --- | --- | --- | --- | --- | --- |
| pruned_bad3 | 3 | 0.2309 | 0.0169 | 0.3095 | 0.0106 | 314 |
| evolved_checkpoint | 3 | 0.2377 | 0.0103 | 0.3217 | 0.0145 | 0 |
| question_router_risk_profile_baseline_v2_end2end | 3 | 0.2424 | 0.0204 | 0.3530 | 0.0248 | 35 |
| question_router_risk_profile_baseline_v3_end2end | 3 | 0.2350 | 0.0032 | 0.3471 | 0.0107 | 17 |
| question_router_risk_profile_baseline_v4_end2end | 3 | 0.2371 | 0.0183 | 0.3317 | 0.0190 | 19 |

## Materialized Diagnostic Overall

| Config | n | F1 Mean | F1 Std | Judge Mean | Judge Std |
| --- | --- | --- | --- | --- | --- |
| pruned_bad3 | 3 | 0.2309 | 0.0169 | 0.3095 | 0.0106 |
| evolved_checkpoint | 3 | 0.2377 | 0.0103 | 0.3217 | 0.0145 |
| question_router_risk_profile_baseline_v2 | 3 | 0.2447 | 0.0026 | 0.3296 | 0.0060 |

## Router Categories

| Category | n | F1 Mean | F1 Std | Judge Mean | Judge Std |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0.1691 | 0.0214 | 0.2826 | 0.0103 |
| 2 | 3 | 0.2177 | 0.0242 | 0.1769 | 0.0655 |
| 3 | 3 | 0.5602 | 0.0456 | 0.6500 | 0.0736 |
| 4 | 3 | 0.2489 | 0.0038 | 0.3719 | 0.0135 |

## Router vs Pruned Bad3

| Category | Rows | Wins | Losses | Ties | Delta F1 | Delta Judge | Sum F1 | Sum Judge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 207 | 35 | 38 | 134 | -0.0110 | -0.0048 | -2.2852 | -1.0000 |
| 2 | 195 | 50 | 61 | 84 | +0.0140 | +0.0615 | +2.7385 | +12.0000 |
| 3 | 60 | 12 | 8 | 40 | +0.0180 | +0.0333 | +1.0798 | +2.0000 |
| 4 | 480 | 134 | 120 | 226 | +0.0240 | +0.0125 | +11.5319 | +6.0000 |

## Router vs Evolved Checkpoint

| Category | Rows | Wins | Losses | Ties | Delta F1 | Delta Judge | Sum F1 | Sum Judge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 207 | 17 | 16 | 174 | +0.0058 | +0.0121 | +1.1972 | +2.5000 |
| 2 | 195 | 2 | 1 | 192 | +0.0026 | +0.0000 | +0.5091 | +0.0000 |
| 3 | 60 | 6 | 1 | 53 | +0.0860 | +0.0833 | +5.1587 | +5.0000 |
| 4 | 480 | 6 | 8 | 466 | -0.0006 | +0.0000 | -0.2646 | +0.0000 |

## Readout

- The router's main value over the evolved checkpoint is Cat3 recovery.
- Cat2 and Cat4 mostly preserve the evolved checkpoint gains.
- Cat1 remains the main residual weakness relative to pruned bad3.
- The same question-text rules now have an end-to-end eval entrypoint:
  `REPEATS=3 bash scripts/repeat_locomo_question_router_v2_end2end.sh`.
- The first end-to-end repeat validates the method path: F1 remains above both
  parents and close to the materialized diagnostic, while Judge becomes the
  strongest repeated score so far.
- The v3 conservative pruning pass improved stability but reduced headline F1
  and Judge relative to v2; keep v3 as an ablation, not the promoted method.
- Use `scripts/compare_question_router_end2end_versions.sh` to inspect direct
  v3-minus-v2 question-level deltas before changing router rules again.
- `risk_profile_baseline_v4` isolates the next test: v2 minus only the
  `what kind of` route, retaining `would ... prefer`. It also fails to beat
  v2, mainly because Cat3 and Judge regress.
- Stop promoting router micro-prunes on LoCoMo10; use v2 for the formal method
  until larger-split validation says otherwise.
