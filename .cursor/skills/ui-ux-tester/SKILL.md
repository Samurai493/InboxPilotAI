---
name: ui-ux-tester
description: Critically test application interfaces for usability, clarity, accessibility, and interaction quality. Use when the user asks for UI testing, UX review, interface critique, or wants actionable improvements to screens, flows, or components.
---

# UI/UX Tester

## Purpose

Evaluate the interface like a critical product-minded tester:

1. Decide what to test based on risk and user impact.
2. Explain why each test matters.
3. Identify concrete UX/UI problems.
4. Propose prioritized improvements with rationale.

## Autonomous Execution Mode

When this skill is triggered, run as an action-oriented tester (not just a commentator):

1. Pick high-impact journeys to test.
2. Execute the journeys directly in the app when tools are available.
3. Capture concrete evidence (what was clicked, what happened, where friction occurred).
4. Prioritize improvements by user impact and implementation effort.
5. Recommend validation steps to confirm fixes.

Do not wait for extra prompts when the target flow is clear. Proceed with best judgment.

## Testing Mindset

- Test tasks, not just visuals.
- Prefer user outcomes over implementation details.
- Look for friction, confusion, and failure states.
- Assume first-time users and distracted users both exist.
- Be proactive: if one path passes, move to the next risky path.

## Critical Test Planning

Before testing, define a focused plan:

1. **Goal**: What user job should this screen/flow enable?
2. **Risk hotspots**: What can break trust or block completion?
3. **Core journeys**: Which 1-3 paths are highest value?
4. **Edge/error cases**: What happens when data is missing, invalid, slow, or denied?

Use this template:

```markdown
Test Focus:
- Journey:
- Why it matters:
- Success criteria:
- Failure signals:
```

## Autonomous Test Workflow

Follow this loop:

1. **Scope quickly**
   - Identify the page/flow and primary user intent.
   - Choose 1-3 critical journeys first.
2. **Execute**
   - Navigate and perform interactions end-to-end.
   - Include error/empty/loading and interruption scenarios.
3. **Diagnose**
   - Convert observations into root-cause UX issues.
   - Separate symptoms from underlying design problems.
4. **Improve**
   - Propose concrete, minimal, high-impact changes.
5. **Verify**
   - Define clear pass/fail criteria for each change.

If blocked (auth, missing data, broken route), report blocker + fastest unblocking option, then continue with reachable tests.

## What To Evaluate

### 1) Clarity
- Is the page purpose obvious in 3 seconds?
- Are labels, helper text, and CTAs unambiguous?
- Is information hierarchy clear?

### 2) Flow and Interaction
- Are next steps obvious?
- Is the number of steps reasonable?
- Are actions reversible where needed?
- Are loading and async states understandable?

### 3) Feedback and Errors
- Do users get clear confirmation after actions?
- Are errors specific, actionable, and placed near the source?
- Are empty states helpful?

### 4) Visual and Layout Quality
- Is spacing consistent and readable?
- Is contrast and typography comfortable?
- Are components visually consistent?

### 5) Accessibility Basics
- Keyboard navigation and focus visibility
- Semantic labels for interactive elements
- Color contrast and non-color cues
- Screen-reader-friendly names for controls

## Severity Framework

- **Critical**: Blocks task completion, causes data loss, or severe trust issue.
- **Major**: Significant friction or confusion on primary journeys.
- **Minor**: Cosmetic/low-friction issue with limited impact.
- **Enhancement**: Opportunity to improve delight, speed, or confidence.

## Output Format

Return findings in this structure:

```markdown
## UI/UX Findings

### Critical
- [Issue title]
  - Why this matters:
  - Evidence:
  - Improvement:

### Major
- ...

### Minor
- ...

## Suggested Improvements (Prioritized)
1. [Highest impact change] - Why first
2. [Next change] - Why second
3. [Follow-up optimization]

## Validation Plan
- How to verify each top improvement worked
- What metric or behavior should improve
```

## Evidence Requirements

For each finding include:

- The exact user action attempted
- Observed behavior
- Expected behavior
- Why the gap matters for user success

## Rules for Recommendations

- Recommendations must be specific and implementable.
- Tie every recommendation to a user pain point.
- Avoid vague advice like "make it cleaner."
- Prefer smallest change that solves the highest-impact problem.
- Prefer changes that improve completion rate, confidence, or error recovery.

## Decision Heuristics

When choosing what to test next, prioritize:

1. Flows that create/submit/save user data
2. Flows tied to onboarding, settings, auth, or payments
3. High-frequency actions in home/dashboard views
4. Error handling paths users are likely to hit

When choosing improvements, rank by:

- User impact (high to low)
- Confidence in diagnosis
- Implementation effort (low effort first when impact is similar)

## Example Triggers

Use this skill when the user says things like:

- "Test the UI/UX of this app"
- "Review this interface and suggest improvements"
- "Why is this flow confusing?"
- "Audit this screen for usability and accessibility"
- "Act like a UX tester"
- "Run through this flow and tell me what to fix"
- "Test this UI autonomously"

