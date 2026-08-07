#!/usr/bin/env python3
"""
CAT Command Center HTTP Server

Serves CAT data files as JSON for the dashboard.
Uses stdlib only (http.server, threading, yaml).
"""

import os
import json
import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timedelta
import sys


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP server with threading support for concurrent requests."""
    daemon_threads = True


class CATRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for CAT API endpoints."""

    # Base directory: parent of 'reference/' (i.e., C:\.01_CAT)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Route GET requests to appropriate handlers."""
        path = self.path.split("?")[0]  # Remove query string if present

        routes = {
            "/": self.serve_dashboard,
            "/api/state": self.api_state,
            "/api/beads": self.api_beads,
            "/api/agents": self.api_agents,
            "/api/missions": self.api_missions,
            "/api/gates": self.api_gates,
            "/api/events": self.api_events,
            "/api/all": self.api_all,
        }

        if path in routes:
            routes[path]()
        else:
            self.send_error(404)

    def _send_json_response(self, data, status=200):
        """Send JSON response with CORS headers."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _send_html_response(self, html_content, status=200):
        """Send HTML response with CORS headers."""
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def _load_yaml(self, filepath):
        """Load and parse YAML file, return {} on error."""
        try:
            if not os.path.exists(filepath):
                return {}
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except Exception:
            return {}

    def _load_yaml_files_from_dir(self, directory):
        """Load all YAML files from a directory, return [] on error."""
        try:
            if not os.path.exists(directory):
                return []
            files = []
            for filename in os.listdir(directory):
                if filename.endswith(".yaml"):
                    filepath = os.path.join(directory, filename)
                    data = self._load_yaml(filepath)
                    if data:
                        files.append(data)
            return files
        except Exception:
            return []

    def serve_dashboard(self):
        """Serve dashboard.html from reference/ directory."""
        dashboard_path = os.path.join(self.BASE_DIR, "reference", "dashboard.html")
        try:
            with open(dashboard_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_html_response(content)
        except Exception:
            self._send_html_response("<h1>Dashboard not found</h1>", 404)

    def api_state(self):
        """GET /api/state - Return TOWER_STATE.yaml as JSON."""
        state_file = os.path.join(self.BASE_DIR, "state", "TOWER_STATE.yaml")
        data = self._load_yaml(state_file)
        self._send_json_response(data)

    def api_beads(self):
        """GET /api/beads - Return all BEADs from all status directories."""
        beads = []
        for status_dir in ["active", "queued", "completed", "failed"]:
            dir_path = os.path.join(self.BASE_DIR, "beads", status_dir)
            files = self._load_yaml_files_from_dir(dir_path)
            for bead in files:
                bead["_dir"] = status_dir
                beads.append(bead)
        self._send_json_response(beads)

    def api_agents(self):
        """GET /api/agents - Merge AGENT_SCORECARD with AGENT_REGISTRY."""
        scorecard_file = os.path.join(self.BASE_DIR, "agents", "registry", "AGENT_SCORECARD.yaml")
        registry_file = os.path.join(self.BASE_DIR, "agents", "registry", "AGENT_REGISTRY.yaml")

        scorecard = self._load_yaml(scorecard_file)
        registry = self._load_yaml(registry_file)

        # Create lookup of registry roles
        registry_lookup = {}
        if registry and "agents" in registry:
            for agent in registry["agents"]:
                role = agent.get("role")
                if role:
                    registry_lookup[role] = agent

        # Merge scorecard agents with registry data
        merged_agents = []
        if scorecard and "agents" in scorecard:
            for agent in scorecard["agents"]:
                role = agent.get("role")
                registry_data = registry_lookup.get(role, {})

                # Merge registry fields into scorecard agent
                merged = dict(agent)
                merged["autonomy_level"] = registry_data.get("autonomy_level", "")
                merged["can_dispatch"] = registry_data.get("can_dispatch", False)

                merged_agents.append(merged)

        # Build response object with merged agents
        response = dict(scorecard) if scorecard else {}
        response["agents"] = merged_agents

        self._send_json_response(response)

    def api_missions(self):
        """GET /api/missions - Return missions array from MISSION_REGISTRY."""
        registry_file = os.path.join(self.BASE_DIR, "missions", "registry", "MISSION_REGISTRY.yaml")
        data = self._load_yaml(registry_file)

        # Extract missions array, or return empty array
        missions = data.get("missions", []) if data else []
        self._send_json_response(missions)

    def api_gates(self):
        """GET /api/gates - Compute gate status from active BEADs."""
        # Load active BEADs
        active_dir = os.path.join(self.BASE_DIR, "beads", "active")
        active_beads = self._load_yaml_files_from_dir(active_dir)

        gates = {
            "confidence": {"status": "pass", "score": 0},
            "human": {"status": "pending"},
            "tool_budget": {"status": "ok"},
            "review": {"status": "open"},
            "promotion": {"status": "open"},
        }

        # Compute average confidence if active beads exist
        if active_beads:
            scores = []
            for bead in active_beads:
                if "confidence" in bead and isinstance(bead["confidence"], dict):
                    current = bead["confidence"].get("current", 0)
                    if isinstance(current, (int, float)):
                        scores.append(current)

            if scores:
                avg_score = sum(scores) / len(scores)
                gates["confidence"]["score"] = round(avg_score, 1)

                # Derive status based on score
                if avg_score >= 85:
                    gates["confidence"]["status"] = "pass"
                elif avg_score >= 70:
                    gates["confidence"]["status"] = "warn"
                else:
                    gates["confidence"]["status"] = "fail"

            # Check for human gate flags in any active BEAD
            for bead in active_beads:
                # Look for any indication of human gate flags
                if "handoff" in bead or "required_approval" in bead:
                    gates["human"]["status"] = "pending"
                    break

        self._send_json_response(gates)

    def _normalize_event(self, entry, bead_id=""):
        """Normalize a transition_history entry to dashboard event format."""
        return {
            "time": entry.get("timestamp", ""),
            "bead_id": entry.get("target_id") or bead_id,
            "from": entry.get("from_status", ""),
            "to": entry.get("to_status", ""),
            "actor": entry.get("actor", ""),
            "reason": entry.get("reason", ""),
            "ok": entry.get("guard_ok", True),
        }

    def api_events(self):
        """GET /api/events - Collect transition history from active and completed BEADs."""
        events = []

        # Load active and completed BEADs
        for status_dir in ["active", "completed"]:
            dir_path = os.path.join(self.BASE_DIR, "beads", status_dir)
            beads = self._load_yaml_files_from_dir(dir_path)

            for bead in beads:
                bead_id = bead.get("bead_id", "")
                if "transition_history" in bead and isinstance(bead["transition_history"], list):
                    for history_entry in bead["transition_history"]:
                        events.append(self._normalize_event(history_entry, bead_id))

        # Filter events from the last 7 days
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        filtered_events = []

        for event in events:
            timestamp_str = event.get("time")
            if timestamp_str:
                try:
                    # Parse ISO 8601 format (with timezone info if present)
                    if "T" in timestamp_str:
                        # Remove timezone info for parsing
                        if "+" in timestamp_str:
                            timestamp_str = timestamp_str.split("+")[0]
                        elif timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1]

                        event_time = datetime.fromisoformat(timestamp_str)

                        if event_time >= seven_days_ago:
                            filtered_events.append(event)
                except ValueError:
                    pass

        # Sort by timestamp descending and return latest 25
        filtered_events.sort(
            key=lambda x: x.get("time", ""), reverse=True
        )
        latest_events = filtered_events[:25]

        self._send_json_response(latest_events)

    def api_all(self):
        """GET /api/all - Return all data in a single object."""
        state_file = os.path.join(self.BASE_DIR, "state", "TOWER_STATE.yaml")
        scorecard_file = os.path.join(self.BASE_DIR, "agents", "registry", "AGENT_SCORECARD.yaml")
        registry_file = os.path.join(self.BASE_DIR, "agents", "registry", "AGENT_REGISTRY.yaml")
        missions_file = os.path.join(self.BASE_DIR, "missions", "registry", "MISSION_REGISTRY.yaml")

        # Gather state
        state = self._load_yaml(state_file)

        # Gather beads
        beads = []
        for status_dir in ["active", "queued", "completed", "failed"]:
            dir_path = os.path.join(self.BASE_DIR, "beads", status_dir)
            files = self._load_yaml_files_from_dir(dir_path)
            for bead in files:
                bead["_dir"] = status_dir
                beads.append(bead)

        # Gather agents (merged)
        scorecard = self._load_yaml(scorecard_file)
        registry = self._load_yaml(registry_file)

        registry_lookup = {}
        if registry and "agents" in registry:
            for agent in registry["agents"]:
                role = agent.get("role")
                if role:
                    registry_lookup[role] = agent

        merged_agents = []
        if scorecard and "agents" in scorecard:
            for agent in scorecard["agents"]:
                role = agent.get("role")
                registry_data = registry_lookup.get(role, {})
                merged = dict(agent)
                merged["autonomy_level"] = registry_data.get("autonomy_level", "")
                merged["can_dispatch"] = registry_data.get("can_dispatch", False)
                merged_agents.append(merged)

        agents = dict(scorecard) if scorecard else {}
        agents["agents"] = merged_agents

        # Gather missions
        missions_data = self._load_yaml(missions_file)
        missions = missions_data.get("missions", []) if missions_data else []

        # Gather gates
        gates = {
            "confidence": {"status": "pass", "score": 0},
            "human": {"status": "pending"},
            "tool_budget": {"status": "ok"},
            "review": {"status": "open"},
            "promotion": {"status": "open"},
        }

        active_dir = os.path.join(self.BASE_DIR, "beads", "active")
        active_beads = self._load_yaml_files_from_dir(active_dir)

        if active_beads:
            scores = []
            for bead in active_beads:
                if "confidence" in bead and isinstance(bead["confidence"], dict):
                    current = bead["confidence"].get("current", 0)
                    if isinstance(current, (int, float)):
                        scores.append(current)

            if scores:
                avg_score = sum(scores) / len(scores)
                gates["confidence"]["score"] = round(avg_score, 1)
                if avg_score >= 85:
                    gates["confidence"]["status"] = "pass"
                elif avg_score >= 70:
                    gates["confidence"]["status"] = "warn"
                else:
                    gates["confidence"]["status"] = "fail"

            for bead in active_beads:
                if "handoff" in bead or "required_approval" in bead:
                    gates["human"]["status"] = "pending"
                    break

        # Gather events
        events = []
        for status_dir in ["active", "completed"]:
            dir_path = os.path.join(self.BASE_DIR, "beads", status_dir)
            beads_for_events = self._load_yaml_files_from_dir(dir_path)

            for bead in beads_for_events:
                bead_id = bead.get("bead_id", "")
                if "transition_history" in bead and isinstance(bead["transition_history"], list):
                    for history_entry in bead["transition_history"]:
                        events.append(self._normalize_event(history_entry, bead_id))

        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        filtered_events = []

        for event in events:
            timestamp_str = event.get("time")
            if timestamp_str:
                try:
                    if "T" in timestamp_str:
                        if "+" in timestamp_str:
                            timestamp_str = timestamp_str.split("+")[0]
                        elif timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1]

                        event_time = datetime.fromisoformat(timestamp_str)

                        if event_time >= seven_days_ago:
                            filtered_events.append(event)
                except ValueError:
                    pass

        filtered_events.sort(
            key=lambda x: x.get("time", ""), reverse=True
        )
        latest_events = filtered_events[:25]

        # Build response
        response = {
            "state": state,
            "beads": beads,
            "agents": agents,
            "missions": missions,
            "gates": gates,
            "events": latest_events,
        }

        self._send_json_response(response)


def main():
    """Start the CAT Command Center server."""
    port = int(os.environ.get("CAT_PORT", "8000"))
    server = ThreadingHTTPServer(("", port), CATRequestHandler)
    print(f"CAT Command Center → http://localhost:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
