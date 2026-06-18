# CAT Mission Pipeline Mermaid Charts

## 1. End-to-end GO-mode pipeline

```mermaid
flowchart LR
    I[Intent] --> MP[Mission Pack]
    MP --> P[Plan and Decompose]
    P --> B[BEAD Queue]
    B --> D[Dispatch]
    D --> E[Execute]
    E --> M[Magnets Observe and Collect]
    M --> V[Score and Validate]
    V --> C{Confidence Gate}
    C -->|90-100 Auto-Proceed| N[Next BEAD]
    C -->|70-89 Proceed| R[Reviewer Proceed]
    C -->|50-69 Self-Heal| H[Remediation BEAD]
    C -->|0-49 Escalate| X[Human Replan]
    N --> B
    H --> B
    R --> L[Learn and Close]
    X --> MP
```

## 2. Atomic control planes

```mermaid
flowchart TB
    subgraph Mission Plane
        MR[Mission Registry]
        MC[Mission Contract]
        AC[Acceptance Criteria]
    end
    subgraph Execution Plane
        BQ[BEAD Queue]
        AD[Agent Dispatch]
        TB[Tool Budget]
    end
    subgraph Evidence Plane
        LOG[Logs]
        DIFF[Diffs]
        TEST[Test Results]
        ART[Artifacts]
    end
    subgraph Governance Plane
        CG[Completeness Gate]
        SG[Substantive Gate]
        TG[Control Gate]
        PG[Promotion Gate]
    end
    subgraph Learning Plane
        DL[Decision Log]
        IL[Incident Log]
        KB[Pattern Library]
    end

    MR --> MC --> AC --> BQ --> AD --> TB
    AD --> LOG
    AD --> DIFF
    AD --> TEST
    AD --> ART
    LOG --> CG
    DIFF --> SG
    TEST --> SG
    ART --> PG
    CG --> PG
    SG --> PG
    TG --> PG
    PG --> DL --> KB
    PG --> IL --> KB
```

## 3. Agent orchestration

```mermaid
flowchart LR
    O[Orchestrator] --> S[Scout]
    O --> B[Builder]
    O --> R[Reviewer]
    O --> A[Auditor]
    O --> Sec[Security]
    O --> W[Scribe]

    S --> CXT[Context Snapshot]
    B --> OUT[Work Product]
    R --> QR[Quality Review]
    A --> GR[Governance Review]
    Sec --> SR[Security Review]
    W --> EV[Evidence Bundle]

    CXT --> EV
    OUT --> EV
    QR --> EV
    GR --> EV
    SR --> EV
    EV --> G{Confidence Gate}
```

## 4. LLM/model routing

```mermaid
flowchart TB
    M[Mission Pack] --> C[Complexity Classifier]
    C -->|M1/C1 Simple| L1[Local Fast Model minimax]
    C -->|M2/C2 Structured| L2[Local Coding Model kimi]
    C -->|M3/C3 Complex| L3[Strong Coding Reasoning claude-sonnet]
    C -->|M4/C4 Atomic| F[Frontier Reasoning claude-opus + Human Gate]

    L1 --> V[Validation]
    L2 --> V
    L3 --> V
    F --> V
    V -->|Pass| E[Evidence Bundle]
    V -->|Fail| FB[Fallback or Escalation]
    FB --> C
```

## 5. CI and CI/CD validation ladder

```mermaid
flowchart TB
    PR[Pull Request] --> RH[Repo Health]
    RH --> SC[Schema Validation]
    SC --> HA[Harness Alignment Validation]
    HA --> MM[Mermaid Fence Validation]
    MM --> UT[Pytest]
    UT --> EB[Evidence Bundle Artifact]
    EB --> CS[Confidence Score]
    CS -->|>=90| AP[Auto-Proceed Eligible]
    CS -->|70-89| HR[Human Review Required]
    CS -->|<70| BL[Block Promotion]
    AP --> REL[Release / Merge]
    HR --> REL
```

## 6. Gate stack

```mermaid
flowchart LR
    MP[Mission Pack] --> CG[Completeness Gate]
    CG --> RG[Routing Gate]
    RG --> AG[Authority Gate]
    AG --> EG[Execution Gate]
    EG --> SVG[Substantive Validation Gate]
    SVG --> ESG[Evidence Sufficiency Gate]
    ESG --> PG[Promotion Gate]
    PG --> LG[Learning Gate]
```
