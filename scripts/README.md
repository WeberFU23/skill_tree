# Experiment Script Naming

Scripts in this directory use:

```text
<phase>_<dataset>_<method>_<variant>.sh
```

- `phase`: `train`, `eval`, `sweep`, or `curate`
- `dataset`: `locomo`, `alfworld`, `hotpotqa`, `longmemeval`
- `method`: main system path, such as `flat_memskill`, `skilltree`, or `flat_designer`
- `variant`: key experimental condition, such as `negmem`, `nonegmem`, `autoevolve`, or `topk`

Current scripts:

| Script | Purpose |
| --- | --- |
| `train_locomo_flat_memskill.sh` | Original flat MemSkill LoCoMo baseline training |
| `eval_locomo_flat_memskill.sh` | Original flat MemSkill LoCoMo baseline evaluation |
| `train_locomo_skilltree_negmem_autoevolve.sh` | LoCoMo skill-tree training with negative memory auto-recording and skill-tree hard-case evolution |
| `train_locomo_skilltree_negmem_designer_autoevolve.sh` | LoCoMo skill-tree training with negative memory, legacy operation-bank designer, and skill-tree hard-case evolution; auto-recording is opt-in |
| `eval_locomo_skilltree_negmem.sh` | LoCoMo skill-tree evaluation with negative memory retrieval |
| `eval_locomo_skilltree_negmem_designer.sh` | Evaluate the checkpoint produced by the designer-enabled skill-tree run |
| `eval_locomo_skilltree_negmem_curated.sh` | LoCoMo skill-tree evaluation with curated negative memory retrieval |
| `eval_locomo_skilltree_negmem_curated_agg055.sh` | Current best-known curated aggregate LoCoMo evaluation entrypoint; defaults to top-1 negative memory with 1200 chars |
| `eval_locomo_skilltree_negmem_curated_agg055_catmatch.sh` | Curated agg055 ablation that restricts QA-time negative memories to the current LoCoMo category tag |
| `eval_locomo_skilltree_negmem_curated_agg055_cat23match.sh` | Curated agg055 ablation that restricts QA-time negative memories only for LoCoMo category 2 and 3 |
| `eval_locomo_question_router_v2_end2end.sh` | True LoCoMo question-router v2 eval entrypoint; routes each question to pruned bad3 or evolved checkpoint before answer generation |
| `repeat_locomo_skilltree_negmem_curated_agg055.sh` | Repeat the current best-known curated aggregate LoCoMo evaluation and report mean/std |
| `repeat_locomo_skilltree_curated_agg055_cat23match.sh` | Repeat the selective category-2/3 matched curated aggregate LoCoMo ablation |
| `repeat_locomo_skilltree_core_configs.sh` | Repeat the three key LoCoMo comparison configs: no negative, raw top-2, and curated agg055 top-1/1200 |
| `repeat_locomo_question_router_v2_end2end.sh` | Repeat the true question-router v2 eval and write a normal repeat `summary.tsv` |
| `analyze_question_router_v2_end2end.sh` | Analyze the true question-router v2 repeat with category summaries, parent comparisons, and a markdown report |
| `compare_question_router_end2end_versions.sh` | Compare two true end-to-end router repeats, e.g. v3 minus v2, with question/category/reason deltas |
| `summarize_locomo_repeat_categories.py` | Parse repeat logs and aggregate LoCoMo category-wise F1 / LLM Judge means |
| `compare_locomo_repeat_configs.py` | Compare category-wise deltas between two repeat configs, e.g. curated agg055 vs raw top-2 |
| `compare_locomo_repeat_questions.py` | Compare detailed question-level JSON outputs between two configs, including retrieved memory and negative-memory context |
| `eval_locomo_skilltree_nonegmem.sh` | LoCoMo skill-tree evaluation without negative memory retrieval |
| `sweep_locomo_skilltree_negmem_topk.sh` | LoCoMo negative-memory top-k / score-threshold sweep |
| `sweep_locomo_skilltree_curated_negmem_budget.sh` | Sweep curated negative-memory top-k and prompt character budget |
| `curate_locomo_skilltree_negmem.sh` | Cluster raw LoCoMo negative memories and export aggregate curated representatives |
| `train_alfworld_flat_designer.sh` | Original flat operation-bank ALFWorld designer training |
| `eval_alfworld_flat_designer.sh` | Original flat operation-bank ALFWorld designer evaluation |
| `eval_hotpotqa_flat_designer.sh` | Original flat operation-bank HotpotQA designer evaluation |
| `eval_longmemeval_flat_designer.sh` | Original flat operation-bank LongMemEval designer evaluation |

The repository root keeps compatibility wrappers with the old names. New
experiments should add scripts here using the naming convention above.
