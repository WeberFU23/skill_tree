# Running LoCoMo Skill Tree Experiments

This fork keeps the original MemSkill flat operation-bank path and adds a
directory-backed skill tree path.

## 1. Original MemSkill Path

Run the existing flat operation-bank baseline:

```bash
source ~/.config/skill_tree/env.sh
bash scripts/train_locomo_flat_memskill.sh
bash scripts/eval_locomo_flat_memskill.sh
```

For real runs, avoid typing the key directly in commands. Store it once in a
private shell file outside the repo:

```bash
mkdir -p ~/.config/skill_tree
umask 077
read -rsp "DeepSeek API key: " DEEPSEEK_API_KEY
printf '\n'
printf 'export DEEPSEEK_API_KEY=%q\n' "$DEEPSEEK_API_KEY" > ~/.config/skill_tree/env.sh
unset DEEPSEEK_API_KEY
chmod 600 ~/.config/skill_tree/env.sh
grep -qxF 'source ~/.config/skill_tree/env.sh' ~/.bashrc || \
  printf '\n# skill_tree secrets\nsource ~/.config/skill_tree/env.sh\n' >> ~/.bashrc
source ~/.config/skill_tree/env.sh
```

The scripts read `DEEPSEEK_API_KEY` from the environment and do not pass it as
`--api-key`, so it is not exposed in the process command line. API error logs
also redact the key.

## 2. Skill Tree Path

Run the PPO skill-tree router over `skills_memory/`:

```bash
source ~/.config/skill_tree/env.sh
bash scripts/train_locomo_skilltree_negmem_autoevolve.sh
bash scripts/eval_locomo_skilltree_negmem.sh
```

To run the same skill-tree path with the original MemSkill operation-bank
designer also enabled, use the explicit designer experiment:

```bash
source ~/.config/skill_tree/env.sh
bash scripts/train_locomo_skilltree_negmem_designer_autoevolve.sh
bash scripts/eval_locomo_skilltree_negmem_designer.sh
```

Note: in the skill-tree path, the effective skill editor is
`--enable-skill-tree-evolution`; legacy `--enable-designer` evolves the flat
operation bank and is therefore tracked as an ablation rather than the default
performance path.

The designer ablation reads negative memories by default but does not write new
ones into `negative_memories/`. If you intentionally want it to auto-record more
negative lessons, opt in explicitly:

```bash
AUTO_RECORD_NEGATIVE_MEMORY=1 NEGATIVE_MEMORY_WRITE_LIMIT=20 \
  bash scripts/train_locomo_skilltree_negmem_designer_autoevolve.sh
```

The important flags are:

```bash
--enable-skill-tree
--skill-tree-dir ./skills_memory
--enable-skill-tree-evolution
--enable-negative-memory
--negative-memory-dir ./negative_memories
--auto-record-negative-memory
```

`skills_memory/` contains executable memory skills:

- `insert`
- `insert_negative_lesson`
- `update`
- `delete`
- `noop`

To run the matching skill-tree checkpoint without loading negative memories,
use the ablation script:

```bash
bash scripts/eval_locomo_skilltree_nonegmem.sh
```

Do not hand-write this ablation from `main.py` defaults unless you also pass the
same checkpoint encoder flags used by training:

```bash
--state-encoder sentence-transformers/all-MiniLM-L6-v2
--op-encoder sentence-transformers/all-MiniLM-L6-v2
```

The PPO checkpoint stores controller weights sized for those encoders.

To test whether negative memory retrieval is adding noise, sweep the prompt
guardrail count and optional similarity threshold:

```bash
NEGATIVE_MEMORY_TOP_K=1 bash scripts/eval_locomo_skilltree_negmem.sh
NEGATIVE_MEMORY_TOP_K=2 bash scripts/eval_locomo_skilltree_negmem.sh
NEGATIVE_MEMORY_TOP_K=3 bash scripts/eval_locomo_skilltree_negmem.sh
NEGATIVE_MEMORY_TOP_K=3 NEGATIVE_MEMORY_MIN_SCORE=0.35 bash scripts/eval_locomo_skilltree_negmem.sh
```

`NEGATIVE_MEMORY_MIN_SCORE` filters out retrieved negative memories below the
embedding/keyword similarity score. Leave it unset to preserve the original
top-k behavior.

For the standard LoCoMo sweep, run:

```bash
bash scripts/sweep_locomo_skilltree_negmem_topk.sh
```

It evaluates:

- `no_negative`
- `top1`
- `top2`
- `top3`
- `top3_score035`

Each case writes its result JSON and log under
`results/negative_memory_sweep_<timestamp>/`, plus a `summary.tsv` with F1 and
LLM Judge.

The repository root still has compatibility wrappers such as
`train_locomo_skill_tree.sh`, but new experiments should use the descriptive
scripts under `scripts/`. See `scripts/README.md` for the naming rule:
`<phase>_<dataset>_<method>_<variant>.sh`.

Latest negative-memory sweep on the 40-entry store:

| Case | F1 | LLM Judge | Readout |
| --- | ---: | ---: | --- |
| no negative | 0.1852 | 0.2357 | lower bound |
| top1 | 0.1993 | 0.2707 | helps over no negative |
| top2 | 0.2204 | 0.3041 | best in this sweep |
| top3 | 0.1925 | 0.2596 | too much prompt noise |
| top3 + min score 0.35 | 0.1403 | 0.1975 | threshold too strict |

Raw-store conclusion: use negative memory, but limit retrieval to
`NEGATIVE_MEMORY_TOP_K=2` before doing deeper quality filtering. The raw
LoCoMo skill-tree train/eval scripts default to top-2 negative memories.

## 3. Current Performance and Analysis Path

The designer ablation did not improve test performance because legacy
`--enable-designer` refines the flat operation bank, while the active skill-tree
path executes markdown nodes under `skills_memory/`. Its useful diagnosis was
tested by strengthening `insert.md`, but the clean raw40 ablation still
underperformed baseline.

The 2026-05-16 repeat changed the current decision point: raw negative-memory
top-2 is the stronger stable baseline, while curated aggregate memory remains an
analysis path until its category-2/category-3 drop is explained.

Run the current stable raw top-2 evaluation:

```bash
bash scripts/eval_locomo_skilltree_negmem.sh
```

Run the curated aggregate evaluation for comparison:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055.sh
```

To test whether curated negative memories are hurting by crossing LoCoMo QA
categories, run the category-matched ablation:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055_catmatch.sh
```

This passes `--negative-memory-match-category`, so QA evaluation only retrieves
negative memories tagged with the current question category, for example
`category_2` lessons for category-2 questions. Memory construction still uses
the normal query-only retrieval because chunks do not have QA categories.

The single catmatch run improved category 2/3 but hurt category 1/4. To test
the narrower policy suggested by that result, match only category 2 and 3:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055_cat23match.sh
```

Equivalent generic form:

```bash
NEGATIVE_MEMORY_MATCH_CATEGORIES="2 3" \
  bash scripts/eval_locomo_skilltree_negmem_curated_agg055.sh
```

If the single run is promising, repeat the selective policy:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_curated_agg055_cat23match.sh
```

The category-2/3 repeat shows most of the useful signal in category 3, while
category 2 remains weak. To isolate that signal, run category-3 matching only:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055_cat3match.sh
```

If the single run is promising, repeat it:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_curated_agg055_cat3match.sh
```

Latest all-category catmatch single run:

| Config | F1 | LLM Judge | Readout |
| --- | ---: | ---: | --- |
| curated agg055 top1/1200 + all-category match | 0.2014 | 0.2580 | category 2/3 stayed strong, but category 1/4 dropped |
| curated agg055 top1/1200 + category 2/3 match only | 0.2188 | 0.3089 | stronger single-run result; repeat before promoting |

Latest category-2/3 selective repeat on 2026-05-18:

| Config | F1 mean +/- std | LLM Judge mean +/- std | Readout |
| --- | ---: | ---: | --- |
| curated agg055 top1/1200 + category 2/3 match only | 0.2105 +/- 0.0185 | 0.2983 +/- 0.0314 | strong Judge, but F1 does not clearly beat ordinary curated repeat |

Category readout for that repeat:

| Config | Cat 1 F1 / Judge | Cat 2 F1 / Judge | Cat 3 F1 / Judge | Cat 4 F1 / Judge |
| --- | ---: | ---: | ---: | ---: |
| curated agg055 top1/1200 + category 2/3 match only | 0.1449 / 0.2416 | 0.1746 / 0.1308 | 0.5129 / 0.5667 | 0.2156 / 0.3573 |

The category table suggests category 2 is not the source of the gain. Category
3 remains the clearest target for the next selective-matching ablation.

Latest category-3-only selective repeat on 2026-05-18:

| Config | F1 mean +/- std | LLM Judge mean +/- std | Readout |
| --- | ---: | ---: | --- |
| curated agg055 top1/1200 + category 3 match only | 0.2100 +/- 0.0198 | 0.2930 +/- 0.0228 | similar F1 to category-2/3 matching but lower Judge; not a better default |

Category readout from the category-3-only repeat:

| Config | Cat 1 F1 / Judge | Cat 2 F1 / Judge | Cat 3 F1 / Judge | Cat 4 F1 / Judge |
| --- | ---: | ---: | ---: | ---: |
| curated agg055 top1/1200 + category 3 match only | 0.1460 / 0.2415 | 0.1966 / 0.1744 | 0.5620 / 0.5750 | 0.1990 / 0.3281 |

Category-3-only matching improves category 3 relative to category-2/3 matching,
but the overall gain is canceled by category 4 and run variance. Keep selective
category matching as a diagnostic path, not as the stable default.

To summarize categories for a selective repeat:

```bash
python -B scripts/summarize_locomo_repeat_categories.py \
  results/repeat_locomo_skilltree_curated_agg055_cat23match_YYYYMMDD_HHMMSS/summary.tsv \
  --config-name curated_agg055_cat23match_top1_chars1200
```

For category-3-only repeats, use:

```bash
python -B scripts/summarize_locomo_repeat_categories.py \
  results/repeat_locomo_skilltree_curated_agg055_cat3match_YYYYMMDD_HHMMSS/summary.tsv \
  --config-name curated_agg055_cat3match_top1_chars1200
```

Then sweep curated negative-memory prompt budget:

```bash
bash scripts/sweep_locomo_skilltree_curated_negmem_budget.sh
```

The sweep searches:

- top-k: `1`, `2`, `3`
- max chars per negative memory: `900`, `1200`, `1800`

Latest curated budget sweep on `curated_negative_memories_agg055`:

| Case | F1 | LLM Judge | Readout |
| --- | ---: | ---: | --- |
| top1, 900 chars | 0.2230 | 0.3153 | strong, compact |
| top1, 1200 chars | 0.2286 | 0.3312 | best single-run curated setting |
| top1, 1800 chars | 0.1946 | 0.2914 | too verbose |
| top2, 900 chars | 0.2040 | 0.2548 | extra retrieved lesson added noise |
| top2, 1200 chars | 0.2018 | 0.2707 | below top1 |
| top2, 1800 chars | 0.2119 | 0.3010 | below top1 |
| top3, 1200 chars | 0.2072 | 0.2850 | below top1 |
| top3, 1800 chars | 0.2149 | 0.3105 | below top1 |

Current curated comparison setting: `NEGATIVE_MEMORY_TOP_K=1` and
`NEGATIVE_MEMORY_MAX_CHARS=1200`. It remains useful for analysis, but the
three-run repeat below makes raw top2 the current stable baseline.

Because memory construction and LLM judging are not fully deterministic, repeat
the current best setting before treating a single score as conclusive:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_negmem_curated_agg055.sh
```

To compare the three core LoCoMo conditions with repeated mean/std in one run,
use:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_core_configs.sh
```

This runs:

- `no_negative`
- raw negative memory `top2`
- curated aggregate memory `curated_negative_memories_agg055`, `top1`, `1200` chars

After it finishes, summarize category-wise means from the produced logs:

```bash
python -B scripts/summarize_locomo_repeat_categories.py \
  results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/summary.tsv
```

To compare curated agg055 against raw top2 category-by-category:

```bash
python -B scripts/compare_locomo_repeat_configs.py \
  results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/category_summary.tsv \
  --baseline raw_top2 \
  --candidate curated_agg055_top1_chars1200
```

New eval-only runs also save detailed per-question JSON to `OUT_FILE`. After
rerunning the repeat script with this code, compare raw top2 and curated at the
question level:

```bash
python -B scripts/compare_locomo_repeat_questions.py \
  --summary-tsv results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/summary.tsv \
  --baseline-config raw_top2 \
  --candidate-config curated_agg055_top1_chars1200 \
  --categories 2 3
```

This writes a TSV ranked by candidate-minus-baseline F1, including the question,
gold answer, both predictions, QA-retrieved memories, and retrieved negative
memories. Use it to inspect why curated loses category 2 and category 3.

After creating a question comparison TSV, summarize which retrieved negative
memories are associated with candidate wins and losses:

```bash
python -B scripts/summarize_negative_memory_question_impacts.py \
  results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/question_compare_curated_agg055_top1_chars1200_vs_raw_top2.tsv

column -t -s $'\t' \
  results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/question_compare_curated_agg055_top1_chars1200_vs_raw_top2_negative_memory_summary.tsv
```

The summary ranks lessons by mean F1 delta. Negative rows are the first
candidate lessons to inspect, rewrite, or filter from retrieval. The companion
`*_negative_memory_examples.tsv` file keeps concrete loss/win examples for each
lesson.

The 2026-05-18 question-level impact summary for raw top2 vs curated agg055
found three negative-mean curated aggregate lessons:

| Memory key | Rows | Wins | Losses | Mean delta F1 | Readout |
| --- | ---: | ---: | ---: | ---: | --- |
| `curated auto failure locomo conv-42 37` | 24 | 6 | 9 | -0.1115 | strongest negative candidate |
| `curated auto failure locomo conv-42 43` | 9 | 1 | 3 | -0.0923 | small but consistently harmful sample |
| `curated auto failure locomo conv-42 9` | 15 | 2 | 6 | -0.0451 | moderate negative candidate |

To test whether removing these lessons improves curated retrieval, build the
pruned directory and run the pruned eval:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055_pruned_bad3.sh
```

If the single run improves over ordinary curated agg055, repeat it:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_curated_agg055_pruned_bad3.sh
```

Latest pruned repeat on 2026-05-18/19:

| Config | F1 mean +/- std | LLM Judge mean +/- std | Readout |
| --- | ---: | ---: | --- |
| curated agg055 pruned bad3 top1/1200 | 0.2309 +/- 0.0169 | 0.3095 +/- 0.0106 | strongest current curated candidate; beats raw top2 on mean F1 and Judge, but still has Cat2 Judge weakness |

Category-wise readout for pruned bad3:

| Config | Cat 1 F1 / Judge | Cat 2 F1 / Judge | Cat 3 F1 / Judge | Cat 4 F1 / Judge |
| --- | ---: | ---: | ---: | ---: |
| curated agg055 pruned bad3 top1/1200 | 0.1801 / 0.2874 | 0.2037 / 0.1154 | 0.5422 / 0.6167 | 0.2249 / 0.3594 |

Compared with the documented raw-top2 category repeat, pruned bad3 improves
category 1 and 4, is close on category 3, and remains weaker on category 2
Judge. The next diagnostic should compare pruned bad3 against raw top2 at the
question level:

```bash
python -B scripts/compare_locomo_repeat_questions.py \
  --summary-tsv \
    results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/summary.tsv \
    results/repeat_locomo_skilltree_curated_agg055_pruned_bad3_YYYYMMDD_HHMMSS/summary.tsv \
  --baseline-config raw_top2 \
  --candidate-config curated_agg055_pruned_bad3_top1_chars1200 \
  --categories 2
```

The Cat2 question-level comparison showed two negative-mean remaining lessons:

| Memory key | Rows | Wins | Losses | Mean delta F1 | Readout |
| --- | ---: | ---: | ---: | ---: | --- |
| `curated auto failure locomo conv-42 23` | 6 | 0 | 3 | -0.0707 | category-1 lesson retrieved for category-2 questions; safest next prune |
| `curated auto failure locomo conv-42 35` | 87 | 25 | 21 | -0.0342 | broad high-recall lesson; do not prune until isolated |

The next conservative pruning test removes only `conv-42 23` on top of bad3:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated_agg055_pruned_bad4.sh
```

If the single run is promising, repeat it:

```bash
REPEATS=3 bash scripts/repeat_locomo_skilltree_curated_agg055_pruned_bad4.sh
```

The bad4 repeat did not validate the single-run improvement:

| Config | F1 mean +/- std | LLM Judge mean +/- std | Readout |
| --- | ---: | ---: | --- |
| curated agg055 pruned bad4 top1/1200 | 0.2011 +/- 0.0173 | 0.2585 +/- 0.0298 | worse than bad3; do not promote |

Bad4 is an important negative result. Removing `conv-42 23` looked reasonable
from category-2 attribution, but repeat showed that the remaining 4-memory
store became too sparse/noisy. Keep `pruned_bad3` as the current best curated
candidate.

With the negative-memory route fixed at pruned bad3, run the next
skill-tree-evolution ablation in an isolated skill-tree copy:

```bash
bash scripts/train_locomo_skilltree_pruned_bad3_autoevolve_isolated.sh
```

This script copies `skills_memory/` into a timestamped result directory, trains
with `--enable-skill-tree-evolution`, uses `curated_negative_memories_agg055_pruned_bad3`,
and disables new negative-memory writes by default. After it finishes, use the
`EVAL_COMMANDS.txt` written in the run directory to evaluate the evolved skill
tree.

If the single eval is promising, repeat-evaluate the produced checkpoint before
promoting it. If `RUN_DIR` is omitted, the script uses the newest
`results/skill_tree_evolution_pruned_bad3_*` directory:

```bash
RUN_DIR=results/skill_tree_evolution_pruned_bad3_YYYYMMDD_HHMMSS \
  REPEATS=3 bash scripts/repeat_locomo_skilltree_pruned_bad3_evolved_checkpoint.sh
```

Interpret this carefully: if `diff -ru skills_memory "$RUN_DIR/skills_memory"`
has no output, the skill-tree markdown did not evolve. Any gain then comes from
the trained checkpoint, not from new skill definitions.

Latest core-config repeat on 2026-05-16:

| Config | F1 mean +/- std | LLM Judge mean +/- std | Readout |
| --- | ---: | ---: | --- |
| no negative | 0.1756 +/- 0.0049 | 0.2458 +/- 0.0134 | lower bound |
| raw top2 | 0.2254 +/- 0.0091 | 0.2850 +/- 0.0013 | best stable setting in this repeat |
| curated agg055 top1, 1200 chars | 0.1897 +/- 0.0194 | 0.2691 +/- 0.0251 | unstable and below raw top2 in repeat |

Category-wise readout from the same repeat:

| Config | Cat 1 F1 / Judge | Cat 2 F1 / Judge | Cat 3 F1 / Judge | Cat 4 F1 / Judge |
| --- | ---: | ---: | ---: | ---: |
| no negative | 0.1563 / 0.2343 | 0.1072 / 0.0897 | 0.3239 / 0.4917 | 0.1931 / 0.2833 |
| raw top2 | 0.1483 / 0.2440 | 0.2102 / 0.1359 | 0.5576 / 0.6500 | 0.2234 / 0.3177 |
| curated agg055 top1, 1200 chars | 0.1426 / 0.2271 | 0.1358 / 0.1180 | 0.4747 / 0.5333 | 0.1962 / 0.3156 |

This repeat supersedes the single curated sweep high as the current decision
point: keep curated aggregate memory as an analysis path, but use raw top2 as
the stronger stable baseline until question-level analysis explains the curated
drop. The largest curated losses are category 2 and category 3, so the next
diagnostic should inspect which curated lessons were retrieved for those
queries.

## 4. Curated Negative-Memory Run

Automatic training failures are useful but noisy. Before increasing top-k, build
a curated representative set:

```bash
bash scripts/curate_locomo_skilltree_negmem.sh
```

This reads `negative_memories/`, clusters near-duplicate mistake patterns, writes
representatives to `curated_negative_memories/`, and creates a markdown report
under `results/negative_memory_curation_<timestamp>.md`.
Curated entries aggregate concrete source corrections from each cluster instead
of keeping only one representative failure.

Evaluate the curated set with:

```bash
bash scripts/eval_locomo_skilltree_negmem_curated.sh
```

For custom directories:

```bash
NEGATIVE_MEMORY_DIR=./curated_negative_memories \
  bash scripts/eval_locomo_skilltree_negmem.sh
```

Important curation knobs:

```bash
CURATION_SIMILARITY_THRESHOLD=0.55
CURATION_MAX_CURATED=30
CURATION_MAX_EXAMPLES_PER_CLUSTER=8
CURATION_MIN_CLUSTER_SIZE=1
CURATION_MIN_QUALITY=0
CURATION_OVERWRITE=1
```

## 5. Negative Memories

Negative memories are markdown lessons from mistakes or user corrections. They
are optional prompt guardrails and are loaded only when
`--enable-negative-memory` is passed.

Only markdown files with `type: negative` or a `negative` tag are loaded from
`negative_memories/`. Use the template in `negative_memories/README.md`.

Do not store hidden chain-of-thought. Store the reusable wrong pattern,
correction, trigger, and lesson.

You can record a user/evaluator correction dialogue directly:

```bash
python -B record_negative_memory.py \
  --dialogue-file ./correction_dialogue.txt \
  --title "entity recall correction" \
  --user-id "user_123" \
  --tag locomo
```

Use `--dialogue-file -` to read the dialogue from stdin, or `--dry-run` to
preview the generated fields without writing a markdown file.

`scripts/train_locomo_skilltree_negmem_autoevolve.sh` also passes
`--auto-record-negative-memory`, so training QA failures are written as compact
markdown lessons, up to `--negative-memory-write-limit`. Evaluation does not
write new negative memories, which avoids contaminating the test set with test
answers.

You can write one entry manually:

```bash
python -B record_negative_memory.py \
  --problem "The model answered A when the corrected answer was B." \
  --wrong-behavior "Ignored the user's explicit correction." \
  --correction "Use B when condition X appears." \
  --lesson "Check condition X before reusing answer A." \
  --trigger "Similar questions involving condition X" \
  --user-id "user_123" \
  --tag reasoning_error
```

## 6. Skill-Tree Hard-Case Evolution

`scripts/train_locomo_skilltree_negmem_autoevolve.sh` passes
`--enable-skill-tree-evolution`. During training, failed QA cases are grounded
back to the skill-tree paths that created the retrieved memories. At the end of
an outer epoch, the designer can refine an implicated skill node or add one
child node under it.

The script limits evolution to one hard-case bucket per run:

```bash
--skill-tree-evolution-min-cases 5
--skill-tree-evolution-max-buckets 1
```

This keeps the lite LoCoMo run cheap and avoids broad edits from a single small
experiment. Evolved markdown files are written under `skills_memory/`.
