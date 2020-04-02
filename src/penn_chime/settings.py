#!/usr/bin/env python

import datetime

from .parameters import Parameters, Regions, Disposition


def get_defaults():
    return Parameters(
        population=3600000,
        covid_census_value=10,
        covid_census_date=(datetime.datetime.utcnow() - datetime.timedelta(hours=6)).date(),
        total_covid_beds=300,
        icu_covid_beds=30,
        covid_ventilators=10,
        date_first_hospitalized=datetime.date(2020,3,7),
        doubling_time=4.0,
        hospitalized=Disposition(0.025, 7),
        icu=Disposition(0.0075, 9),
        infectious_days=14,
        market_share=0.15,
        n_days=100,
        relative_contact_rate=0.3,
        ventilators=Disposition(0.005, 10),
    )
