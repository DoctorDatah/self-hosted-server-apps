# Document Formatting Guide

## Summary
- **Goal:** Make docs fast to scan and easy to review.

## Front Matter
- **Title:** Document Formatting Guide
- **Project:** Repo-wide documentation
- **Owner:** Malik
- **Status:** Draft
- **Last updated:** 2026-01-25
- **Related docs:** `AI/design document writing guide.md`

## Purpose
- **Standardize structure** so readers know where to look.
- **Increase scanability** with predictable formatting patterns.

## Scanability Rules
- **Start with a 1-2 line summary** at the top.
- **Use consistent headings** and section order.
- **Prefer single-line bullets** for each idea.
- **Add spacing only when points have subpoints.**
- **Use tables** for variables, settings, or mappings.

## Heading Structure
- **H1:** Document title.
- **H2:** Major sections.
- **H3:** Subsections only when needed.

## Front Matter (recommended)
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
- **Avoid nested bullets** unless absolutely necessary.
- **For multi-field content, use tables** or single-line labeled bullets.

## Tables
- **Use tables** for variables, config options, and comparisons.
- **Keep column headers short.**
- **Put long explanations in text,** not tables.
- **Use tables for decisions** (Decision, Rationale, Alternatives, Impact).

## Emphasis
- **Bold each unique idea/point** in bullets and tables.
- **Use inline code** for paths, commands, and variables.
- **Avoid excessive capitalization.**

## Sections That Improve Readability
- **Summary** (top).
- **Decisions** (with rationale).
- **Risks and mitigations.**
- **Open questions.**

## Examples
- **Bad:** "We should probably add monitoring later."
- **Good:** "Out of scope: monitoring dashboards and alerting."

## Template (copy/paste)
```text
# Title

## Summary
- **Goal:**

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
|  |  |  |  |

## Overview
- **Goal:**
- **Target users:**
- **Business value:**

## Scope
- **In scope:**
- **Out of scope:**
- **Assumptions:**
- **Constraints:**

## Requirements
| **Type** | **Requirement** |
| --- | --- |
| **Functional** |  |
| **Functional** |  |
| **Non-functional** |  |
| **Non-functional** |  |

## Architecture
- **Components:**
- **Data flow:**
- **External dependencies:**
- **Deployment model:**

## Risks and Mitigations
- **Risk:**
- **Mitigation:**

## Open Questions
- **Question:**
```
