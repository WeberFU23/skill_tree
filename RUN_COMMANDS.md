# Running LoCoMo Skill Tree Experiments

This fork keeps the original MemSkill flat operation-bank path and adds a
directory-backed skill tree path.

## 1. Original MemSkill Path

Run the existing flat operation-bank baseline:

```bash
source ~/.config/skill_tree/env.sh
bash train_locomo.sh
bash eval_locomo.sh
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
bash train_locomo_skill_tree.sh
bash eval_locomo_skill_tree.sh
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
bash eval_locomo_skill_tree_no_negative.sh
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
NEGATIVE_MEMORY_TOP_K=1 bash eval_locomo_skill_tree.sh
NEGATIVE_MEMORY_TOP_K=2 bash eval_locomo_skill_tree.sh
NEGATIVE_MEMORY_TOP_K=3 bash eval_locomo_skill_tree.sh
NEGATIVE_MEMORY_TOP_K=3 NEGATIVE_MEMORY_MIN_SCORE=0.35 bash eval_locomo_skill_tree.sh
```

`NEGATIVE_MEMORY_MIN_SCORE` filters out retrieved negative memories below the
embedding/keyword similarity score. Leave it unset to preserve the original
top-k behavior.

## 3. Negative Memories

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

`train_locomo_skill_tree.sh` also passes `--auto-record-negative-memory`, so
training QA failures are written as compact markdown lessons, up to
`--negative-memory-write-limit`. Evaluation does not write new negative
memories, which avoids contaminating the test set with test answers.

## 4. Skill-Tree Hard-Case Evolution

`train_locomo_skill_tree.sh` passes `--enable-skill-tree-evolution`. During
training, failed QA cases are grounded back to the skill-tree paths that created
the retrieved memories. At the end of an outer epoch, the designer can refine an
implicated skill node or add one child node under it.

The script limits evolution to one hard-case bucket per run:

```bash
--skill-tree-evolution-min-cases 5
--skill-tree-evolution-max-buckets 1
```

This keeps the lite LoCoMo run cheap and avoids broad edits from a single small
experiment. Evolved markdown files are written under `skills_memory/`.

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
