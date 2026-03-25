# Code Review Standards

Use this checklist after understanding the intended behavior.

## 1) Correctness and logic

- Feature behavior matches the stated requirement and changed flows.
- Edge cases are handled (empty input, null/undefined, limits, invalid states).
- Control flow avoids hidden fallthrough or dead branches.
- State transitions are explicit and recoverable after failures.

## 2) Error handling and observability

- Errors are caught at the right layer and surfaced with useful context.
- Messages are actionable and do not leak sensitive internals.
- Retries/timeouts are bounded when external services are involved.
- Logs are sufficient to debug failures without being noisy.

## 3) Data validation and contracts

- Inputs are validated at trust boundaries (API, queue, file, user input).
- Output shape and types match expected contracts.
- Backward compatibility is preserved for public interfaces unless intentional.
- Migrations and schema changes include safe rollout/rollback thinking.

## 4) Maintainability and readability

- Naming reflects domain intent, not implementation accidents.
- Functions/classes have clear responsibilities and reasonable size.
- Duplication is reduced where it improves clarity.
- Complex sections are broken down or documented with short intent comments.

## 5) Testing adequacy

- New behavior has tests at the right level (unit/integration/e2e as needed).
- Regressions are covered for fixed bugs.
- Failure paths and validation errors are tested, not only happy paths.
- Test names describe behavior and expected outcomes.

## 6) Security sanity checks

- Authorization and access-control checks are present where required.
- User input is sanitized/escaped for target context.
- Secrets/tokens are never hardcoded or logged.
- Sensitive operations have least-privilege assumptions.

## 7) Performance and reliability hotspots

- No obvious N+1 queries or repeated expensive work in hot paths.
- Resource handling is safe (connections, streams, file handles, memory).
- Concurrency assumptions are explicit where shared state exists.
- Time complexity is reasonable for expected data sizes.

## 8) Documentation and developer impact

- README/docs/config examples are updated for behavior changes.
- New flags/env vars/defaults are documented.
- Breaking changes and migration notes are clearly called out.

## Severity mapping

- Critical: likely bug, regression, security flaw, or contract break.
- Major: maintainability risk, missing validation/error handling, or substantial test gap.
- Minor: clarity/style improvements with low risk.
