# Knowledge Graph Memory (Phase 1)

This project now includes a persistent knowledge graph layer stored in the relational DB.

## Goals

- Persist cross-thread memory per user.
- Capture lightweight entities and relations from processed emails.
- Retrieve recent graph context for routing and drafting.

## Data Model

### `knowledge_entities`

- `user_id`: owner of the memory
- `entity_type`: e.g. `person`, `intent`, `topic`, `task_item`
- `canonical_name`: display value
- `normalized_key`: dedupe key (`lower/trim`)
- `confidence`: extraction confidence
- `metadata` (JSON): optional attributes

Uniqueness: `(user_id, entity_type, normalized_key)`

### `knowledge_relations`

- `user_id`
- `source_entity_id`, `target_entity_id`
- `relation_type`: e.g. `HAS_INTENT`, `CONTACTED_ABOUT`, `REQUESTED_ACTION`
- `confidence`
- `evidence_message_id`, `evidence_thread_id`
- `metadata` (JSON)

## Workflow Integration

In `main_graph`:

1. `retrieve_memory` now fetches:
   - user preferences (existing)
   - recent knowledge graph context (`knowledge_graph` memory hit)
2. `synthesize_email_insights` runs next (see `app/graphs/kg_email_insights.py`):
   - Uses the LLM plus KG snapshot + preferences + email text to populate:
     - `email_context` — narrative context grounded in memory/graph when relevant
     - `email_summary` — short neutral summary
     - `follow_ups` — suggested next steps for the recipient
   - Draft nodes (general + specialists) prepend this block via `build_draft_user_message`.
3. `persist_knowledge_memory` runs after task extraction in both specialist and general paths.
3. Extracted entities/relations are committed via `KnowledgeGraphService.persist_from_state`.

## Notes

- This is a practical phase-1 schema for durability and retrieval.
- Next phase can add:
  - richer ontology (`Organization`, `Commitment`, `Meeting`, `Issue`)
  - temporal validity windows (`valid_from`, `valid_to`)
  - hybrid GraphRAG retrieval (vector + graph neighborhood)
