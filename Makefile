.PHONY: build ask eval ui test shell clean

IMAGE := agentic-loop-qa:latest

build:
	docker build -t $(IMAGE) .

# make ask Q="Who designed the Eiffel Tower?"
ask:
	docker run --rm --env-file .env $(IMAGE) ask "$(Q)"

eval:
	mkdir -p reports
	docker run --rm --env-file .env -v $$(pwd)/reports:/app/reports $(IMAGE) eval --out /app/reports/report.json

ui:
	docker run --rm -p 8000:8000 --env-file .env $(IMAGE) ui --host 0.0.0.0 --port 8000

test:
	docker run --rm --entrypoint python $(IMAGE) -m pytest -q

shell:
	docker run --rm -it --env-file .env --entrypoint /bin/bash $(IMAGE)

clean:
	docker rmi $(IMAGE) 2>/dev/null || true
