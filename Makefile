UV ?= uv
NPM ?= npm
PYTHON ?= $(UV) run --frozen --all-groups python
DATASET ?=
RUN_ID ?= repro-v1
EPOCHS ?= 30
ALLOW_SYNTHETIC ?= 0
SYNTHETIC_FLAG = $(if $(filter 1,$(ALLOW_SYNTHETIC)),--allow-synthetic,)
JAVA_TEST_FLAGS ?=

.PHONY: setup data train eval bench test test-java test-python lint-python eval-smoke report security

bench:
	$(PYTHON) scripts/bench_pipeline.py $(SYNTHETIC_FLAG) $(JAVA_TEST_FLAGS)

test: test-python test-java

test-java:
	$(PYTHON) scripts/record_maven_tests.py $(JAVA_TEST_FLAGS)

data train eval:
	$(PYTHON) scripts/reproduce.py $@ --dataset "$(DATASET)" --run-id "$(RUN_ID)" --epochs "$(EPOCHS)" $(SYNTHETIC_FLAG)

setup:
	$(UV) sync --frozen --all-groups
	$(NPM) --prefix frontend ci --ignore-scripts --no-audit --no-fund

test-python:
	$(PYTHON) scripts/record_tests.py --phase security-python --coverage

lint-python:
	$(PYTHON) -m ruff check ml_service scripts
	$(PYTHON) -m ruff format --check ml_service scripts
	$(PYTHON) -m mypy
	$(PYTHON) scripts/check_unsafe_paths.py
	$(PYTHON) scripts/check_repo_hygiene.py
	$(PYTHON) scripts/render_readme_metrics.py --check

eval-smoke:
	$(PYTHON) scripts/eval_smoke.py --allow-synthetic

report:
	$(PYTHON) scripts/aggregate_reports.py
	$(PYTHON) scripts/render_readme_metrics.py

security:
	$(PYTHON) scripts/security_gate.py
