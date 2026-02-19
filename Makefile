.PHONY: format, lint

format:
	isort --profile black .
	black .

lint:
	isort --profile black --diff .
	black --check --diff .
