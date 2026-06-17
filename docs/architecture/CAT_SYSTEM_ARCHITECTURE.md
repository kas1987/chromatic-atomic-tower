# CAT System Architecture

CAT is a filesystem-native governance kernel.

## Core components

```text
Mission Registry -> Mission Contract -> BEAD Contract -> Agent Role -> Gate -> Evidence -> Learning
```

## Why filesystem-native

Sprint 000 avoids databases and services so the system can be adopted immediately in a new repo.

Future sprints can add adapters, but the base contract remains readable and version-controlled.
