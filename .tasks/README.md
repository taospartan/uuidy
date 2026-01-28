# uuidy Build Tasks

This directory contains task specifications for building the uuidy application incrementally.

## Task Dependency Graph

```
01-project-setup
    ├── 02-database-layer ──┬── 04-cache-service ──┐
    │                       │                      │
    └── 03-schemas ─────────┴── 05-search-service ─┼── 07-api-routes ── 08-integration ── 09-docs
                            │                      │
                            └── 06-classifier ─────┘
```

## Task Summary

| Task | Title | Complexity | Dependencies |
|------|-------|------------|--------------|
| 01 | Project Setup & Tooling | Low | None |
| 02 | Database Layer | Medium | 01 |
| 03 | Pydantic Schemas | Low | 01 |
| 04 | Cache Service | Medium | 02, 03 |
| 05 | Search Service | Medium | 01, 03 |
| 06 | Classifier Service | High | 03, 05 |
| 07 | API Routes | Medium | 04, 05, 06 |
| 08 | Integration Testing | Medium | 07 |
| 09 | Documentation | Low | 08 |

## Execution Order

For optimal context management, execute tasks in this order:

1. **01-project-setup** - Foundation, no dependencies
2. **03-schemas** - Define data shapes early (parallel with 02)
3. **02-database-layer** - Models depend on schema understanding
4. **04-cache-service** - Requires DB and schemas
5. **05-search-service** - Independent of DB, needs schemas
6. **06-classifier-service** - Core logic, needs search results
7. **07-api-routes** - Orchestrates all services
8. **08-integration-testing** - Validates full system
9. **09-documentation-polish** - Final polish

## Usage

When working on a task:

1. Read the task JSON file for full specifications
2. Implement deliverables in order listed
3. Run acceptance criteria tests
4. Commit before moving to next task

Each task is sized to be completed in a single focused session while maintaining relevant context.
