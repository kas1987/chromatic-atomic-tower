# Decision Log

| Date | Decision | Reason | Owner |
|---|---|---|---|
| 2026-06-17 | Create CAT as new repo | Avoid Harness V2 legacy sprawl | Human Owner |
| 2026-06-17 | Use Harness V2 as donor only | Extract value without inheriting clutter | Human Owner |
| 2026-06-17 | Use Mission -> BEAD -> Evidence -> Learning hierarchy | Enables traceable autonomous work | Human Owner |
| 2026-06-17 | Use YAML/JSON for operational contracts | Enables validation and automation | Human Owner |
| 2026-06-17 | Adopt Sprint 000 package as live repo at C:\.01_CAT root | Promote validated scaffold; remove staging nesting | Human Owner |
| 2026-06-17 | Baseline accepted: repo check + 16-contract schema validation + GO resolver + 3 pytest all pass | Satisfies PDR-CAT-000 section 14 acceptance criteria | Human Owner |
| 2026-06-17 | Govern the multi-model coding harness as CAT mission MP-CAT-002 (not a separate repo/.agent dir) | Keep model choice as routing inside mission authority; honor CHROMATIC_TREES (no ungoverned top-level files) | Human Owner |
| 2026-06-17 | Verified Ollama Cloud worker tags: kimi-k2.7-code:cloud, minimax-m3:cloud | Implementation role for MP-CAT-002 workers | Human Owner |
| 2026-06-17 | Adopt budget_agent_harness_pdr_pack as MP-CAT-002 implementation; harness home is .agent/ (pack-native, harness_settings paths) | Pack is self-consistent and design-complete; avoid refactoring its layout into separate planes | Human Owner |
| 2026-06-17 | Promote MP-CAT-002 draft->approved and dispatch via implementer subagent | Human Owner directed "set up a plan and have a subagent implement" | Human Owner |
