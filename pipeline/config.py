from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PROCESSED = ROOT / "processed"
PUBLISHED = ROOT / "data" / "published"
TABLEAU = ROOT / "tableau"
PROCESSED.mkdir(parents=True, exist_ok=True)

ANALYSIS_START_YEAR = 2019
ANALYSIS_END_YEAR = 2026

T100_COLUMNS = ['year',
 'month',
 'origin',
 'origin_numeric_code',
 'origin_wac',
 'origin_city_name',
 'destination',
 'destination_numeric_code',
 'destination_wac',
 'destination_city_name',
 'carrier_code',
 'carrier_entity_code',
 'carrier_group_code',
 'distance_miles',
 'service_class',
 'aircraft_group',
 'aircraft_type',
 'aircraft_configuration',
 'departures_performed',
 'departures_scheduled',
 'payload_pounds',
 'seats',
 'passengers',
 'freight_pounds',
 'mail_pounds',
 'ramp_to_ramp_minutes',
 'airborne_minutes',
 'carrier_wac']

INT_FIELDS = {'airborne_minutes',
 'aircraft_configuration',
 'aircraft_group',
 'aircraft_type',
 'carrier_group_code',
 'carrier_wac',
 'departures_performed',
 'departures_scheduled',
 'destination_numeric_code',
 'destination_wac',
 'distance_miles',
 'freight_pounds',
 'mail_pounds',
 'month',
 'origin_numeric_code',
 'origin_wac',
 'passengers',
 'payload_pounds',
 'ramp_to_ramp_minutes',
 'seats',
 'year'}

# SEC CompanyFacts concepts used for consolidated Delta Air Lines, Inc. actuals.
# "duration" facts are income-statement or cash-flow amounts reported over a period;
# "instant" facts are balance-sheet amounts reported at a period end.
# Each metric uses the first tag in its list that is present in CompanyFacts.
FINANCIAL_METRICS = {
    'revenue': {'label': 'Total Operating Revenue', 'namespace': 'us-gaap', 'kind': 'duration',
                'tags': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues'],
                'unit': 'USD', 'domain': 'Financial Performance'},
    'operating_expenses': {'label': 'Total Operating Expense', 'namespace': 'us-gaap', 'kind': 'duration',
                           'tags': ['CostsAndExpenses'], 'unit': 'USD', 'domain': 'Operating Costs'},
    'operating_income': {'label': 'Operating Income', 'namespace': 'us-gaap', 'kind': 'duration',
                         'tags': ['OperatingIncomeLoss'], 'unit': 'USD', 'domain': 'Profitability'},
    'net_income': {'label': 'Net Income', 'namespace': 'us-gaap', 'kind': 'duration',
                   'tags': ['NetIncomeLoss'], 'unit': 'USD', 'domain': 'Profitability'},
    'fuel_costs': {'label': 'Aircraft Fuel and Related Taxes', 'namespace': 'us-gaap', 'kind': 'duration',
                   'tags': ['FuelCosts'], 'unit': 'USD', 'domain': 'Operating Costs'},
    'labor_costs': {'label': 'Salaries, Wages and Related Costs', 'namespace': 'us-gaap', 'kind': 'duration',
                    'tags': ['LaborAndRelatedExpense'], 'unit': 'USD', 'domain': 'Operating Costs'},
    'maintenance_costs': {'label': 'Aircraft Maintenance Materials and Outside Repairs', 'namespace': 'us-gaap',
                          'kind': 'duration', 'tags': ['AircraftMaintenanceMaterialsAndRepairs'],
                          'unit': 'USD', 'domain': 'Operating Costs'},
    'depreciation_amortization': {'label': 'Depreciation and Amortization', 'namespace': 'us-gaap',
                                  'kind': 'duration', 'tags': ['DepreciationDepletionAndAmortization'],
                                  'unit': 'USD', 'domain': 'Operating Costs'},
    'operating_cash_flow': {'label': 'Net Cash Provided by Operating Activities', 'namespace': 'us-gaap',
                            'kind': 'duration', 'tags': ['NetCashProvidedByUsedInOperatingActivities'],
                            'unit': 'USD', 'domain': 'Cash Flow'},
    'capex_total': {'label': 'Capital Expenditures (Total)', 'namespace': 'us-gaap', 'kind': 'duration',
                    'tags': ['PaymentsToAcquireProductiveAssets'], 'unit': 'USD', 'domain': 'Capital Expenditure'},
    'capex_flight_equipment': {'label': 'Capital Expenditures: Flight Equipment', 'namespace': 'us-gaap',
                               'kind': 'duration', 'tags': ['PaymentsForFlightEquipment'],
                               'unit': 'USD', 'domain': 'Capital Expenditure'},
    'capex_ground_technology': {'label': 'Capital Expenditures: Ground Property, Equipment and Technology',
                                'namespace': 'us-gaap', 'kind': 'duration',
                                'tags': ['PaymentsToAcquireOtherProductiveAssets'],
                                'unit': 'USD', 'domain': 'Capital Expenditure'},
    'cash': {'label': 'Cash and Cash Equivalents', 'namespace': 'us-gaap', 'kind': 'instant',
             'tags': ['CashAndCashEquivalentsAtCarryingValue'], 'unit': 'USD', 'domain': 'Liquidity'},
    'assets': {'label': 'Total Assets', 'namespace': 'us-gaap', 'kind': 'instant',
               'tags': ['Assets'], 'unit': 'USD', 'domain': 'Balance Sheet'},
    'liabilities_and_equity': {'label': 'Total Liabilities and Stockholders\' Equity', 'namespace': 'us-gaap',
                               'kind': 'instant', 'tags': ['LiabilitiesAndStockholdersEquity'],
                               'unit': 'USD', 'domain': 'Balance Sheet'},
    'stockholders_equity': {'label': 'Stockholders\' Equity', 'namespace': 'us-gaap', 'kind': 'instant',
                            'tags': ['StockholdersEquity'], 'unit': 'USD', 'domain': 'Balance Sheet'},
    'debt_total': {'label': 'Debt Including Current Maturities (Excluding Leases)', 'namespace': 'us-gaap',
                   'kind': 'instant', 'tags': ['LongTermDebt', 'DebtLongtermAndShorttermCombinedAmount'],
                   'fill_from_alternate_tags': True, 'unit': 'USD', 'domain': 'Capital Structure'},
    'debt_current': {'label': 'Current Maturities of Debt', 'namespace': 'us-gaap', 'kind': 'instant',
                     'tags': ['LongTermDebtCurrent'], 'unit': 'USD', 'domain': 'Capital Structure'},
    'employees': {'label': 'Employees (Full-Time Equivalent)', 'namespace': 'dei', 'kind': 'instant',
                  'tags': ['EntityNumberOfEmployees'], 'unit': 'employee', 'domain': 'Workforce'},
}

NETWORK_KPIS = [('passengers', 'Passengers', 'count', 'Reported', 'SUM(passengers)'),
 ('seats', 'Available Seats', 'count', 'Reported', 'SUM(seats)'),
 ('asm', 'Available Seat Miles (ASM)', 'seat-miles', 'Derived', 'SUM(seats * distance_miles)'),
 ('rpm', 'Revenue Passenger Miles (RPM)', 'passenger-miles', 'Derived', 'SUM(passengers * distance_miles)'),
 ('load_factor', 'Load Factor', '%', 'Derived', 'RPM / ASM'),
 ('departures_performed', 'Departures Performed', 'count', 'Reported', 'SUM(departures_performed)'),
 ('departures_scheduled', 'Departures Scheduled', 'count', 'Reported', 'SUM(departures_scheduled)'),
 ('completion_rate', 'Completion Rate', '%', 'Derived', 'Departures Performed / Departures Scheduled'),
 ('passengers_per_departure',
  'Passengers per Departure',
  'passengers/departure',
  'Derived',
  'Passengers / Departures Performed'),
 ('average_stage_length',
  'Average Stage Length',
  'miles',
  'Derived',
  'SUM(distance * departures performed) / SUM(departures performed)'),
 ('freight_pounds', 'Freight Transported', 'lb', 'Reported', 'SUM(freight_pounds)'),
 ('mail_pounds', 'Mail Transported', 'lb', 'Reported', 'SUM(mail_pounds)'),
 ('airborne_hours', 'Airborne Time', 'hours', 'Derived', 'SUM(airborne_minutes) / 60')]

# (metric_id, label, unit, class, formula, domain, source_system)
DERIVED_KPIS = [
    ('free_cash_flow', 'Free Cash Flow', 'USD', 'Derived',
     'operating_cash_flow - capex_total', 'Cash Flow', 'Derived from SEC CompanyFacts'),
    ('total_liabilities', 'Total Liabilities', 'USD', 'Derived',
     'liabilities_and_equity - stockholders_equity', 'Balance Sheet', 'Derived from SEC CompanyFacts'),
    ('operating_margin', 'Operating Margin', '%', 'Derived',
     'operating_income / revenue', 'Profitability', 'Derived from SEC CompanyFacts'),
    ('net_margin', 'Net Margin', '%', 'Derived', 'net_income / revenue', 'Profitability',
     'Derived from SEC CompanyFacts'),
    ('revenue_growth_yoy', 'Revenue Growth YoY', '%', 'Derived',
     'revenue_t / revenue_same_period_prior_year - 1', 'Financial Performance', 'Derived from SEC CompanyFacts'),
    ('fuel_share_of_opex', 'Fuel Share of Operating Expense', '%', 'Derived',
     'fuel_costs / operating_expenses', 'Operating Costs', 'Derived from SEC CompanyFacts'),
]

# Mainline unit economics: Form 41 (P-1.2, P-12a) over T-100 capacity, same DL reporting entity.
UNIT_ECONOMICS_KPIS = [
    ('pax_revenue', 'Scheduled Passenger Revenue (Mainline)', 'USD', 'Reported', 'Form 41 P-1.2 TRANS_REV_PAX x 1000'),
    ('mainline_revenue', 'Operating Revenue excl. Transport-Related (Mainline)', 'USD', 'Derived',
     'OP_REVENUES - TRANS_REVENUE'),
    ('mainline_expense', 'Operating Expense excl. Transport-Related (Mainline)', 'USD', 'Derived',
     'OP_EXPENSES - TRANS_EXPENSES'),
    ('mainline_operating_margin', 'Operating Margin excl. Transport-Related (Mainline)', '%', 'Derived',
     '(mainline_revenue - mainline_expense) / mainline_revenue'),
    ('prasm_cents', 'Passenger Revenue per ASM', 'cents', 'Derived', 'pax_revenue / ASM x 100'),
    ('trasm_cents', 'Total Revenue per ASM (Mainline)', 'cents', 'Derived', 'mainline_revenue / ASM x 100'),
    ('casm_cents', 'Cost per ASM (Mainline)', 'cents', 'Derived', 'mainline_expense / ASM x 100'),
    ('casm_ex_fuel_cents', 'Cost per ASM excl. Fuel (Mainline)', 'cents', 'Derived',
     '(mainline_expense - scheduled_fuel_cost) / ASM x 100'),
    ('yield_cents', 'Passenger Yield', 'cents', 'Derived', 'pax_revenue / RPM x 100'),
    ('fuel_cost_per_gallon', 'Fuel Cost per Gallon (Scheduled Service)', 'USD/gallon', 'Derived',
     'scheduled_fuel_cost / scheduled_fuel_gallons'),
    ('asm_per_gallon', 'ASMs per Gallon of Fuel', 'seat-miles/gallon', 'Derived', 'ASM / scheduled_fuel_gallons'),
]

FPNA_KPIS = [
    ('actual_vs_budget', 'Actual vs Budget Variance', 'USD', 'Modeled', 'Actual - Budget', 'FP&A'),
    ('actual_vs_budget_pct', 'Actual vs Budget Variance %', '%', 'Modeled', '(Actual - Budget) / ABS(Budget)', 'FP&A'),
    ('actual_vs_forecast', 'Actual vs Forecast Variance', 'USD', 'Modeled', 'Actual - Forecast', 'FP&A'),
    ('forecast_accuracy', 'Forecast Accuracy', '%', 'Modeled', '1 - ABS(Actual - Forecast) / ABS(Actual)', 'FP&A'),
    ('forecast_bias', 'Forecast Bias', '%', 'Modeled', '(Forecast - Actual) / ABS(Actual)', 'FP&A'),
]
