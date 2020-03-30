import base64
from datetime import (
    datetime, 
    date,
)
import json
import io
from typing import Tuple

from .defaults import (
    Constants, 
    Regions, 
    RateLos,
)


def constants_from_uploaded_file(file: io.StringIO) -> Tuple[Constants, dict]:
    imported_params = json.loads(file.read())
    constants = Constants(
        region=Regions(area=imported_params["RegionalPopulation"]),
        doubling_time=imported_params["DoublingTimeBeforeSocialDistancing"],
        known_infected=imported_params["CurrentlyKnownRegionalInfections"],
        n_days=imported_params["NumberOfDaysToProject"],
        market_share=float(imported_params["HospitalMarketShare"]),
        relative_contact_rate=float(imported_params["SocialDistancingPercentReduction"]),
        hospitalized=RateLos(float(imported_params["HospitalizationPercentage"]), imported_params["HospitalLengthOfStay"]),
        icu=RateLos(float(imported_params["ICUPercentage"]), imported_params["ICULengthOfStay"]),
        ventilators=RateLos(float(imported_params["VentilatorsPercentage"]),imported_params["VentLengthOfStay"]),

        total_beds=imported_params["TotalNumberOfBeds"],
        total_non_covid_beds=imported_params["TotalNumberOfBedsForNCPatients"],
        total_icu_beds=imported_params["TotalNumberOfICUBeds"],
        total_non_covid_icu_beds=imported_params["TotalNumberOfICUBedsForNCPatients"],
        total_vents=imported_params["TotalNumberOfVents"],
        total_non_covid_vents=imported_params["TotalNumberOfVentsForNCPatients"],

        current_hospitalized=imported_params["CurrentlyHospitalizedCovidPatients"],
        census_date = date.fromisoformat(imported_params.get("CurrentlyHospitalizedCovidPatientsDate", date.today().isoformat())),
        selected_offset = imported_params.get("SelectedOffsetDays", -1)
    )
    return constants, imported_params

def param_download_widget(st, parameters, as_date, max_y_axis_set, max_y_axis):
    if parameters.author == "Jane Doe" or parameters.scenario == "COVID Model":
        st.sidebar.markdown("""
        **Enter a unique author name and scenario name to enable parameter download.**""")
    else:
        filename = "ModelParameters" + "_" + parameters.author + "_" + parameters.scenario + "_" + datetime.now().isoformat() + ".json"
        out_obj = {
            "Author": parameters.author,
            "Scenario": parameters.scenario,
            "NumberOfDaysToProject": parameters.n_days,
            "DoublingTimeBeforeSocialDistancing": parameters.doubling_time,
            "SocialDistancingPercentReduction": parameters.relative_contact_rate,
            "HospitalizationPercentage": parameters.hospitalized.rate,
            "ICUPercentage": parameters.icu.rate,
            "VentilatorsPercentage": parameters.ventilators.rate,
            "HospitalLengthOfStay": parameters.hospitalized.length_of_stay,
            "ICULengthOfStay": parameters.icu.length_of_stay,
            "VentLengthOfStay": parameters.ventilators.length_of_stay,
            "HospitalMarketShare": parameters.market_share,
            "RegionalPopulation": parameters.susceptible,
            "CurrentlyKnownRegionalInfections": parameters.known_infected,
            "PresentResultAsDates": as_date,
            "MaxYAxisSet":max_y_axis_set,
            "MaxYAxis":max_y_axis,
            
            "TotalNumberOfBeds": parameters.total_beds,
            "TotalNumberOfBedsForNCPatients": parameters.total_non_covid_beds,
            "TotalNumberOfICUBeds": parameters.total_icu_beds,
            "TotalNumberOfICUBedsForNCPatients": parameters.total_non_covid_icu_beds,
            "TotalNumberOfVents": parameters.total_vents,
            "TotalNumberOfVentsForNCPatients": parameters.total_non_covid_vents,

            "CurrentlyHospitalizedCovidPatients": parameters.current_hospitalized,
            "CurrentlyHospitalizedCovidPatientsDate": parameters.census_date.isoformat(),
            "SelectedOffsetDays": parameters.selected_offset,
        }
        out_json = json.dumps(out_obj)
        b64_json = base64.b64encode(out_json.encode()).decode()
        st.sidebar.markdown(
            """<a download="{filename}" href="data:text/plain;base64,{b64_json}" style="padding:.75em;border-radius:10px;background-color:#00aeff;color:white;font-family:sans-serif;text-decoration:none;">Save Parameters</a>"""
            .format(b64_json=b64_json,filename=filename), 
            unsafe_allow_html=True,
        )
