"""Parameters.

Changes affecting results or their presentation should also update
constants.py `change_date``.
"""

from collections import namedtuple
import datetime
from typing import Optional

from .validators import (
    Positive, OptionalStrictlyPositive, StrictlyPositive, Rate, Date, OptionalDate
    )

# Parameters for each disposition (hospitalized, icu, ventilated)
#   The rate of disposition within the population of infected
#   The average number days a patient has such disposition

# Hospitalized:
#   2.5 percent of the infected population are hospitalized: hospitalized.rate is 0.025
#   Average hospital length of stay is 7 days: hospitalized.days = 7

# ICU:
#   0.75 percent of the infected population are in the ICU: icu.rate is 0.0075
#   Average number of days in an ICU is 9 days: icu.days = 9

# Ventilated:
#   0.5 percent of the infected population are on a ventilator: ventilated.rate is 0.005
#   Average number of days on a ventilator: ventilated.days = 10

# Be sure to multiply by 100 when using the parameter as a default to a percent widget!


Disposition = namedtuple("Disposition", ("rate", "days"))


class Regions:
    """Arbitrary regions to sum population."""

    def __init__(self, **kwargs):
        population = 0
        for key, value in kwargs.items():
            setattr(self, key, value)
            population += value
        self.population = population


class Parameters:
    """Parameters."""

    def __init__(
        self,
        *,
        covid_census_value: int, # used to be current_hospitalized
        covid_census_date: datetime.date, # added by Health Catalyst team
        total_covid_beds: int,
        icu_covid_beds: int,
        covid_ventilators: int,
        hospitalized: Disposition,
        icu: Disposition,
        relative_contact_rate: float,
        ventilators: Disposition, # used to be ventilated
        current_date: datetime.date = datetime.date.today() - datetime.timedelta(hours=6),
        social_distancing_start_date: datetime.date = datetime.date.today()  - datetime.timedelta(hours=6),
        date_first_hospitalized: Optional[datetime.date] = None,
        first_hospitalized_date_known: bool = False,
        doubling_time: Optional[float] = None,
        infectious_days: int = 14,
        market_share: float = 1.0,
        max_y_axis: Optional[int] = None,
        max_y_axis_set: bool = False,
        n_days: int = 100,
        population: Optional[int] = None,
        recovered: int = 0,
        region: Optional[Regions] = None,
        # Added by the Health Catalyst Team
        author: str = "Jane Doe",
        scenario: str = "COVID-19 Model",
    ):
        self.covid_census_value = StrictlyPositive(value=covid_census_value)
        self.covid_census_date = Date(value=covid_census_date)
        self.current_date = Date(value=current_date)
        self.relative_contact_rate = Rate(value=relative_contact_rate)

        self.total_covid_beds = StrictlyPositive(value=total_covid_beds)
        self.icu_covid_beds = StrictlyPositive(value=icu_covid_beds)
        self.covid_ventilators = StrictlyPositive(value=covid_ventilators)
        Rate(value=hospitalized.rate)
        Rate(value=icu.rate)
        StrictlyPositive(value=hospitalized.days)
        StrictlyPositive(value=icu.days),

        self.hospitalized = hospitalized
        self.icu = icu

        self.ventilators = ventilators

        if region is not None and population is None:
            self.region = region
            self.population = StrictlyPositive(value=region.population)
        elif population is not None:
            self.region = None
            self.population = StrictlyPositive(value=population)
        else:
            raise AssertionError('population or regions must be provided.')

        self.social_distancing_start_date = Date(value=social_distancing_start_date)
       
        self.date_first_hospitalized = OptionalDate(value=date_first_hospitalized)
        self.first_hospitalized_date_known = first_hospitalized_date_known
        self.doubling_time = OptionalStrictlyPositive(value=doubling_time)

        self.infectious_days = StrictlyPositive(value=infectious_days)
        self.market_share = Rate(value=market_share)
        self.max_y_axis = OptionalStrictlyPositive(value=max_y_axis)
        self.max_y_axis_set = max_y_axis_set
        self.n_days = StrictlyPositive(value=n_days)
        self.recovered = Positive(value=recovered)
        
        self.author = author
        self.scenario = scenario
            
        self.labels = {
            "hospitalized": "Hospitalized",
            "icu": "ICU",
            "ventilators": "Ventilators",
            "day": "Day",
            "date": "Date",
            "susceptible": "Susceptible",
            "infected": "Infected",
            "recovered": "Recovered",
        }

        self.dispositions = {
            "total": hospitalized,
            "hospitalized": hospitalized,
            "icu": icu,
            "ventilators": ventilators,
        }

        self.patient_chart_desc = {
            "hospitalized": "Hospitalized COVID-19 Admissions peak at",
            "icu": "ICU COVID-19 Admissions peak at",
            "ventilators": "COVID-19 Ventilators peak at",
            "total": "Total COVID-19 Admissions peaks at"
        }
        
        self.eqpt_chart_desc = {
            "hospitalized": "Hospitalized COVID-19 Beds",
            "icu": "ICU COVID-19 Beds",
            "ventilators": "COVID-19 Ventilators",
            "total": "Total COVID-19 Beds"
        }
