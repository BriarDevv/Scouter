# ADR-001: Use PostgreSQL for All Tests via Testcontainers

**Status:** Accepted
**Date:** 2026-04-04

## Context

Scouter's test suite originally ran against SQLite using pytest fixtures that spun up an in-memory database. SQLAlchemy's SQLite dialect silently accepted values that PostgreSQL would reject — most notably, invalid enum values were stored without error. This meant test coverage was giving false confidence: a field accepting `"INVALID_STATUS"` would pass in CI but blow up in production against a real Postgres instance.

The project uses PostgreSQL 16 in production (via Docker Compose). Running tests against a different engine created a permanent class/dialect gap.

## Decision

All tests run against a real PostgreSQL 16 instance provisioned by testcontainers-python. A dedicated guardrail test (`test_postgres_enum_strictness`) asserts that the test database rejects invalid enum literals, ensuring the guarantee holds across future refactors.

The `conftest.py` session-scoped fixture starts a `PostgresContainer`, runs Alembic migrations, and yields an async engine shared across the test session.

## Consequences

**Positive**
- Enum constraints, check constraints, and other Postgres-specific behaviors are exercised in every test run.
- Dialect drift between dev and CI is eliminated.
- The guardrail test fails loudly if someone accidentally reverts the engine.

**Negative**
- Test startup is slower: container spin-up adds roughly 5–15 seconds per session.
- Docker must be available in the test environment (local and CI).
- Parallel test runs require isolated containers or schemas to avoid state bleed.

## Alternatives Considered

**Keep SQLite for unit tests, Postgres only for integration tests.** Rejected because the boundary between "unit" and "integration" is fuzzy in an async SQLAlchemy codebase and maintaining two fixture stacks doubles the setup burden.

**Use a shared dev Postgres instance (no testcontainers).** Rejected because it requires pre-existing infrastructure and makes the test suite non-portable across developer machines and CI runners.
