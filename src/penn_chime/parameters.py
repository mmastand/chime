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
        beds_borrow: bool = True,
        total_covid_beds: int,
        icu_covid_beds: int,
        covid_ventilators: int,
        non_icu: Disposition,
        icu: Disposition,
        relative_contact_rate: float,
        ventilators: Disposition, # used to be ventilated
        current_date: datetime.date = datetime.date.today() - datetime.timedelta(hours=6),
        social_distancing_is_implemented: bool = False,
        mitigation_date: datetime.date = datetime.date.today()  - datetime.timedelta(hours=6),
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
        scenario: str = "Scenario Name",
        # PPE Params
        masks_n95: int = 5,
        masks_surgical: int = 7,
        face_shield: int = 5,
        gloves: int = 10,
        gowns: int = 10,
        other_ppe: int = 2,
        masks_n95_icu: int = 5,
        masks_surgical_icu: int = 7,
        face_shield_icu: int = 5,
        gloves_icu: int = 10,
        gowns_icu: int = 10,
        other_ppe_icu: int = 2,
        
        # Staffing Params
        # Non-ICU
        nurses: int = 6,
        physicians: int = 20,
        advanced_practice_providers: int= 20,
        healthcare_assistants: int = 10,
        other_staff=10,
        # ICU
        nurses_icu: int = 2,
        physicians_icu: int = 12,
        advanced_practice_providers_icu: int = 12,
        healthcare_assistants_icu: int = 10,
        other_staff_icu=10,
        # Shift Duration
        shift_duration: int = 12,
    ):
        self.covid_census_value = covid_census_value
        self.covid_census_date = Date(value=covid_census_date)
        self.current_date = Date(value=current_date)
        self.relative_contact_rate = Rate(value=relative_contact_rate)

        self.beds_borrow = beds_borrow
        self.total_covid_beds = total_covid_beds
        self.icu_covid_beds = icu_covid_beds
        self.covid_ventilators = covid_ventilators
        Rate(value=non_icu.rate)
        Rate(value=icu.rate)

        self.non_icu = non_icu
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

        self.mitigation_date = mitigation_date
        self.social_distancing_is_implemented = social_distancing_is_implemented

        ####
        if date_first_hospitalized is None: 
            self.date_first_hospitalized = datetime.date(2020, 3, 1)
        else:
            if date_first_hospitalized > self.current_date:
                self.date_first_hospitalized = self.current_date
            else:
                self.date_first_hospitalized = date_first_hospitalized
        ####

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
        
        # PPE Params
        self.masks_n95 = masks_n95
        self.masks_surgical = masks_surgical
        self.face_shield = face_shield
        self.gloves = gloves 
        self.gowns = gowns
        self.other_ppe = other_ppe
        self.masks_n95_icu = masks_n95_icu
        self.masks_surgical_icu = masks_surgical_icu
        self.face_shield_icu = face_shield_icu
        self.gloves_icu = gloves_icu
        self.gowns_icu = gowns_icu
        self.other_ppe_icu = other_ppe_icu
        
        # Staffing Params
        # Non-ICU
        self.nurses = nurses
        self.physicians = physicians
        self.advanced_practice_providers = advanced_practice_providers
        self.healthcare_assistants = healthcare_assistants
        self.other_staff = other_staff
        # ICU
        self.nurses_icu = nurses_icu
        self.physicians_icu = physicians_icu
        self.advanced_practice_providers_icu = advanced_practice_providers_icu
        self.healthcare_assistants_icu = healthcare_assistants_icu
        self.other_staff_icu = other_staff_icu
        # Shift Duration
        self.shift_duration = shift_duration
        
        self.labels = {
            "hospitalized": "Hospitalized",
            "icu": "ICU",
            "ventilators": "Ventilators",
            "total": "Total",
            "non_icu": "Non-ICU",
            "day": "Day",
            "date": "Date",
            "susceptible": "Susceptible",
            "infected": "Infected",
            "recovered": "Recovered",
            "masks_n95": "Masks - N95",
            "masks_surgical": "Masks - Surgical",
            "face_shield": "Face Shields",
            "gloves": "Gloves",
            "gowns": "Gowns",
            "other_ppe": "Other",
            "masks_n95_icu": "Masks - N95 (ICU)",
            "masks_surgical_icu": "Masks - Surgical (ICU)",
            "face_shield_icu": "Face Shields (ICU)",
            "gloves_icu": "Gloves (ICU)",
            "gowns_icu": "Gowns (ICU)",
            "other_ppe_icu": "Other (ICU)",
            "nurses": "Patients/Nurse",
            "physicians": "Physicians",
            "advanced_practice_providers": "Advanced Practice Providers (APP)",
            "healthcare_assistants": "Healthcare Assistants (PCT, CNA, etc)",
            "nurses_icu": "Patients/Nurse (ICU)",
            "physicians_icu": "Physicians (ICU)",
            "advanced_practice_providers_icu": "Advanced Practice Providers (APP) (ICU)",
            "healthcare_assistants_icu": "Healthcare Assistants (PCT, CNA, etc) (ICU)",
            "shift_duration": "Shift Duration",
        }

        self.dispositions = {
            "total": non_icu,
            "non_icu": non_icu,
            "icu": icu,
            "ventilators": ventilators,
        }

        self.actuals_labels = {
            "total_admissions_actual": "Total ",
            "non_icu_admissions_actual": "Non-ICU ",
            "icu_admissions_actual": "ICU ",
            "intubated_actual": "Intubated ",
            "total_census_actual": "Total ",
            "non_icu_census_actual": "Non-ICU ",
            "icu_census_actual": "ICU ",
            "ventilators_in_use_actual": "Ventialtors In Use ",
        }
        
        self.admits_patient_chart_desc = {
            "Non-ICU": "Non-ICU COVID-19 census peak at",
            "ICU": "ICU COVID-19 Admissions peak at",
            "Ventilators": "COVID-19 Ventilators peak at",
            "Total": "Total COVID-19 Admissions peaks at",
        }

        self.census_patient_chart_desc = {
            "Non-ICU": "Non-ICU COVID-19 Census peaks at",
            "ICU": "ICU COVID-19 Census peaks at",
            "Ventilators": "COVID-19 Ventilator usage peaks at",
            "Total": "Total COVID-19 Census peaks at"
        }
        
        self.beds_chart_desc = {
            "Non-ICU": "Non-ICU COVID-19 Beds",
            "ICU": "ICU COVID-19 Beds",
            "Ventilators": "COVID-19 Ventilators",
            "Total": "Total COVID-19 Beds",
        }

        self.ppe_labels = {
            "total": "Total",
            "non_icu": "Non-ICU",
            "icu": "ICU",
            "masks_n95": {
                "label": "Masks - N95",
                "col1_name": "masks_n95_total",
                "col2_name": "masks_n95_non_icu",
                "col3_name": "masks_n95_icu",
            },
            "masks_surgical": {
                "label": "Masks - Surgical",
                "col1_name": "masks_surgical_total",
                "col2_name": "masks_surgical_non_icu",
                "col3_name": "masks_surgical_icu",
            },
            "face_shield": {
                "label": "Face Shields",
                "col1_name": "face_shield_total",
                "col2_name": "face_shield_non_icu",
                "col3_name": "face_shield_icu",
            },
            "gloves": {
                "label": "Gloves",
                "col1_name": "gloves_total",
                "col2_name": "gloves_non_icu",
                "col3_name": "gloves_icu",
            },
            "gowns": {
                "label": "Gowns",
                "col1_name": "gowns_total",
                "col2_name": "gowns_non_icu",
                "col3_name": "gowns_icu",
            },
            "other_ppe": {
                "label": "Other PPE",
                "col1_name": "other_ppe_total",
                "col2_name": "other_ppe_non_icu",
                "col3_name": "other_ppe_icu",
            },
        }

        self.staffing_labels = {
            "total": "Total",
            "icu": "ICU",
            "non_icu": "Non-ICU",
            "nurses": {
                "label": "Nurses",
                "col1_name": "nurses_total",
                "col2_name": "nurses_non_icu",
                "col3_name": "nurses_icu",
            },
            "physicians": {
                "label": "Physicians",
                "col1_name": "physicians_total",
                "col2_name": "physicians_non_icu",
                "col3_name": "physicians_icu",
            },
            "advanced_practice_providers": {
                "label": "Advanced Practice Providers",
                "col1_name": "advanced_practice_providers_total",
                "col2_name": "advanced_practice_providers_non_icu",
                "col3_name": "advanced_practice_providers_icu",
            },
            "healthcare_assistants": {
                "label": "Healthcare Assistants",
                "col1_name": "healthcare_assistants_total",
                "col2_name": "healthcare_assistants_non_icu",
                "col3_name": "healthcare_assistants_icu",
            },
            "other_staff": {
                "label": "Other Staff",
                "col1_name": "other_staff_total",
                "col2_name": "other_staff_non_icu",
                "col3_name": "other_staff_icu",
            },
        }
