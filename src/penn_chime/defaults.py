"""Defaults."""
import datetime
from .utils import RateLos


class Regions:
    """Arbitrary number of counties."""

    def __init__(self, **kwargs):
        susceptible = 0
        for key, value in kwargs.items():
            setattr(self, key, value)
            susceptible += value
        self._susceptible = susceptible

    @property
    def susceptible(self):
        return self._susceptible


class Constants:
    def __init__(
        self,
        *,
        current_hospitalized: int,
        doubling_time: int,
        relative_contact_rate: int,
        region: Regions,

        total_non_covid_beds: int,
        total_non_covid_icu_beds: int,
        total_non_covid_vents: int,

        hospitalized: RateLos,
        icu: RateLos,
        ventilators: RateLos,

        as_date: bool = False,
        market_share: float = 1.0,
        max_y_axis: int = None,
        n_days: int = 60,
        recovery_days: int = 14,

        census_date: datetime.date = datetime.datetime.today(),
        selected_offset: int = -1

    ):
        self.region = region
        self.current_hospitalized = current_hospitalized
        self.doubling_time = doubling_time
        self.relative_contact_rate = relative_contact_rate

        self.hospitalized = hospitalized
        self.icu = icu
        self.ventilators = ventilators

        self.as_date = as_date
        self.market_share = market_share
        self.max_y_axis = max_y_axis
        self.n_days = n_days
        self.recovery_days = recovery_days

        self.total_non_covid_beds = total_non_covid_beds
        self.total_non_covid_icu_beds = total_non_covid_icu_beds
        self.total_non_covid_vents = total_non_covid_vents

        self.census_date = census_date
        self.selected_offset = selected_offset

    def __repr__(self) -> str:
        return f"Constants(susceptible_default: {self.region.susceptible})"
