.PHONY: bootstrap build validate all clean

bootstrap:
	python scripts/download_official_sources.py

build:
	python scripts/build_data_foundation.py

validate:
	python scripts/validate_foundation.py

all: bootstrap build validate

clean:
	rm -f processed/delta_fpna_foundation.sqlite \
	      processed/fact_route_aircraft_monthly.csv \
	      processed/fact_route_monthly.csv
