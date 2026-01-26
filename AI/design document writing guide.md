# Design Document Writing Guide

## Summary
- **Goal:** AI-focused guide for writing deterministic, reviewable design documents.

## Front Matter
- **Title:** Design Document Writing Guide
- **Project:** Repo-wide documentation
- **Owner:** Malik
- **Status:** Draft
- **Last updated:** 2026-01-25
- **Related docs:** `AI/document formatting guide.md`

## Purpose
- **Guide AI** in writing design documents that are consistent, actionable, and safe to implement.
- **Provide guardrails** for clarity, determinism, and reviewer-friendly structure.

## AI Approach (how to write the doc)
- **Start with Global Variables** so users make top-level selections once.
- **Treat the rest as read-only** derived output from those selections.
- **Derive every section** from Global Variables; if not possible, stop and ask.
- **Make decisions explicit** and remove ambiguity.
- **Separate facts, decisions, and open questions.**
- **Prefer deterministic language** ("must/only" over "should/may").
- **Ask for missing variables** before drafting.
- **Run a validation pass** before finalizing.

## Document Standards
- **Use clear headings** and consistent structure.
- **Prefer short, declarative bullets** over long paragraphs.
- **Define terms once** and reuse consistently.
- **Separate decisions from options** and open questions.
- **Include versioning** (status, owner, last updated).
- **Keep scope explicit** and avoid silent assumptions.

## Global Variables (for user selection)
- **Put this section at the top** of every design doc.
- **Use one source of truth** for each variable.
- **Drive downstream sections** from these variables.
- **Split env-specific values** into OS or env variants.
- **Example (infra):**

| **Variable** | **Value** |
| --- | --- |
| `PRIMARY_OS` | Ubuntu 22.04 LTS |
| `SUPPORTED_OS` | Ubuntu 22.04 LTS or Debian 12 |
| `DOCKER_APT_REPO_UBUNTU` | https://download.docker.com/linux/ubuntu |
| `DOCKER_APT_REPO_DEBIAN` | https://download.docker.com/linux/debian |
| `DOCKER_APT_REPO` | pick from OS-specific values based on `PRIMARY_OS` (manual) |

- **Example (non-infra):**

| **Variable** | **Value** |
| --- | --- |
| `REGION` | us-east-1 |
| `SLA_TARGET` | 99.9% |
| `AUTH_MODEL` | SSO + API keys |

## Guardrails (make it foolproof)
- **Eliminate conflicting sources** or document the exception.
- **Avoid ambiguous phrasing** like "choose later."
- **Require a primary option** when multiple options are supported.
- **Call out prohibited actions** or dependencies explicitly.
- **State selection method** when a variable depends on another.
- **Avoid nested bullets**; use tables or single-line labeled bullets.

## Realism Checks
- **Ensure every step is actionable** with available tools.
- **Match package sources** to the supported OS.
- **Avoid hidden dependencies** by listing required tools.
- **Validate upgrade and rollback** steps are feasible for a single VM.

## Validation Checklist (run before final output)
- **Global Variables are present** at the top and referenced consistently.
- **Template includes Global Variables.**
- **No section contradicts** Global Variables.
- **All dependencies and sources** are explicit.
- **Open Questions** only includes unresolved items.
- **Rollback and upgrade paths** are feasible and stated.

## Required Front Matter
- **Title**
- **Project**
- **Owner**
- **Status** (Draft, In Review, Approved)
- **Last updated** (YYYY-MM-DD)
- **Related docs** (links or paths)

## Required Sections
1) **Overview:** one-sentence goal; target users; business value.
2) **Scope:** in scope; out of scope; assumptions; constraints.
3) **Requirements:** functional requirements; non-functional requirements.
4) **Architecture:** components; data flow; external dependencies; deployment model.
5) **Data Design:** entities and fields; relationships; storage/retention.
6) **Security:** threats; mitigations; secrets management.
7) **Observability:** logging; metrics; alerts.
8) **Testing Strategy:** unit; integration; E2E.
9) **Rollout Plan:** milestones; rollback plan.
10) **Open Questions and Risks:** questions; risks and mitigations.

## Optional Sections (use when relevant)
- **API Design**
- **UX/Workflow**
- **Performance and scaling**
- **Cost model**
- **Compliance**

## Decision Recording
- **Each decision should include** Decision, Rationale, Alternatives, Impact.
- **Use a decision table** (no nested bullets).

## Diagrams
- **Provide at least one diagram description** in words.
- **Keep diagrams focused** on data flow or system boundaries.

## Style Guide
- **Titles:** sentence case, concise.
- **Bullets:** one idea per line.
- **Numbers:** use numerals for lists and requirements.
- **Avoid jargon** unless defined in Definitions.
- **Use repo-relative paths** for references.

## Examples (bad vs good)
```text
Scope
- Bad: "We will probably add monitoring later."
- Good: "Out of scope: monitoring dashboards and alerting."

Requirements
- Bad: "The system should be secure."
- Good: "Secrets are stored in GitHub Secrets and injected at deploy time."

Decisions
- Bad: "Use Docker."
- Good: "Decision: Use Docker Compose for deployment; Rationale: single-VM simplicity; Alternatives: systemd services."
```

## Template (copy/paste)
```text
Title:
Project:
Owner:
Status:
Last updated:
Related docs:

Global Variables (select here)
- **If not provided, ask the user to select values before continuing.**

Decisions
| **Decision** | **Rationale** | **Alternatives** | **Impact** |
| --- | --- | --- | --- |
|  |  |  |  |

Definitions (optional)
- **Term:**
- **Definition:**

Overview
- **Goal:**
- **Target users:**
- **Business value:**

Scope
- **In scope:**
- **Out of scope:**
- **Assumptions:**
- **Constraints:**

Requirements
| **Type** | **Requirement** |
| --- | --- |
| **Functional** |  |
| **Functional** |  |
| **Non-functional** |  |
| **Non-functional** |  |

Architecture
- **Components:**
- **Data flow:**
- **External dependencies:**
- **Deployment model:**

Data Design
- **Entities:**
- **Relationships:**
- **Storage/retention:**

Security
- **Threats:**
- **Mitigations:**
- **Secrets:**

Observability
- **Logging:**
- **Metrics:**
- **Alerts:**

Testing Strategy
- **Unit:**
- **Integration:**
- **E2E:**

Rollout Plan
- **Milestones:**
- **Rollback:**

Open Questions and Risks
- **Questions:**
- **Risks and mitigations:**
```
