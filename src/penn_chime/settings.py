#!/usr/bin/env python

import datetime

from .parameters import ForecastMethod, ForecastedMetric, Parameters, Regions, Disposition


def get_defaults():
    return Parameters(
        population=3600000,
        covid_census_value=10,
        covid_census_date=(datetime.datetime.utcnow() - datetime.timedelta(hours=6)).date(),
        total_covid_beds=300,
        icu_covid_beds=30,
        covid_ventilators=10,
        date_first_hospitalized=datetime.date(2020,3,1),
        doubling_time=4.0,
        non_icu=Disposition(0.025, 7),
        icu=Disposition(0.0075, 9),
        infectious_days=14,
        market_share=0.15,
        n_days=100,
        relative_contact_rate=0.3,
        ventilators=Disposition(0.005, 10),
        
        # Model Settings
        forecasted_metric = ForecastedMetric.DOUBLING_TIME,
        forecast_method = ForecastMethod.ETS,
        
        # PPE
        masks_n95=5,
        masks_surgical=7,
        face_shield=5,
        gloves=10,
        gowns=10,
        other_ppe=2,
        masks_n95_icu=5,
        masks_surgical_icu=7,
        face_shield_icu=5,
        gloves_icu=10,
        gowns_icu=10,
        other_ppe_icu=2,
        
        # Staffing Params
        # Non-ICU
        nurses = 6,
        physicians = 20,
        advanced_practice_providers = 20,
        healthcare_assistants = 10,
        other_staff=10,
        # ICU
        nurses_icu = 2,
        physicians_icu= 12,
        advanced_practice_providers_icu = 12,
        healthcare_assistants_icu = 10,
        other_staff_icu=10,
        # Shift Duration
        shift_duration = 12,
    )
