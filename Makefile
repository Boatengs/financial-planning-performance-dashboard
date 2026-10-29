.PHONY: download download-sec download-t100 download-bts build validate test compile check all app clean

YEARS := 2019 2020 2021 2022 2023 2024 2025 2026
CURRENT_YEAR := 2026

download: download-sec download-t100 download-bts

download-sec:
	python scripts/download_official_sources.py --force

download-t100:
	python scripts/download_t100_history.py --years $(YEARS) --refresh-years $(CURRENT_YEAR)

download-bts:
	python scripts/download_bts_tables.py --years $(YEARS) --refresh-years $(CURRENT_YEAR)

build:
	python scripts/build_data_foundation.py

validate:
	python scripts/validate_foundation.py

test:
	python -m unittest discover -s tests -v

compile:
	python -m compileall -q pipeline scripts tests app

check: compile test

all: download build validate

app:
	streamlit run app/Home.py

clean:
	rm -rf processed/*.csv processed/*.json processed/*.sqlite
