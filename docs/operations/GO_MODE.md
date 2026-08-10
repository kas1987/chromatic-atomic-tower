# GO Mode

## Operator command

When the operator says:

```text
GO
```

CAT should:

1. read `missions/registry/MISSION_REGISTRY.yaml`
2. select the highest-priority approved mission
3. read `beads/active/`
4. select the current active BEAD for that mission
5. check confidence
6. output dispatch packet
7. execute only that BEAD
8. validate
9. record evidence
10. queue next action

## Local command

```bash
python scripts/cat_resolve_go.py
```

## JSON output

```bash
python scripts/cat_resolve_go.py --json
```

## Short versioned approval

`ANA v1` means **Approved Next Recommended Action**. It approves the exact
`Next Recommended Action` named in the immediately preceding CAT result.

Example:

```text
ANA v1: register the dedicated route/event contract BEAD
```

`ANA` is narrow and action-specific. It does not by itself:

- execute the action;
- mean `GO`;
- approve unrelated work;
- create authority outside a Mission/BEAD contract;
- bypass confidence, evidence, HITL, or remote-mutation gates.

The resolver must still produce the dispatch packet, and execution remains
limited to the approved Mission and BEAD scope.
