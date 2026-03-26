SHELL := /bin/bash

.PHONY: docker-up setup-env
.ONESHELL:

docker-up:
	docker compose up -d

setup-env:
	@set -euo pipefail
	cd backend

	if [ -f ".env" ]; then
		echo "backend/.env already exists. Refusing to overwrite."
		exit 1
	fi

	read -r -s -p "OPENAI_API_KEY: " OPENAI_API_KEY; echo
	read -r -s -p "LANGSMITH_API_KEY (optional): " LANGSMITH_API_KEY; echo

	LANGSMITH_TRACING=false
	if [ -n "$$LANGSMITH_API_KEY" ]; then
		LANGSMITH_TRACING=true
	fi

	printf '%s\n' \
		"OPENAI_API_KEY=$$OPENAI_API_KEY" \
		"OPENAI_MODEL=gpt-4o-mini" \
		"LANGSMITH_API_KEY=$$LANGSMITH_API_KEY" \
		"LANGSMITH_PROJECT=inboxpilot-ai" \
		"LANGSMITH_TRACING=$$LANGSMITH_TRACING" \
		"ALGORITHM=HS256" \
		"ACCESS_TOKEN_EXPIRE_MINUTES=30" \
		"DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inboxpilot" \
		"REDIS_URL=redis://localhost:6379/0" \
		"CORS_ORIGINS=http://localhost:3000,http://localhost:3001" \
		"CONFIDENCE_THRESHOLD=0.7" \
		"MAX_MESSAGE_LENGTH=10000" \
		> .env

	echo "Wrote backend/.env"
