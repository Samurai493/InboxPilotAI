---
name: performance-latency-testing
description: Produces a fixed latency report every run—executive summary, ranked table, bottlenecks, wins, follow-ups, and narrative—by measuring pages, APIs, and heavy resources and mapping timings to user expectations. Use when the user asks about performance, slowness, load times, TTFB, LCP, API latency, waterfalls, benchmarking, or runs this skill explicitly.
---

# Performance & Latency Testing

## When to apply

- Automatic discovery: “slow”, “performance”, “latency”, “load time”, “TTFB”, “LCP”, “why is this laggy”, “benchmark APIs”, “measure page speed”.
- Manual invocation: explicit request to run this skill.

## Mindset

Treat latency as a **user experience** problem, not a single number. Prefer **evidence** (timestamps, network rows, server logs) over guesses. Call out **variance** (cold start vs warm cache, first vs repeat navigation).

## What to measure (pick what applies)

| Category | Examples | Primary metrics |
|----------|----------|-----------------|
| Full page load | Initial URL, hard refresh | TTFB, FCP/LCP (if available), `DOMContentLoaded`, total load |
| Client navigation | Next.js route changes | Transition time until meaningful UI + data ready |
| API / fetch | REST calls from browser or server | **Waiting (TTFB)**, download, total; payload size |
| Backend-only | FastAPI endpoints, DB-heavy routes | Server-side duration if instrumented; approximate RTT + TTFB from client |
| Third parties | Google Identity, OAuth redirects, CDN | Redirect chain length, blocked time, main-thread impact |
| Assets | JS bundles, fonts, images | Transfer size, queueing, parallelization |

## Autonomous execution

1. Infer the **highest-impact user journeys** (sign-in, home/inbox load, message open, workflow run, results, settings save/import).
2. **Run measurements** using whatever fits the environment:
   - Browser: DevTools **Network** (disable cache for cold tests; repeat with cache for warm).
   - Browser: **Performance** recording for long tasks / main-thread jank tied to an action.
   - CLI: `curl -w` or similar for API TTFB when the UI is unavailable.
   - Automated: Playwright traces / HAR export if the project already uses them.
3. For each measured item, record **how** it was measured (tool, cache on/off, throttle off/on).
4. **Sort** all rows by the primary duration column (slowest first).
5. Emit the **Required output order** report (executive summary → table → `###` subsections → narrative); fold interpretation into **Top bottlenecks**, **Fastest wins**, and **Narrative** (cause classes: payload, N+1, cold start, third party, render).

If blocked (no running app, no browser), still deliver the **full structure below**: executive summary must state the blocker; table rows may use **TBD** with exact capture steps in **Follow-up measurements**.

## Required output order (every execution)

**Do not skip sections.** Use these exact `##` headings in this order so reports are comparable across runs.

1. **`## Executive summary`** — 3–6 bullets, plain language:
   - One line: **what was measured** (e.g. “API only, curl, localhost:8000”) and **overall takeaway** (acceptable / mixed / blocked).
   - **Slowest meaningful item** (name + approximate duration) and whether it is **blocking UX** or **background**.
   - **Caveats** in one line (e.g. no browser LCP, no Gmail auth, cold vs warm).
   - If nothing was measurable: **why** and **single next step** to unblock.

2. **`## Latency summary (slowest first)`** — the ranked markdown **table** (schema below). Sort by **Duration (primary)** descending. Include **failed connects**, **401/403/404** rows when those are the observed behavior (they still have latency).

   Place steps **3–6** immediately **below the table** as `###` subsections of this `##` (do not insert another `##` between the table and **Measurement context**).

3. **`### Measurement context`** — paragraph or bullets: tool(s), cache on/off, throttle, base URL(s), environment label (local/staging/prod-like), date.

4. **`### Top bottlenecks (1–3)`** — numbered list; tie to user impact.

5. **`### Fastest wins (low effort / high impact)`** — bullet list.

6. **`### Follow-up measurements`** — bullet list of concrete next probes (e.g. “Browser Network: POST /process with throttle Fast 3G”).

7. **`## Narrative`** — **5–12 sentences** in prose: what hurts users most, what is fine, what to verify next (SQL, Gmail batching, bundles, parallelism). No bullet list in this section.

## Method rules (keep results trustworthy)

- State **environment**: local/staging/prod-like, CPU throttle (if any), network preset (e.g. Fast 3G) or “unthrottled”.
- Prefer **2–5 repeats** per action; report **median** and optionally **p95** or min–max when noisy.
- Separate **cold** (hard refresh, empty cache) vs **warm** (normal revisit) when conclusions differ.
- For APIs, capture **request URL (or stable label)**, **method**, and **status**; redact secrets in pasted output.
- Note **payload size** when total time is high but TTFB is low (serialization/download cost).

## User-expectation rubric (qualitative, not a SLA)

Use this to label **Expected UX** and **Verdict** in the table. Adjust wording if the action is clearly background (prefetch) vs blocking.

| Bucket | Typical user expectation | Verdict hint |
|--------|---------------------------|--------------|
| **Instant** | Feels immediate; no conscious wait | Good |
| **Snappy** | Brief pause; still feels responsive | Good / watch |
| **Noticeable** | User notices wait; tolerable if rare | Investigate if primary path |
| **Frustrating** | User may assume failure or retry | Poor |
| **Broken-feeling** | Perceived hang, spinner fatigue, timeout risk | Critical for blocking flows |

Rough **guidance** for **blocking** UI actions on a fast connection (not a guarantee): under ~200ms toward Instant; ~200–800ms Snappy; ~0.8–2s Noticeable; over ~2s Frustrating unless clearly a heavy job with explicit progress.

## Table schema (inside `## Latency summary (slowest first)`)

Copy this table; replace cells with measured values or **TBD**:

```markdown
| Rank | User-facing action / resource | Type | Metric | Duration (primary) | Also note | User expectation | Verdict |
|------|----------------------------------|------|--------|--------------------|-----------|------------------|---------|
| 1 | … | page / API / asset / redirect | total, TTFB, LCP, etc. | e.g. 1.25s median | HTTP code, size, cache, repeats | Instant / Snappy / … | Good / Poor / … |
| 2 | … | … | … | … | … | … | … |
```

## Severity for performance issues

- **Critical**: Primary task often exceeds “Frustrating” or fails/timeouts; blocks revenue/trust paths.
- **Major**: Primary path often “Noticeable”+ without explanation/progress; large payloads or serial waterfalls.
- **Minor**: Occasional slowness, background work, or dev-only annoyance.
- **Enhancement**: Wins when other risks are clear.

## Anti-patterns

- Declaring “fast” or “slow” without naming **which metric** and **which user action**.
- One-shot numbers with no cache/throttle context.
- Ignoring **payload size** and **parallelization** when total time dominates.
- Mixing **lab** numbers with **production** claims without labeling them.
