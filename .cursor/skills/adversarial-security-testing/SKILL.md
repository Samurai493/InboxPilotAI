---
name: adversarial-security-testing
description: Performs adversarial security review from an attacker mindset (auth, IDOR, injection, SSRF, secrets, supply chain, LLM abuse). Delivers findings in an urgency-sorted table with criticality, fix difficulty, potential damage, and concrete fixes. Use when the user asks for security testing, pentest-style review, vulnerability assessment, threat modeling, exploit analysis, or hardening with prioritized remediation.
---

# Adversarial security testing

## Preconditions

- **Authorized scope only**: Assume testing is permitted for the target (owner’s app, staging, or explicit engagement). Do not instruct or imply testing third-party systems without authorization.
- **No real exploitation of production** unless the user clearly owns the environment and asked for it; prefer code review, config review, and safe local/staging verification.
- **Minimize harm**: Do not exfiltrate real user data, run destructive payloads, or DoS production.

## Mindset

Act as a **motivated, capable attacker** who wants data, control, free compute, or persistence. Goals to consider:

- Steal or forge sessions, tokens, API keys, or OAuth credentials
- Read or modify other users’ data (IDOR, broken access control)
- Run code or SQL/commands on the server (injection, deserialization, template bugs)
- Reach internal services (SSRF), abuse webhooks or redirects
- Poison AI/LLM behavior (prompt injection, tool abuse, data exfiltration via model)
- Abuse email/integrations (spoofing paths, unsafe HTML, attachment handling) when relevant

Use **currently known** techniques (public CVE classes, OWASP Top 10, common misconfigurations). Prefer evidence from **this codebase and deployment** (routes, auth middleware, env handling, parsers) over generic lectures.

## Workflow

1. **Map attack surface**: Entry points (HTTP routes, WebSockets, webhooks, cron, CLI, background workers), trust boundaries, data stores, third-party APIs, file uploads, email ingest, LLM/tool calls.
2. **Identify assumptions**: What must be secret? What is trusted (headers, JWT claims, internal URLs)? Where is user input merged into queries, HTML, emails, prompts, or shell?
3. **Hunt by category** (see checklist below); note **likelihood × impact** mentally, then **sort by real-world urgency** for this app.
4. **For each finding**: assign **criticality**, **fix difficulty**, and **potential damage** (see scales below); capture evidence, **concrete fix**, and **verification**.
5. **Add non-bugs**: **Best practices** and **warnings** as table rows with criticality **Info** (or **Low**) and damage/difficulty as appropriate.
6. **Assemble the master table**: one row per item, sorted by **urgency** (criticality first, then by damage, then by likelihood for ties).

## Category checklist (use what applies)

- **Authentication & sessions**: weak passwords/policy, missing MFA hooks, session fixation, insecure cookie flags, JWT alg/key confusion, refresh token rotation, logout invalidation
- **Authorization**: missing checks, IDOR/BOLA, horizontal/vertical privilege escalation, admin-only routes exposed
- **Input & parsing**: SQL/NoSQL/OS command/LDAP injection, XSS (stored/reflected/DOM), path traversal, XXE, SSRF, open redirects, prototype pollution (JS), unsafe `eval`/deserialize
- **Cryptography & secrets**: hardcoded keys, weak randomness, missing TLS, wrong cipher modes, logging tokens
- **Configuration & headers**: debug in prod, default creds, permissive CORS, missing CSP/HSTS, verbose errors
- **Dependencies & supply chain**: outdated libs with known CVEs, typosquat risk (mention if lockfile suggests risk; do not fabricate CVEs—verify or say “verify with scanner”)
- **Business logic**: abuse of quotas, race conditions, replay, payment/credit manipulation
- **API abuse**: missing rate limits, mass assignment, oversized payloads, auth bypass on “internal” paths
- **LLM / agent features** (if present): prompt injection, tool/API abuse via model, unsafe retrieval (PII in context), insecure tool schemas, lack of output filtering
- **Email / messaging** (if present): HTML injection in rendered mail, link safety, attachment scanning gaps, header injection

## Severity guidance (for ordering)

Use consistent labels and order output **Critical → High → Medium → Low → Informational**:

| Level | Typical meaning |
|-------|-----------------|
| Critical | Unauthenticated RCE, auth bypass, full data breach at scale, secret exposure with immediate abuse |
| High | Authenticated serious impact (admin takeover, large data leak), stored XSS with session impact |
| Medium | Limited impact or harder preconditions, partial data exposure, missing controls with workaround |
| Low | Narrow impact, hard to exploit, or defense-in-depth gaps |
| Informational | Best practices, hygiene, future hardening |

When unsure between two levels, **bias to the higher** for user-visible risk; note uncertainty briefly.

## Rating scales (use consistently)

**Fix difficulty** (engineering effort, not security severity):

| Value | Meaning |
|-------|---------|
| Low | Config/env toggle, few lines, single module, or dependency bump |
| Medium | Multiple routes/services, new middleware/guards, moderate tests |
| High | Auth/session model change, cross-cutting refactor, migration, or new infrastructure |

**Potential damage** (combine **runtime harm** and **codebase/product blast radius** in one judgment):

| Value | Meaning |
|-------|---------|
| Low | Niche edge case, hard to trigger, or mostly hygiene; small code touch |
| Medium | Notable data exposure, integrity risk for some users, or moderate refactor to fix |
| High | Widespread breach, full account takeover class, secrets exfiltration, RCE, or large invasive fix across the system |

**Criticality** in the table is the **security severity** (same labels as above: Critical / High / Medium / Low / Info).

## Required output format

Deliver **one consolidated report**. The **primary artifact** is a **single markdown table** that is easy to scan; follow it with short detail only where the table cells need expansion.

### Master findings table (required)

Sort rows by **urgency**: Critical → High → Medium → Low → Info. Use one row per vulnerability, warning, or best-practice gap.

**Column definitions:**

| Column | Content |
|--------|---------|
| **ID** | Stable id, e.g. C1, H2, M3, L1, I1 |
| **Finding** | Short title + one-line attacker/outcome (parenthetical OK) |
| **Criticality** | Critical / High / Medium / Low / Info |
| **Fix difficulty** | Low / Medium / High |
| **Potential damage** | Low / Medium / High (users, data, availability, **and** how painful the fix is for the codebase if unusual) |
| **How to fix** | Concrete remediation (pattern, file/area, config); keep cell to 1–3 sentences; use a bullet sublist only if necessary |
| **Verify** | One line: test, check, or tool |

**Table template (copy and fill):**

```markdown
# Adversarial security assessment — [app or scope name]

## Scope and assumptions
[Brief: reviewed vs out of scope, environment]

## Executive summary
[3–6 bullets: worst issues first]

## Findings table (by urgency)

| ID | Finding | Criticality | Fix difficulty | Potential damage | How to fix | Verify |
|----|---------|-------------|----------------|------------------|------------|--------|
| C1 | … | Critical | Low | High | … | … |
| H1 | … | High | Medium | Medium | … | … |

## Detail (optional)
Expand only rows where the table is too tight: **attack scenario**, **evidence** (with code citations), edge cases.

## Best practices and warnings
Include as rows in the table above (Criticality **Info** or **Low**). Do not omit if they materially reduce risk.

## Remediation roadmap
1. **Immediate** — …
2. **Short term** — …
3. **Ongoing** — …
```

Use **code citations** when referencing this repo (`start:end:path`). If the assessment is not repo-specific, put “typical pattern” or “confirm in deployment” in **Finding** / detail and still fill the table.

## Fix quality bar

- Prefer **specific** changes: exact control (e.g., parameterized query, server-side authz check, allowlist redirect, CSP directive, secret from env + rotation).
- Avoid vague advice alone (“validate input”); pair with **where** and **how** in this stack.
- If a fix requires product tradeoffs, state the tradeoff and a safer default.

## What not to do

- Do not provide step-by-step exploit recipes for live criminal use; keep scenarios **technical and proportional** to defensive remediation.
- Do not claim “no vulnerabilities” without scanning the relevant surface; say what was **not** reviewed.
