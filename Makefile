.PHONY: bootstrap bootstrap-network history-download build build-network validate validate-network test compile check all network-history clean

bootstrap:
	python scripts/download_official_sources.py

bootstrap-network:
	python scripts/download_official_sources.py --group network

history-download:
	python scripts/download_t100_history.py --years 2019 2020 2021 2022 2023 2024 2025 2026

build:
	python scripts/build_data_foundation.py

build-network:
	python scripts/build_network_history.py

validate:
	python scripts/validate_foundation.py

validate-network:
	python scripts/validate_network_history.py

test:
	python -m unittest discover -s tests -v

compile:
	python -m compileall -q pipeline scripts tests

check: compile test

all: bootstrap build validate

network-history: bootstrap-network history-download build-network validate-network

clean:
	rm -f processed/delta_fpna_foundation.sqlite \
	      processed/fact_route_aircraft_monthly.csv \
	      processed/fact_route_monthly.csv \
	      processed/fact_network_kpi_monthly.csv \
	      processed/dim_airport.csv \
	      processed/dim_route.csv \
	      processed/dim_date.csv \
	      processed/network_source_manifest.csv \
	      processed/network_history_summary.json \
	      processed/network_history_validation.json
