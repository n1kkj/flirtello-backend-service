# Makefile

.PHONY: test full-test podownload poupload pobuild

test:
	pytest --cov-report term --cov-report html -x 

full-test:
	./local-model-tests

run-bot:
	uvicorn src.telegram.bot:app --host 0.0.0.0 --port 48123

podownload:
	@test -s .poeditortoken || { echo "Error: .poeditortoken missing or empty"; exit 1; }
	@POEDITOR_TOKEN=$$(cat .poeditortoken) poeditorial export

poupload:
	@test -s .poeditortoken || { echo "Error: .poeditortoken missing or empty"; exit 1; }
	@poeditorial upload -a $$(cat .poeditortoken)

pobuild:
	@find src/telegram/locales -type f -name '*.po' -print0 | xargs -0 -I{} sh -c 'dir=$$(dirname "{}"); base=$$(basename "{}" .po); out="$$dir/$${base}.mo"; msgfmt -o "$$out" "{}" && echo "built $$out"'

.PHONY: delete-user
delete-user:
	@if [ -z "$(TG_ID)" ]; then \
		echo "Usage: make delete-user TG_ID=<telegram_id>"; \
		exit 1; \
	fi
	@echo "Deleting user with Telegram ID: $(TG_ID)"
	@python -m dotenv -f src/.env run -- python -m src.scripts.user_deletion --tg-id $(TG_ID)
