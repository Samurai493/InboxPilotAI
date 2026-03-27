# InboxPilot State Graphs

This document shows how state flows through the system:

- Main LangGraph workflow
- Specialist branches
- General fallback branch
- API entrypoints that invoke/read graph state

## Main Workflow Graph

```mermaid
flowchart TD
    START([START]) --> ingest_message
    ingest_message --> normalize_message
    normalize_message --> classify_intent
    classify_intent --> retrieve_memory
    retrieve_memory --> route_to_specialist

    route_to_specialist -->|intent=recruiter| recruiter_draft
    route_to_specialist -->|intent=scheduling| scheduling_draft
    route_to_specialist -->|intent=academic| academic_draft
    route_to_specialist -->|intent=support| support_draft
    route_to_specialist -->|intent=billing| billing_draft
    route_to_specialist -->|intent=personal/spam/other OR use_specialist=false| generate_draft

    recruiter_draft --> recruiter_extract
    recruiter_extract --> score_confidence

    scheduling_draft --> scheduling_extract
    scheduling_extract --> score_confidence

    academic_draft --> academic_extract
    academic_extract --> score_confidence

    support_draft --> support_extract
    support_extract --> score_confidence

    billing_draft --> billing_extract
    billing_extract --> score_confidence

    generate_draft --> extract_tasks
    extract_tasks --> score_confidence

    score_confidence --> risk_gate
    risk_gate --> human_review_interrupt
    human_review_interrupt --> finalize_output
    finalize_output --> END([END])
```

## Specialist Agent Paths

Each specialist path has the same shape inside the main graph:

```mermaid
flowchart LR
    route_to_specialist --> specialist_draft
    specialist_draft --> specialist_extract
    specialist_extract --> score_confidence
```

### Recruiter Agent

```mermaid
flowchart LR
    route_to_specialist --> recruiter_draft["recruiter_draft_reply()"]
    recruiter_draft --> recruiter_extract["recruiter_extract_tasks()"]
    recruiter_extract --> score_confidence
```

### Scheduling Agent

```mermaid
flowchart LR
    route_to_specialist --> scheduling_draft["scheduling_draft_reply()"]
    scheduling_draft --> scheduling_extract["scheduling_extract_tasks()"]
    scheduling_extract --> score_confidence
```

### Academic Agent

```mermaid
flowchart LR
    route_to_specialist --> academic_draft["academic_draft_reply()"]
    academic_draft --> academic_extract["academic_extract_tasks()"]
    academic_extract --> score_confidence
```

### Support Agent

```mermaid
flowchart LR
    route_to_specialist --> support_draft["support_draft_reply()"]
    support_draft --> support_extract["support_extract_tasks()"]
    support_extract --> score_confidence
```

### Billing Agent

```mermaid
flowchart LR
    route_to_specialist --> billing_draft["billing_draft_reply()"]
    billing_draft --> billing_extract["billing_extract_tasks()"]
    billing_extract --> score_confidence
```

## General (Non-Specialist) Fallback Path

```mermaid
flowchart LR
    route_to_specialist --> generate_draft["draft_reply()"]
    generate_draft --> extract_tasks["extract_tasks()"]
    extract_tasks --> score_confidence
```

This path is used when:

- `use_specialist == false`, or
- classified intent is not one of `recruiter|scheduling|academic|support|billing`.

## Review Gate Behavior

```mermaid
flowchart TD
    score_confidence --> risk_gate
    risk_gate -->|human_review_required=false| finalize_output
    risk_gate -->|human_review_required=true| human_review_interrupt
    human_review_interrupt -->|resume decision| finalize_output
```

## API to Graph Interaction

```mermaid
flowchart TD
    process["POST /api/v1/process"] --> graph_service["GraphService.process_message()"]
    graph_service --> invoke["graph.invoke(initial_state, config)"]
    invoke --> result["thread_id + state + status/error"]

    get_thread["GET /api/v1/threads/{thread_id}"] --> read_state["GraphService.get_thread_state()"]
    read_state --> checkpoint["graph.get_state(config)"]
```

