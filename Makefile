PYTHON ?= .venv/bin/python

.PHONY: install test refresh refresh-live newsletter dashboard build

install:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	cd web && npm install

test:
	$(PYTHON) -m pytest
	node --test tests/mailing.test.mjs tests/pageview.test.mjs

# Weekly data pull. Cached HTTP responses are reused; use refresh-live to ignore them.
refresh:
	$(PYTHON) -m inflammon refresh

refresh-live:
	$(PYTHON) -m inflammon refresh --force

# Archive the weekly issue. Sends only when NEWSLETTER_SEND=1 or you pass --send
# through the Python CLI. The default is a dry run.
newsletter:
	$(PYTHON) -m inflammon newsletter

dashboard:
	cd web && npm run dev -- --hostname 127.0.0.1 --port 43123

build:
	cd web && npm run build
