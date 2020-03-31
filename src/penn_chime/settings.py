#!/usr/bin/env python

from datetime import datetime
from .defaults import Constants, Regions, RateLos

delaware = 564696
chester = 519293
montgomery = 826075
bucks = 628341
philly = 1581000

DEFAULTS = Constants(
    # EDIT YOUR DEFAULTS HERE
    region=Regions(
        delaware=delaware,
        chester=chester,
        montgomery=montgomery,
        bucks=bucks,
        philly=philly,
    ),
    
    total_non_covid_beds=300,
    total_non_covid_icu_beds=30,
    total_non_covid_vents=10,

    current_hospitalized=14,
    doubling_time=4.0,
    n_days=60,
    market_share=0.15,
    relative_contact_rate=0.3,
    hospitalized=RateLos(0.025, 7),
    icu=RateLos(0.0075, 9),
    ventilators=RateLos(0.005, 10),

    census_date=datetime.today(),
    selected_offset=-1
)
