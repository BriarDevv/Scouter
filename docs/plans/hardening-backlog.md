# Hardening Backlog

Items intentionally deferred when aligning `pyproject.toml` / CI / pre-commit / Makefile contracts and dashboard lint. Each item is non-blocking for current CI (which is green) but leaves debt that should be closed in a dedicated pass.

## Backend — ruff tier-up

`pyproject.toml` currently runs `select = ["F", "W", "I"]` because the broader ruleset fired 316 violations across `app/` and `tests/`. Raising the ruleset one rule at a time is the safest path.

| Rule | Estimated violations | Dominant pattern | Suggested fix |
|---|---|---|---|
| `UP` (pyupgrade) | ~80 | `datetime.now(timezone.utc)` vs `datetime.UTC`, old `typing.Dict/List` imports | `ruff check --select UP --fix` auto-fixes most |
| `E` (pycodestyle errors) | ~40 | Mostly `E501` long lines, some in test data | Run `ruff format` first, then fix remaining E501 manually |
| `B` (bugbear) | ~60 | Mutable defaults, except-Exception, unused loop vars | Manual review, each is a real correctness flag |
| `SIM` (simplify) | ~50 | `if x: return True else return False` style, nested `with` | Mostly auto-fixable with `--fix` |
| `S` (bandit) | ~60 | `S101 assert` in tests, `S105/S106` hardcoded test credentials, `S311` random for non-crypto | Add `[tool.ruff.lint.per-file-ignores] "tests/*" = ["S101", "S105", "S106"]` before raising S |
| `N` (naming) | ~30 | Mostly fine, some class variables that should be lowercase | Low priority; cosmetic |

### Suggested tier-up order

1. Add `per-file-ignores` for tests to pre-absorb `S105/S106` noise.
2. Raise `UP` and `--fix`. Review the diff, commit.
3. Raise `SIM` and `--fix`. Review, commit.
4. Raise `B`. Manual fixes per bugbear rule. Commit per module.
5. Raise `E`. Mostly cosmetic, commit together.
6. Raise `S`. Review security implications, commit.
7. Raise `N`. Optional, rename-heavy.

After each step, run `make test` and `make lint` locally to confirm nothing broke.

## Backend — mypy strictness

`pyproject.toml` currently runs `ignore_missing_imports = true` + `warn_return_any` + `warn_unused_configs`. Non-strict mypy already produces **818 errors across 144 files** — enabling `strict = true` would multiply this by roughly 2-3x.

The type hardening backlog is large enough to be its own project. Suggested approach:

1. Start per-module. Pick one module (e.g., `app/llm/`) and add it to a `[[tool.mypy.overrides]]` block with stricter rules.
2. Use `mypy --strict app/llm/` locally, fix errors, commit.
3. Promote `app/llm/` to strict in pyproject under an override that keeps the rest of `app/` non-strict.
4. Repeat for `app/core/`, `app/api/`, etc.
5. When all overrides cover the tree, lift `strict = true` to the root and delete the overrides.

**Do not** try to enable strict mypy globally in one pass. Use the gradual override pattern.

## Frontend — dashboard ESLint errors (React 19 strictness)

`dashboard/` CI currently runs **only** typecheck (`tsc --noEmit`) and vitest. There is no lint step. When run locally, ESLint reports **10 errors** and **39 warnings** against the React 19 strict rules that shipped with Next 16. These errors are real and pre-existing.

### Hard errors (10, grouped by rule)

| Rule | Count | Files | Fix pattern |
|---|---|---|---|
| `react-hooks/react-compiler` or similar — `Calling setState synchronously within an effect can trigger cascading renders` | 6 | Various (`useEffect` + `setState` in the same tick) | Move state derivation to `useMemo` or track with a ref to break the cascade |
| `react/no-unstable-nested-components` — `Cannot create components during render` | 3 | Files where a component is defined inside another component's JSX | Extract the inner component to module scope |
| `@typescript-eslint/no-explicit-any` | 1 | Stray `any` outside of `tests/readiness-gate.test.tsx` (already fixed) | Replace with proper type or `unknown` |

### Suggested approach

1. Extract inner components first (mechanical, low risk).
2. Fix `setState-in-effect` case by case. Each one may require a small refactor — read the component first, understand the data flow, then fix.
3. Replace the stray `any`.
4. Add `npm run lint` to `ci.yml` frontend job **after** all 10 errors are gone. Start with `--max-warnings 0` disabled to let the 39 warnings stay as backlog, tighten later.

### Soft warnings (39)

Mostly:
- Unused imports (trivial cleanup, `ruff`-equivalent auto-fix)
- `<img>` instead of `next/image` (performance hint, not correctness)
- `react-hooks/exhaustive-deps` where a memo dependency could be refined
- `react-hooks/refs` where a ref could be misused in render

These are not blocking CI and can be cleaned up incrementally after the hard errors land.

## Tracking

When a hardening step completes, edit this document to either strike the line or remove it entirely. If a new category of violation appears, add it here rather than shipping a hack to silence it.

This backlog is the contract — it's how the repo stays honest about what `pyproject.toml` claims vs what runs in CI.
