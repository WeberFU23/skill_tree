# Project Status and Experiment Record

Last updated: 2026-05-11

## Project Goal

This project is a continuation of MemSkill-style agentic memory. The target is
long conversation memory QA: given past multi-session dialogue, build a memory
bank, retrieve useful memories at query time, and answer user questions more
accurately.

The senior requirement was to add a negative-memory mechanism:

- record past dialogue information and personal habits;
- more importantly, record mistakes and corrections from dialogue;
- let the model see prior wrong patterns during inference and avoid repeating
  them;
- keep memory as markdown with explicit negative labels;
- prefer a prompt-level implementation first, with reinforcement learning or
  fine-tuning left as a later direction.

This repository implements that requirement as markdown-backed negative memory
plus PPO skill-tree routing.

## Current System Logic

The original MemSkill path keeps a flat operation bank. This fork adds a
directory-backed skill tree under `skills_memory/`.

Main flow:

1. Load LoCoMo data from `data/locomo10.json`.
2. During training, use PPO to learn which memory operation skill to apply when
   constructing memory banks.
3. Memory operations are represented as markdown skill nodes, currently:
   `insert`, `insert_negative_lesson`, `update`, `delete`, and `noop`.
4. Failed training QA cases can be automatically written as negative-memory
   markdown lessons under `negative_memories/`.
5. At evaluation time, relevant negative memories are retrieved and injected
   into the prompt as guardrails.
6. Hard training cases can also be grouped by implicated skill-tree path and
   passed to a skill-tree evolution step.
7. Raw negative memories can be clustered and curated into aggregate markdown
   lessons with multiple concrete source corrections per cluster.

Negative memory is the prompt-level version of the idea:

```text
P(answer | context, retrieved_memory, retrieved_negative_memory)
```

It does not store hidden chain-of-thought. It stores reusable failure patterns:
problem, wrong behavior, correction, trigger, and lesson.

## Progress Compared With MemSkill

| Area | Original MemSkill Style | Current Project |
| --- | --- | --- |
| Operation structure | Flat operation bank | Hierarchical skill tree in markdown directories |
| Operation selection | Flat candidate selection | PPO routing over skill-tree nodes |
| Mistake learning | No persistent negative lesson store | Markdown negative-memory store with `type: negative` |
| User/evaluator corrections | Not a first-class artifact | `record_negative_memory.py` writes correction dialogues to memory |
| Training failures | Used only for reward/update | Can be auto-recorded as compact negative lessons |
| Test-time guardrails | Retrieved positive memories only | Retrieved positive memories plus negative-memory reminders |
| Skill improvement | Static operation definitions | Hard-case skill-tree evolution hook |
| Experiment hygiene | Ad hoc scripts | Standardized scripts in `scripts/` |
| Secret handling | API keys could appear in commands | Scripts read `DEEPSEEK_API_KEY` from environment |

## Implemented Components

- `src/negative_memory.py`: loads, retrieves, formats, and writes negative
  memory markdown files.
- `record_negative_memory.py`: records manual correction dialogue or structured
  failure descriptions as negative memories.
- `curate_negative_memories.py`: clusters raw negative memories and exports
  curated aggregate lessons.
- `src/trainer.py`: integrates negative-memory retrieval, auto-recording, and
  skill-tree hard-case evolution.
- `src/skill_tree_evolution.py`: groups hard cases and proposes skill-tree
  changes.
- `skills_memory/`: memory-operation skill tree.
- `scripts/`: standardized experiment entrypoints.

## Standard Scripts

| Script | Purpose |
| --- | --- |
| `scripts/train_locomo_flat_memskill.sh` | Original flat MemSkill LoCoMo baseline |
| `scripts/eval_locomo_flat_memskill.sh` | Evaluate flat MemSkill LoCoMo baseline |
| `scripts/train_locomo_skilltree_negmem_autoevolve.sh` | Train skill-tree PPO with negative-memory auto-recording and hard-case evolution |
| `scripts/train_locomo_skilltree_negmem_designer_autoevolve.sh` | Train skill-tree PPO with negative memory, legacy designer, and hard-case evolution |
| `scripts/eval_locomo_skilltree_negmem.sh` | Evaluate skill-tree checkpoint with negative memory |
| `scripts/eval_locomo_skilltree_negmem_designer.sh` | Evaluate the designer-enabled skill-tree checkpoint |
| `scripts/eval_locomo_skilltree_nonegmem.sh` | Ablation: same checkpoint without negative memory |
| `scripts/sweep_locomo_skilltree_negmem_topk.sh` | Sweep negative-memory top-k and score threshold |
| `scripts/curate_locomo_skilltree_negmem.sh` | Cluster raw negative memories into curated aggregate lessons |
| `scripts/eval_locomo_skilltree_negmem_curated.sh` | Evaluate curated negative-memory directory |
| `scripts/eval_locomo_skilltree_negmem_curated_agg055.sh` | Run the best-known curated aggregate evaluation setting, defaulting to top-1 and 1200 chars |
| `scripts/repeat_locomo_skilltree_negmem_curated_agg055.sh` | Repeat the best-known curated aggregate setting and report mean/std |
| `scripts/repeat_locomo_skilltree_core_configs.sh` | Repeat the three key LoCoMo comparison configs: no negative, raw top-2, and curated agg055 top-1/1200 |
| `scripts/summarize_locomo_repeat_categories.py` | Parse repeat logs and aggregate LoCoMo category-wise F1 / LLM Judge means |
| `scripts/compare_locomo_repeat_configs.py` | Compare category-wise deltas between two repeat configs, e.g. curated agg055 vs raw top-2 |
| `scripts/compare_locomo_repeat_questions.py` | Compare detailed per-question eval JSON outputs between two configs |
| `scripts/sweep_locomo_skilltree_curated_negmem_budget.sh` | Sweep curated negative-memory top-k and prompt budget |

## Experiment Record

The numbers below are from LoCoMo10 runs shown in terminal logs. The split is
small (`Train: 6, Val: 2, Test: 2`, 314 test queries), so treat the results as
development evidence rather than final paper-grade averages. DeepSeek judging
and memory construction also introduce run-to-run variance.

| Stage | Purpose | Condition | F1 | LLM Judge | Result |
| --- | --- | --- | ---: | ---: | --- |
| Initial checkpoint eval | Verify end-to-end run after PPO routing | Skill tree, cached memory eval | 0.1313 | 0.1656 | Pipeline worked but score was weak |
| Fresh memory eval 1 | Recompute memory banks instead of using old cache | Skill tree, top-1 action/memory eval | 0.2108 | 0.3089 | Fresh memory construction improved score |
| Fresh memory eval 2 | Check repeat run variance | Same as above | 0.2222 | 0.2946 | Similar F1, judge varied |
| Auto negative-memory training | Test whether training failures can be recorded and reused | 20 auto-recorded negative memories | 0.2623 | 0.3567 | Best early score; negative lessons looked useful |
| Skill-tree hard-case evolution | Let hard cases propose skill-node changes | 40 raw negative memories, evolution enabled in train | 0.2173 | 0.2930 | Evolution hook ran; no strong gain in this short run |
| No-negative ablation | Measure same skill-tree checkpoint without negative-memory retrieval | `eval_locomo_skilltree_nonegmem.sh` | 0.1933 | 0.2277 | Removing negative memory hurt performance |
| Negative-memory sweep | Find useful top-k | no negative | 0.1852 | 0.2357 | Lower bound for sweep |
| Negative-memory sweep | Test small guardrail context | top1 | 0.1993 | 0.2707 | Better than no negative |
| Negative-memory sweep | Test default guardrail count | top2 | 0.2204 | 0.3041 | Best sweep setting |
| Negative-memory sweep | Test larger guardrail context | top3 | 0.1925 | 0.2596 | Too much negative context added noise |
| Negative-memory sweep | Test score threshold | top3 + min score 0.35 | 0.1403 | 0.1975 | Threshold was too strict |
| Standard top2 eval | Confirm current default script behavior | raw 40-entry negative store, top2 | 0.2156 | 0.2930 | Stable improvement over no-negative ablation |
| Curated representative eval | Test deduplicated negative memory | threshold 0.55, 8 representative memories | 0.2003 | 0.2691 | Too compressed; lost useful examples |
| Curated representative eval | Test looser curation | threshold 0.75, 29 representative memories | 0.2019 | 0.2882 | Better than 0.55 but below raw top2 |
| Aggregate curated eval | Preserve multiple examples per mistake cluster | threshold 0.55, 8 aggregate memories | 0.2249 | 0.2946 | Best curated F1; aggregation fixed much of the compression loss |
| Curated budget sweep | Optimize aggregate negative-memory retrieval budget | `curated_negative_memories_agg055`, top1, 1200 chars | 0.2286 | 0.3312 | Best current LoCoMo result in the small development split |
| Curated best-setting repeat 1 | Re-run the selected default after making it the standard script | `curated_negative_memories_agg055`, top1, 1200 chars | 0.2121 | 0.2882 | Lower than the sweep high point, confirming run-to-run variance |
| Core-config repeat | Repeat no-negative, raw top2, and curated agg055 top1/1200 three times | no negative mean/std | 0.1756 +/- 0.0049 | 0.2458 +/- 0.0134 | Lower bound remained stable |
| Core-config repeat | Repeat no-negative, raw top2, and curated agg055 top1/1200 three times | raw top2 mean/std | 0.2254 +/- 0.0091 | 0.2850 +/- 0.0013 | Best stable setting in this repeat |
| Core-config repeat | Repeat no-negative, raw top2, and curated agg055 top1/1200 three times | curated agg055 top1/1200 mean/std | 0.1897 +/- 0.0194 | 0.2691 +/- 0.0251 | Curated setting was unstable and below raw top2 |
| Core-config category summary | Diagnose where raw top2 beats curated agg055 | Category 2 F1 mean: raw top2 vs curated | 0.2102 vs 0.1358 | 0.1359 vs 0.1180 | Curated lost much of raw top2's category-2 gain |
| Core-config category summary | Diagnose where raw top2 beats curated agg055 | Category 3 F1 mean: raw top2 vs curated | 0.5576 vs 0.4747 | 0.6500 vs 0.5333 | Curated also lost the largest category-3 gain |
| Core-config category comparison | Quantify curated-minus-raw deltas by category | Categories 1/2/3/4 | -0.0057 / -0.0744 / -0.0829 / -0.0272 F1 | -0.0169 / -0.0179 / -0.1167 / -0.0021 Judge | Curated lost to raw in every category; category 2 and 3 are the priority diagnostics |
| Designer-enabled ablation | Test original MemSkill designer together with skill-tree + negative memory | `--enable-designer`, raw negative top2 | 0.2016 | 0.2627 | Did not improve test score; the legacy designer refined the flat `operation_bank.insert`, while the active skill-tree path uses `skills_memory/` |
| Insert trigger tuning check | Test stronger entity-fact insertion wording after designer diagnosis | tuned `skills_memory/.../insert.md`, raw negative store had grown to 60 entries | 0.1189 | 0.1688 | Not a clean comparison; the raw negative-memory store was polluted by 20 extra auto-recorded failures and became much noisier |
| Insert trigger tuning clean check | Re-test stronger entity-fact insertion wording after restoring the raw negative store to 40 entries | tuned `skills_memory/.../insert.md`, raw negative top2 | 0.1907 | 0.2675 | Clean comparison still underperformed raw top2 baseline, so the insert tuning was reverted |

## Current Conclusions

1. The project has implemented the senior's requested negative-memory path:
   markdown negative lessons, training-failure recording, manual correction
   recording, prompt injection, and continuous update hooks.
2. Negative memory helps only when retrieval is controlled. Top-2 performed best
   in the sweep; top-3 added prompt noise.
3. Raw auto-recorded negative memories are useful but noisy. Simple
   representative-only curation lost important correction details.
4. Aggregate curated memories are more promising because one curated lesson can
   keep multiple concrete `Question -> Expected` examples from the cluster.
5. Skill-tree evolution is wired, but the current short LoCoMo run did not prove
   a clear improvement from evolved skill definitions.
6. The legacy MemSkill `--enable-designer` can now be run as an explicit
   skill-tree ablation. In the current architecture it evolves the flat
   operation bank, while the skill-tree execution path is edited by
   `--enable-skill-tree-evolution`.
7. The designer ablation still produced a useful diagnosis: failures were
   concentrated around missing entity-specific facts. Directly migrating that
   diagnosis into stronger `insert.md` wording was tested, but the clean raw40
   ablation underperformed baseline, so the tuning was reverted.
8. Raw negative-memory accumulation can hurt performance. The 60-entry raw store
   produced a much worse run after the designer ablation auto-recorded 20 more
   failures. Designer ablation training now makes negative-memory auto-recording
   opt-in so future runs remain comparable by default.
9. The curated budget sweep found the strongest single-run setting:
   `curated_negative_memories_agg055`, top-1 negative memory, and 1200
   characters per retrieved lesson. This reached F1 0.2286 and LLM Judge 0.3312.
10. Core-config repeat on 2026-05-16 changed the current decision point: raw
    negative memory top2 averaged F1 0.2254 +/- 0.0091 and LLM Judge
    0.2850 +/- 0.0013, while curated agg055 top1/1200 averaged only F1
    0.1897 +/- 0.0194 and LLM Judge 0.2691 +/- 0.0251.
11. Category-wise summary shows the curated drop is concentrated in category 2
    and category 3. Raw top2 preserved strong gains in both, while curated
    agg055 lost much of that improvement.
12. The current stable baseline is raw top2. Curated aggregate memory remains an
    analysis path, but it should not be treated as the default performance path
    until question-level analysis explains and fixes the repeat drop.
13. Eval-only now writes detailed per-question JSON to `OUT_FILE`, including the
    question, gold answer, prediction, F1, LLM Judge score, retrieved QA
    memories, and retrieved negative-memory guardrails. This makes the next
    optimization loop inspectable instead of relying only on log averages.

## Recommended Next Experiments

1. Rerun the core repeat with the detailed-output code, then compare raw top2 vs
   curated agg055 at the query level to locate why curated hurts category 2 and
   category 3:

   ```bash
   REPEATS=3 bash scripts/repeat_locomo_skilltree_core_configs.sh
   python -B scripts/compare_locomo_repeat_questions.py \
     --summary-tsv results/repeat_locomo_skilltree_core_configs_YYYYMMDD_HHMMSS/summary.tsv \
     --baseline-config raw_top2 \
     --candidate-config curated_agg055_top1_chars1200 \
     --categories 2 3
   ```
2. Inspect curated aggregate markdown files manually and remove misleading or
   test-leaking lessons if any appear.
3. Use `scripts/compare_locomo_repeat_configs.py` on repeat summaries before
   accepting future curated changes.
4. Run on a larger split or another long-memory benchmark after the small
   LoCoMo10 development loop is stable.
5. Keep fine-tuning/RL over negative examples as a later phase. The current
   prompt-level negative-memory mechanism is the cheaper and more inspectable
   first implementation.

## Git and Experiment Artifact Notes

Git tracks source code, scripts, prompts, skill markdown, and documentation.
It intentionally ignores generated experiment artifacts:

- `checkpoints/`
- `logs/`
- `results/`
- `wandb/`
- `curated_negative_memories*/`
- generated `negative_memories/*.md`

Therefore, a remote server working directory can contain more experiment
folders than GitHub or a local clone. Those folders are not part of the
repository state.

`git pull` does not overwrite ignored or untracked artifact directories just
because they are absent from GitHub. They remain in the working directory. A
pull would only fail or conflict if GitHub later starts tracking a file at the
same path as an existing untracked artifact. Destructive cleanup commands such
as `git clean -fdx` or scripts that write with overwrite flags are what can
delete or replace ignored artifacts.
