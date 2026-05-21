"""
GemmaAudit JCL Parser
=====================

Two-stage pipeline for Job Control Language (JCL) batch scripts:

  Stage 1 — Deterministic regex extraction:
      JOB header, EXEC PGM=/PROC= steps, DD DSN= statements,
      multi-line continuations, comment skipping.

  Stage 2 — Local LLM enrichment (Gemma 4 via Ollama, optional):
      Per-step business-intent inference and dataset role classification.
      Falls back gracefully when no local model server is reachable —
      regex output remains complete and self-contained.

Emits nodes/edges in the same shape as `CobolParser`, so the unified
Knowledge Graph stitched in `parser.py` can simply union the two
parsers' outputs.
"""
from __future__ import annotations

import os
import re
import json
from typing import Dict, List, Optional, Any

from backend.llm_client import call_local_llm_simple, is_local_llm_available


# ---------------------------------------------------------------------------
# Regex grammar (IBM JCL pragmatic subset — covers the constructs that
# orchestrate the COBOL modules in `backend/samples/`).
# ---------------------------------------------------------------------------
RE_STATEMENT     = re.compile(r"^//(\S*)\s+(\S+)(?:\s+(.*))?$")
RE_COMMENT       = re.compile(r"^//\*")
RE_END_OF_STREAM = re.compile(r"^/\*\s*$")
RE_PGM           = re.compile(r"\bPGM=([A-Z0-9\-_.]+)", re.IGNORECASE)
RE_PROC          = re.compile(r"\bPROC=([A-Z0-9\-_.]+)", re.IGNORECASE)
RE_DSN           = re.compile(r"\bDSN=([A-Z0-9\-_.&()]+)", re.IGNORECASE)
RE_SYSOUT        = re.compile(r"\bSYSOUT=([A-Z*]+)", re.IGNORECASE)
RE_DISP          = re.compile(r"\bDISP=\(?([A-Z,()\s]+?)\)?(?:,|$)", re.IGNORECASE)
RE_JOB_DESC      = re.compile(r"'([^']+)'")


class JclParser:
    """Parses `.jcl` / `.job` files into nodes/edges for the unified KG."""

    def __init__(self, samples_dir: Optional[str], llm_enrich: bool = True):
        self.samples_dir = samples_dir
        self.llm_enrich = llm_enrich
        self.nodes: Dict[str, dict] = {}
        self.edges: List[dict] = []
        self._llm_probed: Optional[bool] = None  # lazy probe cache

    # ------------------------------------------------------------------
    # Continuation handling
    # ------------------------------------------------------------------
    def _coalesce_continuations(self, raw_lines: List[str]) -> List[str]:
        """Joins continued JCL statements (col-3 blank = continuation marker)."""
        out: List[str] = []
        buf: str = ""
        for line in raw_lines:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            if not line.startswith("//"):
                if RE_END_OF_STREAM.match(line):
                    # /* terminates an inline DD * data stream; we ignore the payload.
                    pass
                continue
            if RE_COMMENT.match(line):
                continue
            # Continuation: '//' followed immediately by whitespace.
            if buf and len(line) > 2 and line[2] == " ":
                cont = line[2:].strip()
                buf = buf.rstrip().rstrip(",") + "," + cont
            else:
                if buf:
                    out.append(buf)
                buf = line
        if buf:
            out.append(buf)
        return out

    # ------------------------------------------------------------------
    # File-level parse
    # ------------------------------------------------------------------
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.readlines()

        statements = self._coalesce_continuations(raw)

        job_name: Optional[str] = None
        job_desc: str = ""
        steps: List[Dict[str, Any]] = []
        current_step: Optional[Dict[str, Any]] = None

        for stmt in statements:
            m = RE_STATEMENT.match(stmt)
            if not m:
                continue
            name = m.group(1) or ""
            op = m.group(2).upper()
            params = m.group(3) or ""

            if op == "JOB":
                job_name = name
                desc_match = RE_JOB_DESC.search(params)
                job_desc = desc_match.group(1) if desc_match else ""
            elif op == "EXEC":
                pgm = RE_PGM.search(params)
                proc = RE_PROC.search(params)
                if pgm:
                    target_kind, target_name = "program", pgm.group(1).upper()
                elif proc:
                    target_kind, target_name = "proc", proc.group(1).upper()
                else:
                    # Bare-form `EXEC PROCNAME` (PROC= keyword omitted).
                    first = params.split(",")[0].strip()
                    target_kind = "proc" if first and "=" not in first else "unknown"
                    target_name = first.upper() if target_kind == "proc" else None
                current_step = {
                    "step_name": name,
                    "target_kind": target_kind,
                    "target_name": target_name,
                    "dd": [],
                    "raw_params": params.strip(),
                }
                steps.append(current_step)
            elif op == "DD" and current_step is not None:
                dsn = RE_DSN.search(params)
                sysout = RE_SYSOUT.search(params)
                disp = RE_DISP.search(params)
                current_step["dd"].append({
                    "dd_name": name,
                    "dsn": dsn.group(1).upper() if dsn else None,
                    "sysout": sysout.group(1) if sysout else None,
                    "disp": disp.group(1).strip() if disp else None,
                    "is_inline": params.strip().startswith("*"),
                })

        result = {
            "job_name": job_name or os.path.splitext(os.path.basename(file_path))[0].upper(),
            "job_desc": job_desc,
            "steps": steps,
            "source_file": os.path.basename(file_path),
        }

        # Stage 2: LLM enrichment.
        if self.llm_enrich and self._llm_reachable():
            for step in result["steps"]:
                step["intent"] = self._infer_step_intent(result["job_name"], result["job_desc"], step)

        return result

    # ------------------------------------------------------------------
    # LLM enrichment helpers
    # ------------------------------------------------------------------
    def _llm_reachable(self) -> bool:
        if self._llm_probed is None:
            self._llm_probed = is_local_llm_available()
        return self._llm_probed

    def _infer_step_intent(self, job_name: str, job_desc: str, step: Dict[str, Any]) -> Optional[str]:
        """Asks the local Gemma 4 model to summarize the business purpose of one step."""
        dd_summary = ", ".join(
            f"{d['dd_name']}={d['dsn'] or ('SYSOUT=' + str(d['sysout']))}"
            for d in step["dd"] if d.get("dsn") or d.get("sysout")
        ) or "(no datasets)"

        prompt = (
            "You are a terse mainframe modernization analyst. In ONE sentence (max 25 words), "
            "describe the BUSINESS PURPOSE of this JCL step. Output only the sentence, no preamble.\n\n"
            f"Job: {job_name} — {job_desc or 'no description'}\n"
            f"Step name: {step['step_name']}\n"
            f"Invokes: {step['target_kind']}={step['target_name']}\n"
            f"DD statements: {dd_summary}\n"
        )
        out = call_local_llm_simple(
            messages=[
                {"role": "system", "content": "You are a terse mainframe modernization analyst."},
                {"role": "user", "content": prompt},
            ],
            timeout_seconds=10,
        )
        if not out:
            return None
        return out.strip().strip('"').strip("'")[:240]

    # ------------------------------------------------------------------
    # Directory-level parse → unified nodes/edges
    # ------------------------------------------------------------------
    def parse_directory(self) -> Dict[str, Any]:
        self.nodes = {}
        self.edges = []
        jobs: List[Dict[str, Any]] = []

        if not self.samples_dir or not os.path.exists(self.samples_dir):
            return {"nodes": [], "edges": [], "jobs": []}

        for file in sorted(os.listdir(self.samples_dir)):
            if file.lower().endswith((".jcl", ".job")):
                jobs.append(self.parse_file(os.path.join(self.samples_dir, file)))

        for job in jobs:
            job_id = f"JOB_{job['job_name']}"
            self.nodes[job_id] = {
                "id": job_id,
                "label": f"{job['job_name']}.JCL",
                "type": "job",
                "details": {
                    "description": job["job_desc"] or "JCL batch orchestration",
                    "sourceFile": job["source_file"],
                    "stepCount": len(job["steps"]),
                    "loc": len(job["steps"]) * 4,                  # rough proxy
                    "complexity": len(job["steps"]),
                    "riskIndex": min(100, 25 + len(job["steps"]) * 8),
                },
            }

            prev_step_id: Optional[str] = None
            for step in job["steps"]:
                step_id = f"{job['job_name']}:STEP:{step['step_name']}"
                self.nodes[step_id] = {
                    "id": step_id,
                    "label": step["step_name"],
                    "type": "step",
                    "details": {
                        "targetKind": step["target_kind"],
                        "targetName": step["target_name"],
                        "ddCount": len(step["dd"]),
                        "intent": step.get("intent"),
                        "description": step.get("intent")
                        or f"Executes {step['target_kind']} {step['target_name']}",
                    },
                }
                self.edges.append({
                    "source": job_id,
                    "target": step_id,
                    "type": "contains",
                    "label": "STEP",
                })
                if step["target_name"]:
                    # Step → Program / Step → Proc.
                    self.edges.append({
                        "source": step_id,
                        "target": step["target_name"],
                        "type": "executes",
                        "label": "EXEC",
                    })
                # Step → Step ordering edge (sequential batch flow).
                if prev_step_id is not None:
                    self.edges.append({
                        "source": prev_step_id,
                        "target": step_id,
                        "type": "next_step",
                        "label": "NEXT",
                    })
                prev_step_id = step_id

                for dd in step["dd"]:
                    if dd["dsn"]:
                        ds_id = f"DSN_{dd['dsn']}"
                        if ds_id not in self.nodes:
                            self.nodes[ds_id] = {
                                "id": ds_id,
                                "label": dd["dsn"],
                                "type": "dataset",
                                "details": {
                                    "description": f"Physical dataset '{dd['dsn']}'.",
                                    "disposition": dd["disp"],
                                },
                            }
                        self.edges.append({
                            "source": step_id,
                            "target": ds_id,
                            "type": "uses_dd",
                            "label": f"DD:{dd['dd_name']}",
                        })

        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "jobs": jobs,
        }


if __name__ == "__main__":
    p = JclParser(os.path.join(os.path.dirname(__file__), "samples"), llm_enrich=False)
    print(json.dumps(p.parse_directory(), indent=2))
