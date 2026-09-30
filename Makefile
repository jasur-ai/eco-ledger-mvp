.PHONY: install demo test serve bot docker clean

install:
	pip install -r requirements.txt

demo:
	python3 scripts/run_demo.py

test:
	python3 -m pytest -q tests/

serve:
	uvicorn src.api.app:app --host 0.0.0.0 --port 8000

bot:
	python3 scripts/bot.py

docker:
	docker compose up --build

clean:
	rm -rf data/*.db web/map.html reports/DEMO-NATIJA.md data/measurements.csv
