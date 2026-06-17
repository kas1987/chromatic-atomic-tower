# Tool Budget Rules

Tool budgets limit search, read, write, execute, and runtime behavior.

## Default budgets

| Mission | Search | Read | Write | Execute | Runtime |
|---|---:|---:|---:|---:|---:|
| M1 | 0 | 2 | 2 | 0 | 15 min |
| M2 | 1 | 5 | 4 | 2 | 30 min |
| M3 | 2 | 10 | 8 | 4 | 60 min |
| M4 | 3 | 15 | 4 | 2 | 90 min |

## Stop conditions

Halt if:

- same file is reread more than twice without new reason
- search is repeated without new information
- tool budget is exceeded
- agent begins exploring unrelated folders
- agent tries to discover its own mission
- agent wants to edit outside allowed paths
