# CAT Closeout Report

Target: bead BEAD-CAT-002-CLOSEOUT-EXAMPLE

Transition: completed

Allowed: False

Dry Run: True

Reason: test missing artifact

Message: closeout blocked by evidence gate

Evidence Bundle: evidence\bundles\examples\EB-CAT-002-MISSING.yaml

Validation Result: passed

## Summary

This bundle intentionally references a missing required artifact for negative testing.

## Artifacts

- evidence/reports/this_file_should_not_exist.md (report, required=True, result=passed)

## Errors

- missing required artifact: evidence/reports/this_file_should_not_exist.md

## Learning

Missing required artifacts must block closeout.

Created: 2026-06-18T01:26:45+00:00
