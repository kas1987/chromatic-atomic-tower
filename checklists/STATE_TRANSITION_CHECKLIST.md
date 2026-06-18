# State Transition Checklist

Before applying a transition:

- [ ] Target contract exists.
- [ ] Current status is correct.
- [ ] Target status is listed in `STATE_TRANSITION_RULES.yaml`.
- [ ] Dry-run result is allowed.
- [ ] Evidence exists when required.
- [ ] Reason is specific.
- [ ] No forbidden paths are touched.
- [ ] Registry and tower state are expected to change.
- [ ] Tests pass after transition-related work.
