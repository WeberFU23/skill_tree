# Project Layout and Remote Workflow

Last updated: 2026-05-11

## Canonical Layout

The repository should stay split between source-controlled project files and
local experiment artifacts.

Tracked project files:

```text
README.md
RUN_COMMANDS.md
docs/
scripts/
src/
prompts/
skills/
skills_memory/
data/
negative_memories/README.md
main.py
record_negative_memory.py
curate_negative_memories.py
```

Generated local artifacts:

```text
checkpoints/
logs/
results/
wandb/
experiment_artifacts/
curated_negative_memories*/
negative_memories/*.md
__pycache__/
*.pyc
```

Generated artifacts are ignored by Git. Keep them on the machine where the
experiment was run, or copy them into an external archive when they need to be
shared.

## Script Naming Rule

New experiment scripts belong under `scripts/` and use:

```text
<phase>_<dataset>_<method>_<variant>.sh
```

Examples:

```text
train_locomo_skilltree_negmem_autoevolve.sh
eval_locomo_skilltree_negmem.sh
sweep_locomo_skilltree_negmem_topk.sh
curate_locomo_skilltree_negmem.sh
```

Root-level `.sh` files are compatibility wrappers only. Do not add new
experiment logic to the repository root.

## Local And Remote Roles

The current workflow is:

- Local Windows checkout: has GitHub write permission, used for commits and
  pushes.
- Remote A800 checkout: has the GPU/runtime environment, used for training,
  evaluation, and artifact generation.

Because the remote GitHub identity may only have read permission, treat the
remote as a runner. Make code changes locally, push from local, then pull on the
remote before running new experiments.

## Sync Code To Remote

After pushing locally:

```bash
cd ~/wt/skill_tree
git fetch origin main
git merge --ff-only origin/main
git log --oneline -3
```

If HTTPS GitHub access fails on the remote, use SSH over port 443:

```bash
git remote set-url origin ssh://git@ssh.github.com:443/WeberFU23/skill_tree.git
git fetch origin main
git merge --ff-only origin/main
```

## Pull Safety With Local Artifacts

`git pull` updates tracked files only. It does not delete ignored experiment
directories just because GitHub does not have them.

Remote-only folders such as:

```text
curated_negative_memories_055/
curated_negative_memories_075/
curated_negative_memories_agg055/
results/negative_memory_sweep_*/
logs/
checkpoints/
```

will remain after normal `git pull`.

Cases to avoid:

- Do not run `git clean -fdx` unless you intentionally want to delete ignored
  experiment artifacts.
- Do not reuse an output directory with overwrite flags if you need to keep the
  previous run.
- If GitHub later tracks a file at the same path as an existing untracked
  artifact, `git pull` will usually stop with an error instead of silently
  overwriting it. Move or archive the artifact, then pull again.

## Recommended Experiment Artifact Names

Use names that encode dataset, method, condition, and date:

```text
results/negative_memory_sweep_YYYYMMDD_HHMMSS/
results/negative_memory_curation_YYYYMMDD_HHMMSS.md
curated_negative_memories_agg055_YYYYMMDD/
logs/locomo-skilltree-negmem-top2_YYYYMMDD_HHMMSS.log
```

For important runs, keep the command script plus summary metrics in Git, and
archive the large result directory outside Git.

## Quick Health Checks

Local or remote:

```bash
git status --short --branch
bash -n scripts/*.sh *.sh
python -B -m py_compile main.py record_negative_memory.py curate_negative_memories.py
```

Before pushing from local:

```bash
git diff --check
git status --short
```
