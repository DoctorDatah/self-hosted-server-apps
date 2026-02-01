# Framework Usage Guide (Human-Oriented)

## Summary
- **Goal:** Explain the AI, Design, and Implementation folders, plus repo scope rules, so humans can build any project with AI.

## Purpose
- **Explain the AI folder** and the rules it enforces.
- **Explain the repo scope file** and how it limits work for each session.
- **Show how to reuse the framework** for any project.
- **Clarify how design and implementation** are done with AI support.

## Scope
- **In scope:** Planning, design, and implementation docs for new app features built with AI support.
- **Out of scope:** Runtime deployment, production operations, and post-release support runbooks.
- **Assumptions:** The repo is the source of truth; changes are reviewed in PRs.
- **Constraints:** Use the specified doc formats; do not invent new sections without a need.

## Requirements
- **Read the repo scope file first** and treat it as the session source of truth.
- **Use the AI guides as rules, not suggestions.**
- **Keep all docs in repo format** with required sections and front matter.
- **Treat design as the source of truth** for implementation steps.
- **Update implementation status** to `done` only after real work is complete.

## AI Folder (what it is)
- **Purpose:** Defines how AI should read, write, and edit docs in this repo.
- **Why it matters:** It prevents ambiguity and keeps AI output reviewable.
- **What to read first:** `AI/1. reading guide for ai and syntax for developer.md`.
- **How to format any doc:** `AI/2b. general document formatting guide.md`.

## Repo Scope File (what it is)
- **Purpose:** Defines the current working scope for the repo at any given time.
- **Why it matters:** It limits what can be changed so work stays focused and safe.
- **Where it is:** `Repo's Current Scope For AI.md`.
- **How to use it:** Treat it as the source of truth for what is in scope, out of scope, and allowed changes.

## Use This Framework for Any Project
- **Start with the repo scope file** to confirm what is in scope.
- **Then read the AI folder** to learn the rules for writing and editing.
- **Write a design doc first** so decisions are explicit and testable.
- **Translate design into implementation steps** so execution is deterministic.
- **Reuse the same structure** across projects to keep reviews fast.

## Design Folder (how to design with AI)
- **Purpose:** Capture decisions, scope, and requirements before any coding.
- **Where to start:** `AI/2a. design document writing guide.md`.
- **How to work with AI:** Provide variables and decisions; ask AI to draft the design doc.
- **What to review:** Scope, requirements, architecture, risks, and open questions.

## Implementation Folder (how to implement with AI)
- **Purpose:** Convert the design into a step-by-step checklist.
- **Where to start:** `AI/4. implementation document writing guide.md`.
- **How to work with AI:** Ask AI to create the checklist table from the approved design.
- **What to update:** Mark steps `done` only when code changes are complete.

## Workflow Map

| **Stage** | **Input** | **Output** | **Primary doc** |
| --- | --- | --- | --- |
| 0. Scope | Current repo context | Approved scope boundaries | `Repo's Current Scope For AI.md` |
| 1. Read | Existing repo docs | Clear constraints and exclusions | `AI/1. reading guide for ai and syntax for developer.md` |
| 2. Design | Product intent, constraints | Design doc with decisions | `AI/2a. design document writing guide.md` |
| 3. Format | Draft doc content | Consistent, scannable doc | `AI/2b. general document formatting guide.md` |
| 4. Implement | Approved design doc | Step table with status tracking | `AI/4. implementation document writing guide.md` |

## Step-by-Step Usage
1) Read `Repo's Current Scope For AI.md` and confirm scope boundaries.
2) Read the AI guides and confirm exclusions or locked text.
3) Draft a design document using the required sections and decision table.
4) Apply the formatting guide before asking for review.
5) Convert the approved design into an implementation checklist table.
6) Execute steps in order and update `Implementation status` to `done`.
7) Keep the implementation table in sync with actual code changes.

## Risks and Mitigations
- **Risk:** Design doc and implementation steps drift out of sync.
- **Mitigation:** Update the implementation table with every code change.
- **Risk:** Work drifts outside the current repo scope.
- **Mitigation:** Re-check `Repo's Current Scope For AI.md` before making changes.
- **Risk:** AI edits introduce new requirements.
- **Mitigation:** Enforce the reading protocol and treat exclusions as hard constraints.

## Open Questions
- **OPEN:** Where should finalized app docs live beyond `Implementation/`?
