# Question Router v2 Result

## Summary

`question_router_risk_profile_baseline_v2` is the current best LoCoMo10
development result: F1 0.2447 +/- 0.0026, LLM Judge 0.3296 +/- 0.0060.

It improves over pruned bad3 (0.2309 / 0.3095) and the evolved checkpoint
(0.2377 / 0.3217). The result is a materialized question-text router assembled
from repeated baseline and evolved-checkpoint outputs, not a single-pass
end-to-end eval.

## Overall

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
  Use that repeat to validate whether the materialized diagnostic holds when
  routing happens before answer generation.
