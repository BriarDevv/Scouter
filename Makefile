SHELL := /usr/bin/env bash

.PHONY: dev-up dev-down dev-status

dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-status:
	bash scripts/dev-status.sh
