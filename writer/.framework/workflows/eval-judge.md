---
name: eval-judge
description: Judge workflow that tests the completeness and effectiveness of the agentic framework. Completeness audits structural integrity (does every contract resolve, is the agent↔skill↔workflow graph closed and consistent); effectiveness audits behavioral correctness (does routing delegate, is the boundary honored, does the offline/online mode, agent-first invocation, versioning, and archive-before-overwrite actually hold). Read-only: it never mutates framework or workspace files.
---

# The Eval-Judge Workflow

This workflow is the framework's **self-judge**. It answers two questions the
other workflows do not:

1. **Completeness** — is the framework *complete*? Does every stated contract
   resolve to a real file, does every command route to a real agent, does every
   agent have its required skill, and do the data layers agree?
2. **Effectiveness** — is the framework *effective*? When the routing, boundary,
   execution-mode, and lifecycle rules are actually followed, do they produce a
   consistent, correct result — or do they contradict one another or leak across
   layers?

It is **read-only** and **routing-only**: it inspects and scores, then delegates
the heavy structural audit to the self-eval rule (`.framework/rules/self-eval.md`)
and the per-book readiness check to the eval agent
(`.framework/agents/eval/agent.md`). It adds a behavioral **effectiveness** pass
that neither of those covers.

## Command Surface

This workflow has a single read-only entry point:

```text
/book eval-judge [--completeness] [--effectiveness] [--book <bookname>] [--all]
```

| Flag | What it tests |
|------|---------------|
| `--completeness` | Structural integrity (dimensions 1–5 below). Default when no flag is given. |
| `--effectiveness` | Behavioral correctness (dimensions 6–8 below). |
| `--book <bookname>` | Scope the effectiveness pass to one pipeline (`workspaces/pipeline/<bookname>/`). |
| `--all` | Run both passes, over every pipeline. |

With no flags, run the **completeness** pass (equivalent to `--completeness`).

## Routing

- **Completeness pass** → delegate to `.framework/rules/self-eval.md`, which owns
  the six-dimension structural scorecard (reference integrity, workflow coverage,
  agent↔skill completeness, template/schema validity, data-layer consistency,
  boundary/rule soundness). Re-run it as-is; this workflow does not duplicate its
  method.
- **Effectiveness pass** → owned here (dimensions 6–8 below), scoped per pipeline
  via the eval agent's readiness verdict where applicable.
- **Per-book readiness** → delegate to `.framework/agents/eval/agent.md` for
  write-ready/validated/publish-ready, which the effectiveness pass consumes as
  evidence but does not itself recompute.

## Completeness (delegated to `.framework/rules/self-eval.md`)

Invoke the self-eval rule and reproduce its **Framework Health Score** (0–100) and
**Defects** list. Do not re-derive it. Summarize:

1. The scorecard (six dimensions, score/10, weight, weighted points).
2. The total score and verdict (Healthy / Good / Fragile / Broken / Inoperable).
3. The numbered defects (each with severity and a concrete fix).

## Effectiveness (owned here)

Completeness proves the framework *could* run; effectiveness proves it *does*.
For each pipeline in scope (or the single `--book`), verify these behavioral
contracts against on-disk state and the workflow/agent/rules text. Each check is
binary (**hold** / **violation**) and every violation names the file and the exact
clause that broke.

### 6. Routing delegation

- Every `/book` command in `.framework/workflows/book.md` maps to exactly one
  owning workflow (backlog vs pipeline) with no overlap and no orphan.
- Every pipeline command in `.framework/workflows/pipeline.md` routes to an agent
  whose `agent.md` exists (see its `Command → Agent Routing` table).
- **Agent-first:** no workflow or rule executes a skill directly; every skill is
  reached `workflow → agent → skill`. A direct `workflow → skill` reference is a
  violation.
- **Identity matches folder:** every `.framework/agents/<x>/agent.md` has
  frontmatter `name: <x>` and every `.framework/skills/<x>/SKILL.md` (and
  `.framework/filters/<x>/SKILL.md`) has `name: <x>` — the `name:` field must
  equal its parent folder name. A mismatch is a violation.

### 7. Boundary and execution-mode

- No backlog command's spec touches `workspaces/pipeline/<bookname>/` or
  `workspaces/published/`; no pipeline command writes `workspaces/backlog/<bookname>/`.
- The `factory` resolution (`.framework/rules/command-boundary.md`) is unambiguous:
  one search order, one per-agent default table, no two clauses that resolve a
  given command to different modes.
- **Offline display-and-confirm** is stated consistently: every offline-capable
  command resolves from `.framework/offline_registry.md`, and the registry entry
  actually exists and matches the command shape. A command that says "offline"
  but has no registry entry is a violation.

### 8. Lifecycle and versioning

- The poetry lifecycle contract (`.framework/rules/poetry-lifecycle.md`) does not
  contradict the pipeline workflow's phase gates or the chapter-layout rule.
- `draft-versioning.md` and `source-versioning.md` are referenced by every agent
  that replaces `chapter.md` (write, style, poet) and are consistent with one
  another (pipeline draft versions ≠ reader-facing versions).
- For the scoped pipeline: `progress.json` states (`written`, `validated`,
  `published`) are mutually consistent with the eval agent's verdict — a chapter
  marked `published: true` without a passed, hash-current `quality_review` is a
  violation.
- Audit metadata (`.framework/rules/audit-metadata.md`) is present on every
  non-exempt `.md`/`.json` file under the scoped pipeline. A missing or stale
  `updated_by`/`updated_date` on a file outside `chapters/**` and outside
  `_history/`/`history/`/`version/` snapshots is a violation; audit fields on
  exempt snapshots are not required and their absence is not a violation.

## Scoring

Every run produces a single **score out of 100**. How it is computed depends on
which passes ran.

### Completeness score (0–100)

The self-eval Framework Health Score, used directly. It is the weighted sum of six
dimension scores, each 0–10:

```
weights: reference 25%, workflow 15%, agent↔skill 20%, templates 15%, data 15%, boundary 10%
Completeness = Σ (dimension score × weight)
```

### Effectiveness score (0–100)

Each check is binary (**hold** = 1, **violation** = 0). Group checks by dimension
and average within the dimension, then weight the dimensions:

```
dimension 6 (routing delegation)      weight 40%
dimension 7 (boundary & exec mode)    weight 40%
dimension 8 (lifecycle & versioning)  weight 20%

Effectiveness = 100 × Σ (dimension_average × weight)
```

A dimension with zero checks in scope is excluded and its weight redistributed
proportionally over the remaining dimensions (so the result stays 0–100).

### Single score (0–100)

| Passes run | Score |
|---|---|
| `--completeness` only | Completeness score |
| `--effectiveness` only | Effectiveness score |
| `--all` | `round(0.5 × Completeness + 0.5 × Effectiveness)` |

The verdict is read from the single score:

| Score | Verdict |
|---|---|
| 90–100 | **Healthy** — complete and effective; safe to run end-to-end |
| 75–89 | **Good** — minor drift or a few low-severity violations |
| 50–74 | **Fragile** — structural or behavioral defects will break some commands |
| 25–49 | **Broken** — multiple load-bearing contracts fail |
| 0–24 | **Inoperable** — the framework cannot be trusted to run |

## Output

Produce a report with these sections:

1. **Completeness** — the self-eval scorecard, total, verdict, and defects (or
   "skipped" if only `--effectiveness`).
2. **Effectiveness** — a table of checks (dimension, check, hold/violation,
   evidence file), the weighted score, verdict, and a numbered violation list (or
   "skipped" if only `--completeness`).
3. **Score & verdict** — the single score out of 100 and its verdict, the
   completeness/effectiveness breakdown that produced it, and one line stating the
   combined verdict: the framework is *complete-and-effective* /
   *complete-but-ineffective* / *incomplete-but-effective* /
   *incomplete-and-ineffective*.
4. **Recommended next action** — the single highest-value fix (or "none").

## Rules

- **Read-only.** Never create, edit, move, or delete any file while judging.
- **Traceable.** Every violation names a real file and the exact clause; no
  "may be stale" — verify against the current filesystem.
- **Two passes are distinct.** Do not report a structural gap (completeness) as a
  behavioral failure (effectiveness) or vice versa; score each in its own pass.
- **Always report a 0–100 score.** Even a partial or skipped pass yields a number;
  never report "no score".
- **Report the framework, not your process.** A clean scorecard + violations, not
  a narrative of the search.

## Next Steps

After the report, per `.framework/rules/next-steps.md`, the recommended action is
the single highest-value fix named in section 4; if the framework is healthy, the
recommended action is "none".
