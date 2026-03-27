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
    retrieve_memory --> synthesize_email_insights
    synthesize_email_insights --> orchestration_agent

    orchestration_agent -->|selected_agent=recruiter| recruiter_draft
    orchestration_agent -->|selected_agent=scheduling| scheduling_draft
    orchestration_agent -->|selected_agent=academic| academic_draft
    orchestration_agent -->|selected_agent=support| support_draft
    orchestration_agent -->|selected_agent=billing| billing_draft
    orchestration_agent -->|selected_agent=general| generate_draft

    recruiter_draft --> recruiter_extract
    recruiter_extract --> persist_knowledge_memory

    scheduling_draft --> scheduling_extract
    scheduling_extract --> persist_knowledge_memory

    academic_draft --> academic_extract
    academic_extract --> persist_knowledge_memory

    support_draft --> support_extract
    support_extract --> persist_knowledge_memory

    billing_draft --> billing_extract
    billing_extract --> persist_knowledge_memory

    generate_draft --> extract_tasks
    extract_tasks --> persist_knowledge_memory
    persist_knowledge_memory --> score_confidence

    score_confidence --> risk_gate
    risk_gate --> human_review_interrupt
    human_review_interrupt --> finalize_output
    finalize_output --> END([END])
```

## Specialist Agent Paths

Each specialist path has the same shape inside the main graph:

```mermaid
flowchart LR
    orchestration_agent --> specialist_draft
    specialist_draft --> specialist_extract
    specialist_extract --> persist_knowledge_memory
    persist_knowledge_memory --> score_confidence
```

### Recruiter Agent

```mermaid
flowchart LR
    orchestration_agent --> recruiter_draft["recruiter_draft_reply()"]
    recruiter_draft --> recruiter_extract["recruiter_extract_tasks()"]
    recruiter_extract --> persist_knowledge_memory
```

### Scheduling Agent

```mermaid
flowchart LR
    orchestration_agent --> scheduling_draft["scheduling_draft_reply()"]
    scheduling_draft --> scheduling_extract["scheduling_extract_tasks()"]
    scheduling_extract --> persist_knowledge_memory
```

### Academic Agent

```mermaid
flowchart LR
    orchestration_agent --> academic_draft["academic_draft_reply()"]
    academic_draft --> academic_extract["academic_extract_tasks()"]
    academic_extract --> persist_knowledge_memory
```

### Support Agent

```mermaid
flowchart LR
    orchestration_agent --> support_draft["support_draft_reply()"]
    support_draft --> support_extract["support_extract_tasks()"]
    support_extract --> persist_knowledge_memory
```

### Billing Agent

```mermaid
flowchart LR
    orchestration_agent --> billing_draft["billing_draft_reply()"]
    billing_draft --> billing_extract["billing_extract_tasks()"]
    billing_extract --> persist_knowledge_memory
```

## General (Non-Specialist) Fallback Path

```mermaid
flowchart LR
    orchestration_agent --> generate_draft["draft_reply()"]
    generate_draft --> extract_tasks["extract_tasks()"]
    extract_tasks --> persist_knowledge_memory
    persist_knowledge_memory --> score_confidence
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

