# A020-01 Pre-mortem

Plan: define and test the CAT canonical authority matrix without implementing
cross-repository mutation.

## RISK-1: Duplicate canonical writers

Trigger: The matrix lists a CAT fact with multiple writers or treats a
consumer/cache as authoritative.  
Impact: HIGH  
Mitigation: Require one unique fact per matrix entry, encode the writer policy
in the schema, and add a test that rejects duplicate facts.

## RISK-2: V2 topology leaks into CAT

Trigger: The contract describes Harness V2 internals instead of a bounded
external interface.  
Impact: HIGH  
Mitigation: Represent V2 only as an external consumer/provider boundary and
forbid V2 implementation paths in the A020-01 scope.

## RISK-3: Read-only consumers gain write authority

Trigger: An adapter or derived artifact is described as a co-authoritative
writer.  
Impact: HIGH  
Mitigation: Every entry declares an explicit write policy; consumer-facing
policies are read-only or evidence-only.

## RISK-4: Contract and schema drift

Trigger: The prose matrix and machine-readable contract diverge.  
Impact: MEDIUM  
Mitigation: Keep the canonical matrix as a schema example and validate it with
targeted tests plus CAT-wide validation.

## Security and recovery floor

This slice accepts no external input, touches no secrets, and performs no
remote or destructive mutation. Rollback is deletion/reversion of the three
new A020-01 artifacts.

Decision: PROCEED
