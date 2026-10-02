# ADR-001: ORM and Auth Library Choices

## Status
**Accepted** — October 2026

## Context
The initial plan called for Prisma Python client and the commonly recommended `passlib` + `python-jose` stack for authentication. During research, we discovered:

1. **Prisma Python client (`prisma-client-py`)** was officially **archived in April 2025**. Prisma's engine rewrite from Rust to TypeScript makes the Python client incompatible with newer Prisma versions.
2. **`passlib`** is unmaintained and **crashes on Python 3.13+** due to removal of the `crypt` stdlib module.
3. **`python-jose`** has an inactive repository with unpatched security vulnerabilities.

## Decision
- **ORM**: Use **SQLAlchemy 2.0** (async mode with `asyncpg`) + **Alembic** for migrations.
- **Password hashing**: Use **`pwdlib[argon2]`** — actively maintained, uses Argon2 (winner of the Password Hashing Competition).
- **JWT**: Use **`PyJWT[crypto]`** — widely used, actively maintained, supports RS256/ES256.

## Consequences
### Positive
- SQLAlchemy is the most mature, tested ORM in the Python ecosystem with full async support.
- Argon2 is the current best practice for password hashing (memory-hard, resistant to GPU attacks).
- PyJWT has a clean, well-documented API and active maintenance.

### Negative
- SQLAlchemy requires more boilerplate than Prisma (explicit model definitions, session management).
- Migration from any future ORM adoption would require significant work.
- No auto-generated TypeScript types from the schema (would need a separate code generation step).

## Alternatives Considered
- **SQLModel** (by FastAPI creator): Combines SQLAlchemy + Pydantic but less mature for complex relationships.
- **Tortoise-ORM**: Django-style async ORM, but smaller ecosystem and less battle-tested.
