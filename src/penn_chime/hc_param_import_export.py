import base64
from datetime import (
    datetime, 
    date,
    timedelta,
)
import json
import io
from typing import Tuple

from .parameters import (
    Parameters, 
    Regions, 
    Disposition,
)

def constants_from_uploaded_file(file: io.StringIO) -> Tuple[Parameters, dict]:
    imported_params = json.loads(file.read())
    parameters = Parameters(
        population=imported_params["RegionalPopulation"],
        doubling_time=float(imported_params["DoublingTimeBeforeSocialDistancing"]) if "DoublingTimeBeforeSocialDistancing" in imported_params else 4.0,
        date_first_hospitalized=date.fromisoformat(imported_params["FirstHospitalizedCaseDate"]) if "FirstHospitalizedCaseDate" in imported_params else None,
        first_hospitalized_date_known=imported_params.get("FirstHospitalizedDateKnown", False), # Added in v2.0.0
        # known_infected=imported_params.get("CurrentlyKnownRegionalInfections", 510), # Deprecated in v1.1.1
        n_days=imported_params["NumberOfDaysToProject"],
        market_share=float(imported_params["HospitalMarketShare"]),
        relative_contact_rate=float(imported_params["SocialDistancingPercentReduction"]),
        social_distancing_start_date=date.fromisoformat(imported_params["SocialDistancingStartDate"]) if "SocialDistancingStartDate" in imported_params else (date.today() - timedelta(hours=6)).isoformat(),
        hospitalized=Disposition(float(imported_params["HospitalizationPercentage"]), imported_params["HospitalLengthOfStay"]),
        icu=Disposition(float(imported_params["ICUPercentage"]), imported_params["ICULengthOfStay"]),
        ventilators=Disposition(float(imported_params["VentilatorsPercentage"]),imported_params["VentLengthOfStay"]),

        # total_beds=imported_params.get("TotalNumberOfBeds", 10), # Deprecated in v1.1.1
        total_covid_beds=imported_params["TotalNumberOfBedsForNCPatients"],
        # total_icu_beds=imported_params.get("TotalNumberOfICUBeds", 10), # Deprecated in v1.1.1
        icu_covid_beds=imported_params["TotalNumberOfICUBedsForNCPatients"],
        # total_vents=imported_params.get("TotalNumberOfVents", 10), # Deprecated in v1.1.1
        covid_ventilators=imported_params["TotalNumberOfVentsForNCPatients"],

        covid_census_value=imported_params["CurrentlyHospitalizedCovidPatients"],
        covid_census_date = date.fromisoformat(imported_params["CurrentlyHospitalizedCovidPatientsDate"]) if "CurrentlyHospitalizedCovidPatientsDate" in imported_params else (date.today() - timedelta(hours=6)).isoformat(),
        # selected_offset = imported_params.get("SelectedOffsetDays", -1), # Deprecated in v2.0.0
        author=imported_params.get("Author", "Jane Doe"), # Added in v2.0.0
        scenario=imported_params.get("Scenario", "COVID-19 Model"), # Added in v2.0.0
    )
    return parameters


def param_download_widget(st, parameters, max_y_axis_set, max_y_axis):
    if parameters.author == "Jane Doe" or parameters.scenario == "COVID-19 Model":
        st.sidebar.markdown("""
        **Enter a unique author name and scenario name to enable parameter download.**""")
    else:
        filename = "ModelParameters" + "_" + parameters.author + "_" + parameters.scenario + "_" + datetime.now().isoformat() + ".json"
        out_obj = {
            
            "FirstHospitalizedCaseDate": date.today().isoformat() if parameters.date_first_hospitalized == None else parameters.date_first_hospitalized.isoformat(),
            "FirstHospitalizedDateKnown": parameters.first_hospitalized_date_known,
            "SocialDistancingStartDate": parameters.social_distancing_start_date.isoformat(),
            "Author": parameters.author,
            "Scenario": parameters.scenario,
            "NumberOfDaysToProject": parameters.n_days,
            "DoublingTimeBeforeSocialDistancing": parameters.doubling_time,
            "SocialDistancingPercentReduction": parameters.relative_contact_rate,
            "HospitalizationPercentage": parameters.hospitalized.rate,
            "ICUPercentage": parameters.icu.rate,
            "VentilatorsPercentage": parameters.ventilators.rate,
            "HospitalLengthOfStay": parameters.hospitalized.days,
            "ICULengthOfStay": parameters.icu.days,
            "VentLengthOfStay": parameters.ventilators.days,
            "HospitalMarketShare": parameters.market_share,
            "RegionalPopulation": parameters.population,
            "MaxYAxisSet":max_y_axis_set,
            "MaxYAxis":max_y_axis,
            
            "TotalNumberOfBedsForNCPatients": parameters.total_covid_beds,
            "TotalNumberOfICUBedsForNCPatients": parameters.icu_covid_beds,
            "TotalNumberOfVentsForNCPatients": parameters.covid_ventilators,

            "CurrentlyHospitalizedCovidPatients": parameters.covid_census_value,
            "CurrentlyHospitalizedCovidPatientsDate": parameters.covid_census_date.isoformat(),
            # "SelectedOffsetDays": parameters.selected_offset,  # Deprecated in v2.0.0
        }
        out_json = json.dumps(out_obj)
        b64_json = base64.b64encode(out_json.encode()).decode()
        st.sidebar.markdown(
            """<a download="{filename}" href="data:text/plain;base64,{b64_json}" style="padding:.75em;border-radius:10px;background-color:#00aeff;color:white;font-family:sans-serif;text-decoration:none;">Save Scenario</a>"""
            .format(b64_json=b64_json,filename=filename), 
            unsafe_allow_html=True,
        )