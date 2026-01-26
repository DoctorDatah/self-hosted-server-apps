# Design Document Formatting Guide

## Summary
- **Goal:** Standardize formatting for design documents only.

## Front Matter
- **Title:** Design Document Formatting Guide
- **Project:** Repo-wide documentation
- **Owner:** Malik
- **Status:** Draft
- **Last updated:** 2026-01-25
- **Related docs:** `AI/design document writing guide.md`, `AI/reading guide for ai.md`

## Purpose
- **Make design docs easy to scan** with consistent structure.
- **Keep reviews fast** by using predictable formatting patterns.
- **Reduce rework** by clarifying where decisions live.

## Scope
- **Applies to:** design documents only.
- **Does not apply to:** runbooks, SOPs, or general docs.

## Scanability Rules
- **Start with a 1-2 line summary** at the top.
- **Use consistent headings** and section order.
- **Prefer single-line bullets** for each idea.
- **Use tables** for variables, decisions, and mappings.

## Heading Structure
- **H1:** Document title.
- **H2:** Major sections.
- **H3:** Subsections only when needed.

## Front Matter (required)
- **Title**
- **Project**
- **Owner**
- **Status**
- **Last updated**
- **Related docs**

## Writing Style
- **One idea per line.**
- **Use concrete nouns and verbs.**
- **Avoid filler phrases and vague qualifiers.**
- **Use active voice.**

## Bullets and Lists
- **Max 4-6 bullets** per section.
- **Keep bullets parallel** in grammar and tense.
- **Use numbered lists** for steps or requirements.
- **Avoid nested bullets**; use tables or labeled bullets instead.

## Tables
- **Use tables** for decisions, variables, and comparisons.
- **Keep headers short** and descriptive.
- **Keep long explanations** in text, not tables.

## Required Sections (format only)
1) **Overview**
2) **Scope**
3) **Requirements**
4) **Architecture**
5) **Risks and Mitigations**
6) **Open Questions**

## Decisions (required format)
| **Decision** | **Rationale** | **Alternatives** | **Impact** |
| --- | --- | --- | --- |
|  |  |  |  |

## Examples
```text
# Title

## Summary
- **Goal:** Describe the system change and why.

## Front Matter
- **Title:**
- **Project:**
- **Owner:**
- **Status:**
- **Last updated:**
- **Related docs:**

## Decisions
| **Decision** | **Rationale** | **Alternatives** | **Impact** |
| --- | --- | --- | --- |
| Use Redis for cache | Low latency | Memcached | Operational cost |
```
