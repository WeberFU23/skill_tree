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
| `eval_locomo_skilltree_nonegmem.sh` | LoCoMo skill-tree evaluation without negative memory retrieval |
| `sweep_locomo_skilltree_negmem_topk.sh` | LoCoMo negative-memory top-k / score-threshold sweep |
| `curate_locomo_skilltree_negmem.sh` | Cluster raw LoCoMo negative memories and export aggregate curated representatives |
| `train_alfworld_flat_designer.sh` | Original flat operation-bank ALFWorld designer training |
| `eval_alfworld_flat_designer.sh` | Original flat operation-bank ALFWorld designer evaluation |
| `eval_hotpotqa_flat_designer.sh` | Original flat operation-bank HotpotQA designer evaluation |
| `eval_longmemeval_flat_designer.sh` | Original flat operation-bank LongMemEval designer evaluation |

The repository root keeps compatibility wrappers with the old names. New
experiments should add scripts here using the naming convention above.
