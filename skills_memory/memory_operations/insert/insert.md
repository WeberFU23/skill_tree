---
id: memory_operations.insert
name: insert
visibility: shared
scope_id: null
tags: [memory, insert, durable-facts]
update_type: insert
---

# Insert Durable Memory

## Description

Memory skill for inserting new durable information that is useful beyond the
current text chunk and not already covered by retrieved memories.

## Purpose

Store new information that is stable, attributable, and likely to help future
reasoning or user-specific behavior.

## When To Use

- The text chunk introduces a durable fact, preference, event, plan, constraint,
  or reusable task detail.
- The text chunk introduces entity-specific factual details such as
  relationships, shared interests, recommendations, dates, achievements,
  physical changes, pet details, recipes, or ingredients.
- Retrieved memories do not already contain the same information.
- The information should remain useful after the current chunk is gone.

## How To Apply

- Compare the text chunk with retrieved memories to avoid duplicates.
- Keep each memory concise, specific, and grounded in the text.
- Preserve important entities, time, location, task state, cause, outcome, or
  constraints when they matter.
- Split unrelated facts into separate memory items.
- Explicitly store entity-specific factual details even if they seem minor,
  unless already covered by retrieved memories.

## Constraints

- Do not store raw private or episode-specific details as general skills.
- Do not store trivial, speculative, or one-off details unless they clearly
  affect future behavior.
- Do not update or delete existing memories.

## Output Action

Action type: INSERT only.
