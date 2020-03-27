"""Parameters.

Changes affecting results or their presentation should also update
`change_date`, so users can see when results have last changed
"""

from .utils import RateLos


class Parameters:
    """Parameters."""

    def __init__(
        self,
        *,
        current_hospitalized: int,
        doubling_time: float,
        known_infected: int,
        relative_contact_rate: float,
        susceptible: int,

        total_beds: int,
        total_non_covid_beds: int,
        total_icu_beds: int,
        total_non_covid_icu_beds: int,
        total_vents: int,
        total_non_covid_vents: int,

        hospitalized: RateLos,
        icu: RateLos,
        ventilators: RateLos,

        as_date: bool = False,
        market_share: float = 1.0,
        max_y_axis: int = None,
        max_y_axis_set: bool = False,
        n_days: int = 60,
        recovery_days: int = 14,
        author: str = "Jane Doe",
        scenario: str = "COVID model"
                
    ):
        self.current_hospitalized = current_hospitalized
        self.doubling_time = doubling_time
        self.known_infected = known_infected
        self.relative_contact_rate = relative_contact_rate
        self.susceptible = susceptible

        self.hospitalized = hospitalized
        self.icu = icu
        self.ventilators = ventilators

        self.as_date = as_date
        self.market_share = market_share
        self.max_y_axis = max_y_axis
        self.max_y_axis_set = max_y_axis_set
        self.n_days = n_days
        self.recovery_days = recovery_days

        self.total_beds = total_beds
        self.total_non_covid_beds = total_non_covid_beds
        self.total_icu_beds = total_icu_beds
        self.total_non_covid_icu_beds = total_non_covid_icu_beds
        self.total_vents = total_vents
        self.total_non_covid_vents = total_non_covid_vents

        self.author = author
        self.scenario = scenario

        self.labels = {
            "total": "Total",
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
            "hospitalized": hospitalized,
            "icu": icu,
            "ventilators": ventilators,
        }

    def change_date(self):
        """
        This reflects a date from which previously-run reports will no
        longer match current results, indicating when users should
        re-run their reports
        """
        return "March 23 2020"
