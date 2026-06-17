# Echo Log

The Echo Log records what the system should remember next time.

## Sprint 000 seed learning

- CAT should remain a control system, not a general knowledge base.
- V2 should be mined selectively, not copied wholesale.
- `GO` must resolve to a BEAD, not an open-ended agent instruction.

## Model routing learnings (2026-06-17)

- Kimi via Ollama Cloud is tagged `kimi-k2.7-code:cloud` (NOT `kimi-k2*`; that tag does not exist).
- Drive cloud models through the HTTP API (`POST http://localhost:11434/api/generate` with
  `stream:false, think:false`) — not `ollama run` — to avoid TUI escape-code corruption and the
  thinking-token preamble in captured output.
- Always strip CR (`\r`) from API responses on Windows before parsing.
- MiniMax via Ollama Cloud is tagged `minimax-m3:cloud` (verified responding 2026-06-17).
- Other Ollama Cloud tags available: `glm-5.2:cloud`, `nemotron-3-super:cloud`, `gpt-oss:120b-cloud`.
  Tag strings are non-obvious — read them from the Ollama app's model selector, don't guess.
