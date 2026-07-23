APP_NAME := $(shell uvx --from=toml-cli toml get --toml-path pyproject.toml project.name)
APP_VERSION := $(shell uv version --short)
VENV = .venv

.PHONY: help install sync outdated update test tests coverage coverage-html lint format fmt clean docs check meson-build run flatpak flatpak-deps flatpak-build flatpak-install flatpak-run check-clean bump beta patch minor major release shell stop

help:
	@echo "Filigrane Development Management Commands (using uv):"
	@echo "  make install       Set up virtual environment and install dependencies using uv"
	@echo "  make sync          Sync virtual environment with dependencies"
	@echo "  make run           Run the application using uv"
	@echo "  make test          Run pytest suite using uv"
	@echo "  make coverage      Run pytest suite with code coverage"
	@echo "  make lint          Run linter (ruff) and type checker (mypy) using uv"
	@echo "  make format        Format code using ruff via uv"
	@echo "  make check         Run formatting, linting, and tests via uv"
	@echo "  make meson-build   Build project using Meson build system"
	@echo "  make flatpak-build Build Flatpak package"
	@echo "  make flatpak-run   Run Flatpak app"
	@echo "  make docs          Serve documentation locally"
	@echo "  make clean         Clean temporary cache and build artifacts"

shell:
	tmuxinator

stop:
	tmux kill-session -t $(APP_NAME)

install:
	devbox run uv --version
	devbox run uv venv --clear --python 3.12 --system-site-packages $(VENV)
	devbox run python --version
	devbox run uv pip install -e .[dev]

sync: install
	devbox run uv sync --extra dev

outdated:
	devbox run uv pip list --outdated

update:
	devbox run uv sync --upgrade
	devbox update
	devbox run pre-commit autoupdate

test: tests

tests:
	devbox run uv run pytest tests/ -v

coverage:
	devbox run uv run pytest --cov=filigrane

coverage-html:
	devbox run uv run pytest --cov=filigrane --cov-report=html

lint:
	devbox run pre-commit run --all-files

fmt: format

format:
	devbox run uv run ruff format filigrane tests
	devbox run uv run ruff check --fix filigrane tests

clean:
	rm -rf $(VENV) build build-dir .mypy_cache .pytest_cache .ruff_cache htmlcov .coverage dist *.egg-info uv.lock
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	devbox run serve htdocs

check: format lint tests

meson-build:
	devbox run meson setup build --prefix=/usr
	devbox run ninja -C build

run:
	devbox run uv run python -m filigrane.main

flatpak: flatpak-build ## Alias for flatpak-build

flatpak-deps: ## Generate Flatpak Python dependencies using uv and flatpak-pip-generator
	devbox run uvx --from flatpak-pip-generator python -m flatpak_pip_generator --pyproject-file pyproject.toml --prefer-wheels Pillow,cryptography,cffi --runtime org.gnome.Sdk//49 --ignore-pkg PyGObject,pycairo -o flatpak/python3-requirements.json

flatpak-build: flatpak-deps ## Build flatpak package locally
	[ -d repo ] && [ ! -f repo/config ] && rm -rf repo || true
	devbox run flatpak-builder --force-clean --disable-rofiles-fuse --user --install-deps-from=flathub --repo=repo build-dir flatpak/io.gitlab.demsking.filigrane.json

flatpak-install: flatpak-deps ## Install flatpak package locally
	[ -d repo ] && [ ! -f repo/config ] && rm -rf repo || true
	devbox run flatpak-builder --force-clean --disable-rofiles-fuse --user --install --install-deps-from=flathub --repo=repo build-dir flatpak/io.gitlab.demsking.filigrane.json

flatpak-run: ## Run flatpak app
	flatpak run io.gitlab.demsking.filigrane

check-clean:
	@test -z "$$(git status --porcelain)" || (echo "Working tree is not clean" && exit 1)

bump:
	@test -n "$(VERSION)" || (echo "Usage: make bump VERSION=1.2.3" && exit 1)
	devbox run uv version "$(VERSION)"
	devbox run uv lock
	devbox run git add pyproject.toml uv.lock
	devbox run git commit -m "chore(release): bump version to $(VERSION)"

beta: check-clean
	@set -eu; \
	current="$$(uv version --short)"; \
	case "$$current" in \
		*b[0-9]*) \
			base="$${current%b*}"; \
			num="$${current##*b}"; \
			next="$$base""b$$((num + 1))"; \
			;; \
		*) \
			next="$$current""b1"; \
			;; \
	esac; \
	echo "Bumping version: $$current -> $$next"; \
	devbox run uv version "$$next"; \
	devbox run uv lock

patch: check-clean
	devbox run uv version --bump patch
	devbox run uv lock

minor: check-clean
	devbox run uv version --bump minor
	devbox run uv lock

major: check-clean
	devbox run uv version --bump major
	devbox run uv lock

release: check-clean
	devbox run uv sync
	devbox run git add pyproject.toml uv.lock
	devbox run git commit -m "chore(release): bump version to $(shell uv version --short)"
	devbox run git tag --annotate "v$(shell uv version --short)" --message "Release v$(shell uv version --short)"
