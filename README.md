# Skill Tree Memory Experiments

This repository extends the original MemSkill-style memory workflow with a
hierarchical skill tree and markdown-backed negative memories.

The current main experiment target is LoCoMo long-context memory QA. The system
learns how to build memory banks from conversation sessions, retrieves memories
for test-time QA, and uses negative memories as prompt guardrails for known
failure patterns.

## What Is Added

- Directory-backed memory skill tree under `skills_memory/`
- PPO controller routing over hierarchical memory operations
- Markdown negative memory store under `negative_memories/`
- Automatic training-failure recording as negative memories
- Curated negative-memory clustering and aggregation workflow
- Optional QA-time category matching for all or selected LoCoMo categories
- Hard-case-driven skill-tree evolution during training
- Detailed per-question LoCoMo eval JSON for error analysis
- Standardized experiment scripts under `scripts/`

## Main Scripts

Use the descriptive scripts in `scripts/` for new runs:

```bash
source ~/.config/skill_tree/env.sh

bash scripts/train_locomo_skilltree_negmem_autoevolve.sh
bash scripts/eval_locomo_skilltree_negmem.sh
bash scripts/sweep_locomo_skilltree_negmem_topk.sh
bash scripts/curate_locomo_skilltree_negmem.sh
bash scripts/eval_locomo_skilltree_negmem_curated.sh
```

The repository root keeps old script names as compatibility wrappers only.

See:

- `RUN_COMMANDS.md` for runnable commands and environment setup.
- `scripts/README.md` for script naming conventions.
- `docs/PROJECT_LAYOUT_AND_REMOTE_WORKFLOW.md` for repository layout,
  artifact rules, and local/remote synchronization.
- `docs/PROJECT_STATUS_AND_EXPERIMENTS.md` for project status, method summary,
  experiment results, and next steps.

## Repository Layout

```text
.
├── data/                    # Small checked-in development datasets
├── docs/                    # Project status, experiment notes, workflow docs
├── negative_memories/        # Template only; generated .md lessons are ignored
├── prompts/                 # Prompt templates
├── scripts/                 # Canonical train/eval/sweep/curation entrypoints
├── skills/                  # Skill-evolution instruction tree
├── skills_memory/           # Memory-operation skill tree
├── src/                     # Core implementation
├── main.py                  # Main experiment driver
├── record_negative_memory.py
├── curate_negative_memories.py
└── RUN_COMMANDS.md
```

## Artifact Policy

Training and evaluation outputs are intentionally not tracked by Git:

- `checkpoints/`
- `logs/`
- `results/`
- `wandb/`
- `curated_negative_memories*/`
- generated `negative_memories/*.md`

These directories are local experiment artifacts. Keep code, scripts, prompts,
skill definitions, and documentation in Git; archive large or run-specific
outputs separately when needed.
