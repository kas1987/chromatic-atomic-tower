# A015 Reconciliation Repair Pre-Mortem

Plan: complete the missing A015 closeout evidence, move terminal contracts to
canonical locations, and align the sprint target with the closed/idle registry.

- Risk: a claimed artifact is absent. Mitigation: verify every required output
  and run the fixture-backed move test before closeout.
- Risk: the preserved completed BEAD-04 copy is inconsistent with the active
  contract. Mitigation: compare both copies and adopt only the copy containing
  the terminal transition history.
- Risk: the target passes while active and archived contracts collide.
  Mitigation: require one archived mission contract, no active A015 BEADs, and
  passing registry/reconciliation tests.

Decision: PROCEED.
