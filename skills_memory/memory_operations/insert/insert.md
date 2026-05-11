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

Memory skill for inserting new durable information about entities, attributes,
relations, events, dates, quantities, preferences, or constraints that is useful
beyond the current text chunk and not already covered by retrieved memories.

## Purpose

Store new information that is stable, attributable, and likely to help future
reasoning or user-specific behavior.

## When To Use

- The text chunk introduces a durable fact, preference, event, plan, constraint,
  or reusable task detail.
- The text chunk adds a new attribute or relation for a named entity, including
  people, pets, places, events, groups, objects, or recurring activities.
- The text chunk includes a specific date, time, quantity, count, list item,
  title, location, award, teammate, friend, family relation, allergy, hobby,
  gift, purchase, recipe, ingredient, or other detail that may be asked later.
- A known entity appears again and the chunk says something new about that
  entity, even if the detail seems small.
- Retrieved memories do not already contain the same information.
- The information should remain useful after the current chunk is gone.

## How To Apply

- Identify named entities in the chunk, then compare retrieved memories for
  existing facts about each entity.
- If the chunk adds a new attribute, relation, event, date, quantity, list item,
  or preference for an entity, store it as a separate concise memory.
- Preserve exact entity names, dates, numbers, titles, temporal markers, and
  relation words. Do not replace them with vague summaries.
- Split unrelated facts into separate memory items, especially when a sentence
  mentions multiple people, pets, hobbies, teammates, allergies, gifts, or
  events.
- Prefer complete atomic facts over broad summaries. For example, store each
  hobby, allergy, teammate, award, or gift separately when they are distinct.
- Explicitly store entity-specific factual details even if they seem minor,
  unless already covered by retrieved memories.

## Constraints

- Do not store raw private or episode-specific details as general skills.
- Do not store trivial, speculative, or one-off details unless they clearly
  affect future behavior.
- Do not update or delete existing memories.

## Output Action

Action type: INSERT only.
