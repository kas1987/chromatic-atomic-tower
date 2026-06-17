# Security

CAT must not store secrets, credentials, tokens, private keys, or production connection strings.

## Immediate halt conditions

Stop work and escalate if you encounter:

- API key
- private key
- password
- token
- production credential
- private customer data
- unexplained external endpoint
- destructive command

## Reporting format

```md
## Security Halt

Mission:
BEAD:
File/Location:
What was found:
Why this is sensitive:
Recommended containment:
Human decision needed:
```
