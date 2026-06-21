#!/usr/bin/env python3
"""
HTTP wrapper for CAT: thin FastAPI server that calls cat_resolve_go.py internally.

Allows Harness V2's CAT adapter to dispatch to CAT via HTTP POST without subprocess.
"""

import json
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    print(f"[cat_http_server] ERROR: FastAPI/Pydantic not installed: {e}", file=sys.stderr)
    print("[cat_http_server] Install with: pip install fastapi pydantic uvicorn", file=sys.stderr)
    sys.exit(1)


app = FastAPI(title="Chromatic Atomic Tower HTTP Wrapper", version="1.0.0")


class RunRequest(BaseModel):
    prompt: str
    entrypoint: str = "go"
    metadata: dict = {}


class RunResponse(BaseModel):
    ok: bool
    output: str
    service: str = "chromatic-atomic-tower"
    sprint: str = "unknown"


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        state_file = Path(__file__).parent.parent / "state" / "TOWER_STATE.yaml"
        sprint = "unknown"
        if state_file.exists():
            try:
                import yaml
                with open(state_file) as f:
                    state = yaml.safe_load(f)
                    sprint = state.get("active_sprint", "unknown")
            except Exception:
                pass
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "chromatic-atomic-tower",
        "sprint": sprint,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/run", response_model=RunResponse)
async def run_mission(req: RunRequest):
    """Dispatch a mission to CAT GO."""
    cat_root = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            ["python", str(cat_root / "scripts" / "cat_resolve_go.py"), "--objective", req.prompt],
            capture_output=True,
            timeout=30,
            text=True,
            cwd=str(cat_root)
        )

        return RunResponse(
            ok=result.returncode == 0,
            output=result.stdout or result.stderr,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="CAT dispatch timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dispatch error: {e}")


if __name__ == "__main__":
    port = int(os.getenv("ATOMIC_TOWER_PORT", "8900"))
    log_level = os.getenv("ATOMIC_TOWER_LOG_LEVEL", "info")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level=log_level)
