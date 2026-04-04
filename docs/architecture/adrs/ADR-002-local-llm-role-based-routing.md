# ADR-002: Local LLM-First Architecture with Role-Based Model Routing

**Status:** Accepted
**Date:** 2026-04-04

## Context

Scouter's Agent OS processes lead data, scores prospects, drafts outreach, and reviews outputs. Running every step through a cloud API (OpenAI, Anthropic) would expose contact data to third-party servers, incur per-token costs that scale directly with lead volume, and create a latency dependency on external endpoints.

The operator runs a machine with a local GPU capable of serving quantized models via Ollama. Not all deployments have equivalent hardware, so the system must degrade gracefully on constrained machines.

## Decision

Scouter uses Ollama as its LLM backend. Four named AI roles exist, each assigned a model sized to its workload:

| Role | Responsibility | Default Model |
|------|---------------|---------------|
| Mote | Fast triage, classification, routing | Small (e.g. phi3-mini) |
| Scout | Research, enrichment, summarisation | Medium (e.g. mistral-7b) |
| Executor | Task execution, form-filling, outreach draft | Medium-large (e.g. llama3-8b) |
| Reviewer | Quality gate, scoring, final approval | Large (e.g. llama3-70b or best available) |

A `LOW_RESOURCE_MODE` flag (documented in `docs/agents/governance.md`) collapses all roles to a single small model when GPU memory is insufficient.

## Consequences

**Positive**
- No contact data leaves the operator's machine.
- No per-token API costs; marginal cost per lead is electricity.
- Lower latency for fast roles (Mote) running on-device inference.
- System is usable offline.

**Negative**
- Output quality is bounded by locally available model weights; a hosted GPT-4-class model would outperform quantized local equivalents.
- Requires a GPU with sufficient VRAM for the Reviewer role; CPU inference is too slow for production use.
- Model updates are manual (pull new weights, test, update role assignment).
- `LOW_RESOURCE_MODE` degrades quality noticeably; it is a fallback, not a target.

## Alternatives Considered

**Cloud APIs with data anonymisation.** Rejected because anonymisation of enriched lead data is difficult to guarantee and adds preprocessing complexity without eliminating the compliance concern.

**Single model for all roles.** Rejected because it either over-provisions resources for cheap tasks (Mote) or under-provisions quality for critical tasks (Reviewer). Role-based routing lets each step use the smallest model sufficient for its job.
