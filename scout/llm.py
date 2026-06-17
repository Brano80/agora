"""Local-LLM client (OpenAI-compatible) for the scout's reasoning tier.

Targets a LOCAL Qwen served by Ollama / LM Studio / vLLM. Standard library only.
Degrades gracefully: if the endpoint is down the scout still emits deterministic
findings; the LLM only adds a prioritised narrative and draft patches.

Patch drafting is HARDENED against hallucinated / mis-located edits three ways:
  1. the prompt is grounded with the real repo file list and forbids referencing
     anything off it;
  2. the prompt also carries FILE EXCERPTS - the actual current contents of the
     files most relevant to the finding - so the model edits the real symbol
     that already exists rather than guessing where code lives;
  3. `unverified_paths()` is a deterministic backstop that flags any path-like
     token in a draft that does not exist in the repo - so even if the model
     ignores the instructions, the human reviewer is warned.

Configure via environment:
  AGORA_LLM_BASE_URL  (default http://localhost:11434/v1   # Ollama)
  AGORA_LLM_MODEL     (default qwen3)
  AGORA_LLM_API_KEY   (default 'not-needed')
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import List, Optional


class QwenClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None, timeout: float = 90.0):
        self.base_url = (base_url or os.getenv(
            "AGORA_LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.model = model or os.getenv("AGORA_LLM_MODEL", "qwen3")
        self.api_key = api_key or os.getenv("AGORA_LLM_API_KEY", "not-needed")
        self.timeout = timeout

    def available(self) -> bool:
        try:
            req = urllib.request.Request(
                self.base_url + "/models",
                headers={"Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status == 200
        except Exception:
            return False

    def chat(self, messages: List[dict], temperature: float = 0.2,
             max_tokens: int = 1400) -> Optional[str]:
        payload = json.dumps({
            "model": self.model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens, "stream": False,
        }).encode()
        try:
            req = urllib.request.Request(
                self.base_url + "/chat/completions", data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


SCOUT_SYSTEM = (
    "You are AGORA's research scout. AGORA is a stock-flow-consistent sandbox "
    "for EU-economy / post-labour policy scenarios. You are given DETERMINISTIC "
    "findings as JSON. Write a concise, prioritised brief for a human reviewer. "
    "Rules: do NOT invent data, series codes, numbers, or sources - use only "
    "what is in the findings. Be conservative. Group by urgency, give the "
    "concrete next action for each, and flag anything that would change "
    "calibration (and thus needs re-validation against the consistency gate). "
    "Output GitHub-flavoured markdown, no preamble."
)

PATCH_SYSTEM = (
    "You are AGORA's implementation assistant. Given ONE finding (JSON), the "
    "REPO FILES list, and FILE EXCERPTS (the actual current contents of the "
    "files most relevant to this finding), draft the SMALLEST concrete change "
    "to address it.\n"
    "HARD RULES:\n"
    "- You may reference ONLY file paths that appear verbatim in the REPO FILES "
    "list. NEVER invent a path. If the file you'd change is not in the list, do "
    "not guess - name the closest existing file from the list, or state plainly "
    "that a NEW file must be created and give its intended path.\n"
    "- Locate the EXACT edit site from the FILE EXCERPTS: name the real symbol / "
    "field / line that already exists there; do not guess where code lives or "
    "invent a config structure. If the change flips a flag or value, quote the "
    "current line verbatim and show the edited line. If the code you'd change is "
    "NOT in the excerpts, say so plainly rather than inventing its location.\n"
    "- Use only values present in the finding's evidence; never fabricate "
    "numbers, series codes, or sources. If a value must come from a source, "
    "write 'verify via <source>'.\n"
    "Output a short markdown snippet (a few lines, optionally one code block). "
    "No preamble. This is a draft for human review, not an applied change."
)

# path-like tokens that contain a directory separator and a code/data extension
_PATH_RE = re.compile(
    r"(?<![\w./-])[A-Za-z0-9_.\-]+/[A-Za-z0-9_./\-]+\.(?:py|json|md|txt|ya?ml|toml|cfg)")


def draft_brief(client: QwenClient, findings_json: str) -> Optional[str]:
    return client.chat([
        {"role": "system", "content": SCOUT_SYSTEM},
        {"role": "user", "content":
            "Findings (JSON):\n\n" + findings_json +
            "\n\nWrite the prioritised review brief."},
    ])


def draft_patch(client: QwenClient, finding_json: str,
                file_list: Optional[List[str]] = None,
                file_excerpts: Optional[str] = None) -> Optional[str]:
    """Draft an implementation sketch for one finding.

    `file_list` grounds the set of allowable paths; `file_excerpts` carries the
    actual current contents of the most-relevant files so the model edits the
    real symbol instead of guessing where (or whether) it exists.
    """
    files = "\n".join(file_list or [])
    parts = ["REPO FILES (you may reference ONLY these):\n" + files]
    if file_excerpts:
        parts.append(
            "FILE EXCERPTS (actual current contents of the most relevant files; "
            "find the exact edit site here, do not guess):\n\n" + file_excerpts)
    parts.append("Finding (JSON):\n\n" + finding_json)
    return client.chat([
        {"role": "system", "content": PATCH_SYSTEM},
        {"role": "user", "content": "\n\n".join(parts)},
    ], temperature=0.1, max_tokens=500)


def unverified_paths(text: Optional[str], file_list: List[str]) -> List[str]:
    """Deterministic backstop: return path-like tokens in `text` that are not
    real repo files. Catches hallucinated paths regardless of model behaviour."""
    if not text:
        return []
    known = set(file_list)
    known_base = {p.rsplit("/", 1)[-1] for p in file_list}
    out: List[str] = []
    for m in _PATH_RE.finditer(text):
        tok = m.group(0)
        if "://" in text[max(0, m.start() - 3):m.start()] or tok.startswith(("http", "www")):
            continue
        norm = tok.lstrip("./")
        if norm in known or norm.rsplit("/", 1)[-1] in known_base:
            continue
        if norm not in out:
            out.append(norm)
    return out
