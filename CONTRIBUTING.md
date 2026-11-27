# Contributing

Use a phase/topic branch and conventional commits. Do not merge a failing gate
into main or describe unexecuted checks as passed. Keep user changes intact.

Install the pinned Python runtime with `uv sync --frozen --all-groups`.
`make lint-python test-python eval-smoke report` runs the current local Python
and evidence gates. Override PYTHON for an already synchronized environment.
The complete multi-service Make workflow remains unfinished; these targets are
not substitutes for Java, UI, security, deployment and end-to-end load acceptance.

The data/train/eval targets require an explicit DATASET. For the demo simulator,
also set ALLOW_SYNTHETIC=1 and use a new RUN_ID for each training candidate.
See docs/RUNBOOK.md for the benchmark and platform-test prerequisites. The Java
CI job trains its own explicit fixture rather than fetching unverified weights.

Use `uv run --frozen --all-groups pre-commit install` after installing the locked
hook runner. Hooks invoke the same tools as CI and never rewrite metrics.
Generated evidence belongs in reports, not hand-maintained Markdown tables.
The README renderer's check mode rejects drift. Golden evaluation updates require
an explicit `--update-golden`, a reason in DECISIONS and reviewer inspection of
changed metrics; do not loosen tolerance to hide a regression.

Keep raw data, installation keys, trained binaries and tool environments out of
Git. Read supplier licenses before downloading data. Demo generation must be
explicit and all simulation results must retain provenance. Never copy an old
provider credential from history. Report a suspected exposure privately to the
repository owner without reproducing its value in public issues.

Record commands and output summaries in docs/CHANGELOG_AGENT.md. Source-changing
edits during test execution invalidate its receipt and require a final rerun.
Python deprecation warnings are retained; they are not test failures or proof of
future framework compatibility.

The package uses semantic versioning. Add a CHANGELOG entry for observable
behavioral changes. No production release is declared while required checks or
security remediations remain open.
