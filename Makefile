PYTHON ?= .venv/bin/python

.PHONY: install test refresh refresh-live dashboard build

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	cd web && npm install

test:
	$(PYTHON) -m pytest

# Weekly data pull. Cached HTTP responses are reused; use refresh-live to ignore them.
refresh:
	$(PYTHON) -m inflammon refresh

refresh-live:
	$(PYTHON) -m inflammon refresh --force

dashboard:
	cd web && npm run dev -- --hostname 127.0.0.1 --port 43123

build:
	cd web && npm run build
