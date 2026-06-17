# Evidence Gate

## Executive Summary

The Evidence Gate prevents CAT from accepting completion without proof.

```text
No Evidence Bundle = No BEAD Completion
No Required Artifact = No Closeout
Failed Required Validation = No Completion
```

## Evidence Bundle

An evidence bundle is a machine-readable YAML file that attaches proof to a Mission or BEAD.

Required fields include:

- evidence ID
- mission ID
- BEAD ID for BEAD closeout
- target type
- validation result
- required artifacts
- supporting artifacts
- summary
- learning note
- closeout readiness

## Validate a Bundle

```bash
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml
```

## Negative Test

```bash
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-MISSING.yaml
```

The missing-artifact bundle should fail.

## Operator Rule

A completion transition should never be attempted until the evidence bundle validates.
