.PHONY: docs-api docs-validate

DOCS_SPEC=docs/integration/API_CONTRACTS.yaml
DOCS_OUTPUT=docs/integration/api.html

## Generate static HTML documentation from the OpenAPI contract
## Requires Node.js (`npx @redocly/cli`)
docs-api:
	npx @redocly/cli build-docs $(DOCS_SPEC) -o $(DOCS_OUTPUT)

## Validate that FastAPI exposes the same schema as the contract
docs-validate:
	REDIS_URL=redis://localhost:6379/0 \
	DB_PATH=./data/validate-openapi.db uv run python scripts/validate_openapi.py
