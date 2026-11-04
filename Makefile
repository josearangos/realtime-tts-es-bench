# Human-evaluation operations (feature 009). Run `make help`.
SHELL := /bin/bash
ENV_FILE ?= evaluation/.env
COMPOSE := docker compose -f evaluation/compose.yaml --env-file $(ENV_FILE)
PY ?= python
-include $(ENV_FILE)
export

LS_VERSION ?= 1.23.2
LS_PORT ?= 8080
EVAL_PROVISION ?= 1
LS_URL ?= http://127.0.0.1:$(LS_PORT)
PRE := evaluation/scripts/preflight.sh
CLI := PYTHONPATH=src $(PY) -m tts_bench.evaluation --url $(LS_URL)

.PHONY: help eval-up eval-down eval-reset eval-backup eval-restore eval-export eval-new-batch \
        eval-annotator eval-purge-voice eval-inspect

help: ## list the eval-* targets
	@echo "Human evaluation targets:"
	@echo "  eval-up                  build if needed, start Label Studio, provision projects"
	@echo "  eval-down                stop containers, keep data"
	@echo "  eval-reset               remove ALL evaluation data (asks to type RESET)"
	@echo "  eval-backup              write backups/evaluation/<UTC>.tar.gz"
	@echo "  eval-restore FILE=...    restore a backup into a clean environment"
	@echo "  eval-export [OUT=dir]    export annotations + quality report (default results/human/)"
	@echo "  eval-new-batch           archive the current batch and prepare a new one"
	@echo "  eval-annotator ID=a01    create a pseudonymous annotator"
	@echo "  eval-purge-voice VOICE=  remove a voice (consent withdrawal)"
	@echo "  eval-inspect             print annotator-visible task data"

eval-up:
	@$(PRE)
	@mkdir -p output/evaluation/served output/evaluation/private
	@evaluation/scripts/version_guard.sh
	@if docker image inspect tts-bench-label-studio:$(LS_VERSION) >/dev/null 2>&1; then B=--no-build; echo "using existing image (offline-safe)"; else B=--build; echo "first build: this needs network and may take several minutes"; fi; \
	  $(COMPOSE) up -d $$B --wait label-studio
	@if [ "$(EVAL_PROVISION)" = "1" ]; then \
	  if [ -n "$(REBUILD)" ] || ! docker image inspect tts-bench-provisioner:latest >/dev/null 2>&1; then \
	    $(COMPOSE) --profile provision build provisioner; fi; \
	  $(COMPOSE) --profile provision run --rm provisioner; \
	else echo "EVAL_PROVISION=0: skipping provisioning"; fi
	@echo "Label Studio: http://$${LS_BIND:-127.0.0.1}:$(LS_PORT)  (user $${LS_ADMIN_USER:-admin@eval.invalid})"

eval-down:
	@$(PRE)
	@$(COMPOSE) --profile provision down

eval-reset:
	@$(PRE)
	@read -p "This deletes ALL Label Studio data and output/evaluation/. Type RESET to confirm: " a; \
	  if [ "$$a" = "RESET" ]; then $(COMPOSE) --profile provision down -v && rm -rf output/evaluation && echo "reset done"; \
	  else echo "aborted, nothing changed"; fi

eval-backup:
	@$(PRE)
	@COMPOSE="$(COMPOSE)" LS_VERSION=$(LS_VERSION) evaluation/scripts/backup.sh

eval-restore:
	@$(PRE)
	@test -n "$(FILE)" || { echo "usage: make eval-restore FILE=backups/evaluation/<file>.tar.gz"; exit 2; }
	@COMPOSE="$(COMPOSE)" LS_VERSION=$(LS_VERSION) evaluation/scripts/restore.sh "$(FILE)"

eval-export:
	@$(PRE)
	@$(CLI) --token $$LS_API_TOKEN export $(if $(OUT),--out $(OUT),)

eval-new-batch:
	@$(PRE)
	@$(CLI) --token $$LS_API_TOKEN prepare --new-batch
	@$(CLI) --token $$LS_API_TOKEN provision --storage-path /label-studio/files/served

eval-annotator:
	@$(PRE)
	@test -n "$(ID)" || { echo "usage: make eval-annotator ID=a01 [RESET=1]"; exit 2; }
	@$(CLI) --token $$LS_API_TOKEN annotator $(ID) $(if $(RESET),--reset-password,)

eval-purge-voice:
	@$(PRE)
	@test -n "$(VOICE)" || { echo "usage: make eval-purge-voice VOICE=<voice name>"; exit 2; }
	@$(CLI) --token $$LS_API_TOKEN purge-voice "$(VOICE)"

eval-inspect:
	@$(PRE)
	@$(CLI) --token $$LS_API_TOKEN inspect
