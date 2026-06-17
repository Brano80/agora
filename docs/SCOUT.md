# AGORA scout — the self-upgrading research loop

A watchdog/research agent that keeps AGORA a *living* project. It runs on **your
machine** on a schedule, looks for things worth changing, and writes
**proposals** for your review. It never edits the schema, snapshots, or model.

## The loop (human-gated, self-checking)
```
 scout (daily, local + Qwen)  ->  proposals/*.md  ->  you review
        │                                                  │
        │ deterministic facts + Qwen brief                 ▼
        └──────────────  approve  ──►  I implement  ──►  consistency gate + tests
```
Nothing is auto-applied. Approved changes must pass the gate (no accounting
leaks) and the test suite before they are trusted — the same "validate before
trusting" rule as the rest of AGORA.

## What it checks (deterministic — no LLM needed)
- **DATA_REVISION** — a snapshot value differs from the latest live DBnomics
  value for the baseline year (beyond tolerance) → propose updating + re-validate.
- **NEWER_DATA** — DBnomics has more recent observations than the baseline year.
- **LIVE_FAIL** — a live-enabled series didn't return data (dimensions to fix).
- **SNAPSHOT_ONLY** — series not yet wired live (e.g. labour share / AMECO).
- **COVERAGE_GAP** — a target country has no calibrated snapshot.
- **ROADMAP** — declared-but-inactive schema layers awaiting the next module.

The Qwen layer only **prioritises and narrates** these facts. It is instructed
to invent nothing — no series codes, numbers, or sources beyond the findings.

## Local Qwen setup (OpenAI-compatible)
Serve Qwen locally and point the scout at it via environment variables:

| Server | Default base URL | Set |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | `AGORA_LLM_MODEL=qwen3` (or your tag) |
| LM Studio | `http://localhost:1234/v1` | `AGORA_LLM_BASE_URL=http://localhost:1234/v1` |
| vLLM | `http://localhost:8000/v1` | `AGORA_LLM_BASE_URL=...`, `AGORA_LLM_API_KEY=...` |

```bash
export AGORA_LLM_BASE_URL=http://localhost:11434/v1
export AGORA_LLM_MODEL=qwen3
python scripts/run_scout.py --geo DE FR
```
If the model is down the scout still runs (deterministic findings only).

## Run it
```bash
python scripts/run_scout.py --geo DE FR     # live DBnomics + Qwen brief if up
python scripts/run_scout.py --no-llm        # facts only, no model
python scripts/run_scout.py --offline       # no network (snapshot only)
```

## Schedule it (daily, on your machine)
**Windows Task Scheduler** (PowerShell, runs every day at 07:00):
```powershell
$action  = New-ScheduledTaskAction -Execute "python" `
  -Argument "scripts\run_scout.py --geo DE FR" -WorkingDirectory "C:\Users\brano\Projects\AGORA"
$trigger = New-ScheduledTaskTrigger -Daily -At 7am
Register-ScheduledTask -TaskName "AGORA scout" -Action $action -Trigger $trigger
```
**cron** (Linux/macOS):
```cron
0 7 * * *  cd /path/to/AGORA && /usr/bin/python3 scripts/run_scout.py --geo DE FR >> proposals/cron.log 2>&1
```

## Reviewing
Open the newest `proposals/*.md`. Ask me to walk through it — I'll explain each
proposal, what it changes, and the calibration/consistency impact, and implement
only the ones you approve. (Optionally, a Cowork scheduled task can read the
queue each morning and surface new proposals to you automatically.)

## Safety rails
- Proposals only; the scout has no write access to schema/snapshots/model.
- Deterministic facts are separated from LLM narrative; the model can't fabricate
  numbers into a change.
- Every approved change re-runs the consistency gate + tests.

---

## Hardening update

Three more capabilities:

- **Catalog discovery (deterministic, always on).** Cross-references
  `docs/DATA-SOURCES.md` against the connectors we have and emits one `TOOL`
  finding per catalog section listing sources with no connector yet (BIS, WID,
  EU KLEMS, Penn World Table, Epoch, FIGARO/I-O, energy, …). This turns the
  data-sources catalog into a live connector backlog.
- **DBnomics dataset discovery (live, opt-in).** `--discover` scans provider
  dataset lists for datasets matching AGORA's themes (wage, capital, debt,
  wealth, productivity, …) that we don't use yet, emitting `NEW_DATASET`
  findings. Off by default to keep daily runs lean; parsing is defensive.
- **Per-proposal draft patches (Qwen).** When the local model is up, the scout
  attaches a concrete, conservative implementation sketch to the highest-value
  proposals (which file, what to change), capped by `--max-patches`. The model
  is instructed to fabricate no numbers or codes — patches are review drafts.

```bash
python scripts/run_scout.py --geo DE FR --discover     # + live dataset scan
python scripts/run_scout.py --max-patches 8            # more draft patches
```

---

## Patch hardening (anti-hallucination)

The local model sometimes invented file paths in its draft patches (e.g.
`datasets/ameco.py`, which doesn't exist), and even once paths were grounded it
could still pick a *real but wrong* file (e.g. proposing the `live=` flip in
`data/connectors/dbnomics.py` when the flag actually lives in
`schema/accounts.py`). Three defenses now apply:

1. **Grounded prompt.** `draft_patch` is given the real repo file list
   (`scout.repo_files()`) and a hard rule: reference ONLY paths in that list; if
   the target file isn't listed, name the closest real file or say a new file
   must be created — never invent a path.
2. **File excerpts (the edit site).** `scout.build_excerpts()` selects the files
   whose *contents* matter for the finding — a kind-based shortlist
   (`_KIND_FILES`), the geo snapshot when the finding is country-specific, and
   any real path the finding's own text references — then feeds their **actual
   current contents** into the patch prompt, focused on the series code and
   budget-bounded (≤ ~14k chars over ≤ 3 files, so a local model's context isn't
   blown). The model now edits the symbol that demonstrably exists (it can see
   `labour_share … live=False` and the inline "verify AMECO dims via
   `verify_live.py`" comment) instead of guessing where — or whether — code
   lives. This closes the "right-existence, wrong-file" gap that pillar 1 + the
   backstop alone could not catch.
3. **Deterministic backstop.** `scout.llm.unverified_paths()` scans every draft
   for path-like tokens and flags any that aren't real repo files. Flagged
   drafts get a visible ⚠ warning appended in the report, and the CLI prints the
   count (`draft patches: N (M path-flagged)`). This catches hallucinations even
   if the model ignores the prompt — it does not depend on model behaviour.

Known residual limit: the excerpts make the model far more likely to be right,
but they are a relevance *heuristic*, not a guarantee — the morning review still
has the final say. This just stops both recurring failure modes (invented paths,
and edits aimed at the wrong real file) from reaching the reviewer unmarked.
