# TerraDrift Makefile — common workflows.
# Run `make help` to see commands.

.DEFAULT_GOAL := help
PY := python
PIP := $(PY) -m pip

.PHONY: help install dev demo test lint type fmt clean docker reproduce reproduce-mini pilot

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

install: ## Install runtime deps
	$(PIP) install -e .

dev: ## Install dev deps
	$(PIP) install -e ".[dev]"
	pre-commit install || true

demo: ## Scan the included sample Terraform repo
	$(PY) -m terradrift.cli scan sample/aws-s3-public --output reports/demo.csv || test $$? -eq 1
	@echo "Report: reports/demo.csv"

test: ## Run unit tests with coverage
	$(PY) -m pytest --cov=terradrift --cov-report=term-missing

lint: ## Run ruff
	$(PY) -m ruff check .

type: ## Run mypy
	$(PY) -m mypy src

fmt: ## Auto-format
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

clean: ## Remove build & cache
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

docker: ## Build the distroless image
	docker build -t terradrift:dev .

reproduce-mini: ## Run the bundled 10-repository reproducibility pipeline
	$(PY) -m terradrift.cli reproduce --subset mini --max-commits 10 --output-dir reports/reproduce-mini

pilot: ## Run a fast 10-repository, 3-commit pilot study
	$(PY) -m terradrift.cli reproduce --subset mini --limit 10 --max-commits 3 --output-dir reports/pilot

reproduce: ## Reproduce results using the crawler manifest
	$(PY) -m terradrift.cli reproduce --subset full --manifest corpus/repos.csv --output-dir reports/reproduce-full
