---
name: code-review
description: Reviews code changes for correctness, maintainability, readability, testing adequacy, and practical security concerns. Use when the user asks to review code, run PR review, check changes, audit a patch, or assess code quality.
---

# Code Review

## When to apply

Apply this skill for both:
- Automatic discovery: requests like "review code", "PR review", "check changes", "audit this patch", "code quality review".
- Manual invocation: explicit requests to run the `code-review` skill.

## Review order

1. Correctness and behavior
2. Maintainability and readability
3. Testing adequacy
4. Style and consistency

## Review process

1. Understand scope and changed behavior before judging implementation details.
2. Report findings first, sorted by severity:
   - Critical: bug, regression, security issue, or broken contract.
   - Major: maintainability risk, missing validation, weak error handling, or meaningful test gap.
   - Minor: readability, naming, or style improvements.
3. For each finding, include:
   - What is wrong and where.
   - Why it matters (impact/risk).
   - A concrete fix direction.
4. Keep summaries short; prioritize actionable findings.

## If no findings

State that no significant issues were found, then list:
- Residual risks (if any)
- Testing gaps or unverified paths

## Output format

Use this structure:

```markdown
Findings
- [Severity] path-or-symbol: issue, impact, and fix direction.

Open questions / assumptions
- ...

Brief change summary
- ...
```

## Detailed criteria

Use [STANDARDS.md](STANDARDS.md) for the full checklist.
