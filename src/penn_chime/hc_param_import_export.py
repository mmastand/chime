import base64
from datetime import (
    datetime, 
    date,
    timedelta,
)
import json
import io
from typing import Tuple

import streamlit as st

from .parameters import (
    Disposition,
    ForecastMethod,
    ForecastedMetric,
    Mode,
    Parameters, 
    Regions, 
)

def constants_from_uploaded_file(file: io.StringIO) -> Tuple[Parameters, dict]:
    imported_params = json.loads(file.read())
    if "SocialDistancingStartDate" in imported_params:
        if imported_params["SocialDistancingStartDate"] is None:
            mitigation_date = None
        else:
            # value is ISO date
            mitigation_date = date.fromisoformat(imported_params["SocialDistancingStartDate"])
    else:
        mitigation_date = (date.today() - timedelta(hours=6))
      
    parameters = Parameters(
        population=imported_params["RegionalPopulation"],
        doubling_time=float(imported_params["DoublingTimeBeforeSocialDistancing"]) if "DoublingTimeBeforeSocialDistancing" in imported_params else 5.0,
        infectious_days=imported_params.get("InfectiousDays", 10),
        date_first_hospitalized=date.fromisoformat(imported_params["FirstHospitalizedCaseDate"]) if "FirstHospitalizedCaseDate" in imported_params else None,
        first_hospitalized_date_known=imported_params.get("FirstHospitalizedDateKnown", False), # Added in v2.0.0
        # known_infected=imported_params.get("CurrentlyKnownRegionalInfections", 510), # Deprecated in v1.1.1
        n_days=imported_params["NumberOfDaysToProject"],
        market_share=float(imported_params["HospitalMarketShare"]),
        relative_contact_rate=float(imported_params["SocialDistancingPercentReduction"]),
        mitigation_date=mitigation_date,
        social_distancing_is_implemented=imported_params["SocialDistancingIsImplemented"] if "SocialDistancingIsImplemented" in imported_params else True,
        non_icu=Disposition(float(imported_params["HospitalizationPercentage"]), imported_params["HospitalLengthOfStay"]),
        icu=Disposition(float(imported_params["ICUPercentage"]), imported_params["ICULengthOfStay"]),
        ventilators=Disposition(float(imported_params["VentilatorsPercentage"]),imported_params["VentLengthOfStay"]),

        beds_borrow=imported_params.get("BedBorrowing", True),
        # total_beds=imported_params.get("TotalNumberOfBeds", 10), # Deprecated in v1.1.1
        total_covid_beds=imported_params["TotalNumberOfBedsForNCPatients"],
        # total_icu_beds=imported_params.get("TotalNumberOfICUBeds", 10), # Deprecated in v1.1.1
        icu_covid_beds=imported_params["TotalNumberOfICUBedsForNCPatients"],
        # total_vents=imported_params.get("TotalNumberOfVents", 10), # Deprecated in v1.1.1
        covid_ventilators=imported_params["TotalNumberOfVentsForNCPatients"],
        
        max_y_axis_set = imported_params["MaxYAxisSet"],
        max_y_axis = imported_params["MaxYAxis"],

        covid_census_value=imported_params["CurrentlyHospitalizedCovidPatients"],
        covid_census_date = date.fromisoformat(imported_params["CurrentlyHospitalizedCovidPatientsDate"]) if "CurrentlyHospitalizedCovidPatientsDate" in imported_params else (date.today() - timedelta(hours=6)).isoformat(),
        # selected_offset = imported_params.get("SelectedOffsetDays", -1), # Deprecated in v2.0.0
        author=imported_params.get("Author", "Jane Doe"), # Added in v2.0.0
        scenario=imported_params.get("Scenario", "COVID-19 Model"), # Added in v2.0.0

        # App mode
        app_mode=imported_params.get("AppMode", Mode.PENN_MODEL),

        # Model Settings
        forecast_method=imported_params.get("ForecastMethod", ForecastMethod.ETS),
        forecasted_metric=imported_params.get("ForecastedMetric", ForecastedMetric.DOUBLING_TIME),

        # County Selections
        selected_states = imported_params.get("SelectedStates", []),
        selected_counties = imported_params.get("SelectedCounties", []),

        # PPE Params
        masks_n95=imported_params.get("MasksN95", 5),
        masks_surgical=imported_params.get("MasksSurgical", 7),
        face_shield=imported_params.get("FaceShields", 5),
        gloves=imported_params.get("Gloves", 10),
        gowns=imported_params.get("Gowns", 10),
        other_ppe=imported_params.get("OtherPPE", 2),
        masks_n95_icu=imported_params.get("MasksN95ICU", 5),
        masks_surgical_icu=imported_params.get("MasksSurgicalICU", 7),
        face_shield_icu=imported_params.get("FaceShieldsICU", 5),
        gloves_icu=imported_params.get("GlovesICU", 10),
        gowns_icu=imported_params.get("GownsICU", 10),
        other_ppe_icu=imported_params.get("OtherPPEICU", 2),

        # Staffing Params
        # Non-ICU
        nurses=imported_params.get("PatientsPerNurse", 6),
        physicians=imported_params.get("PatientsPerPhysicians", 20),
        advanced_practice_providers=imported_params.get("PatientsPerAdvancedPraticeProviders", 20),
        healthcare_assistants=imported_params.get("PatientsPerHealthcareAssistants", 10),
        other_staff=imported_params.get("PatientsPerOtherStaff", 10),
        # ICU
        nurses_icu=imported_params.get("PatientsPerNurseICU", 2),
        physicians_icu=imported_params.get("PatientsPerPhysiciansICU", 12),
        advanced_practice_providers_icu=imported_params.get("PatientsPerAdvancedPraticeProvidersICU", 12),
        healthcare_assistants_icu=imported_params.get("PatientsPerHealthcareAssistantsICU", 10),
        other_staff_icu=imported_params.get("PatientsPerOtherStaffICU", 10),
        # Shift Duration
        shift_duration=imported_params.get("ShiftDuration", 12),

        # Population
        override_population=imported_params.get("OverridePopulation", False),
        population_manual_override=imported_params.get("PopulationManualOverride", None),

        # Section Display
        show_forecast_methods=imported_params.get("ShowForecastMethods", False),
        show_ppe_section=imported_params.get("ShowPPESection", False),
        show_staffing_section=imported_params.get("ShowStaffingSection", False),
    )
    return parameters


def param_download_widget(parameters):
    filename = "ModelParameters" + "_" + parameters.author + "_" + parameters.scenario + "_" + datetime.now().isoformat() + ".json"
    out_obj = {
        
        "FirstHospitalizedCaseDate": date.today().isoformat() if parameters.date_first_hospitalized == None else parameters.date_first_hospitalized.isoformat(),
        "FirstHospitalizedDateKnown": parameters.first_hospitalized_date_known,
        "SocialDistancingStartDate": parameters.mitigation_date.isoformat() if parameters.mitigation_date is not None else parameters.mitigation_date,
        "SocialDistancingIsImplemented": parameters.social_distancing_is_implemented,
        "Author": parameters.author,
        "Scenario": parameters.scenario,
        "NumberOfDaysToProject": parameters.n_days,
        "DoublingTimeBeforeSocialDistancing": 4.0 if parameters.doubling_time == None else parameters.doubling_time,
        "InfectiousDays": parameters.infectious_days,
        "SocialDistancingPercentReduction": parameters.relative_contact_rate,
        "HospitalizationPercentage": parameters.non_icu.rate,
        "ICUPercentage": parameters.icu.rate,
        "VentilatorsPercentage": parameters.ventilators.rate,
        "HospitalLengthOfStay": parameters.non_icu.days,
        "ICULengthOfStay": parameters.icu.days,
        "VentLengthOfStay": parameters.ventilators.days,
        "HospitalMarketShare": parameters.market_share,
        "RegionalPopulation": parameters.population,
        "MaxYAxisSet":parameters.max_y_axis_set,
        "MaxYAxis":parameters.max_y_axis,
        
        "BedBorrowing": parameters.beds_borrow,
        "TotalNumberOfBedsForNCPatients": parameters.total_covid_beds,
        "TotalNumberOfICUBedsForNCPatients": parameters.icu_covid_beds,
        "TotalNumberOfVentsForNCPatients": parameters.covid_ventilators,

        "CurrentlyHospitalizedCovidPatients": parameters.covid_census_value,
        "CurrentlyHospitalizedCovidPatientsDate": parameters.covid_census_date.isoformat(),
        # "SelectedOffsetDays": parameters.selected_offset,  # Deprecated in v2.0.0
        
        # App Mode
        "AppMode": parameters.app_mode,

        # Model Setting
        "ForecastMethod": parameters.forecast_method,
        "ForecastedMetric": parameters.forecasted_metric,

        # County Selections
        "SelectedStates": parameters.selected_states,
        "SelectedCounties": parameters.selected_counties,

        # PPE Params
        "MasksN95": parameters.masks_n95,
        "MasksSurgical": parameters.masks_surgical,
        "FaceShields": parameters.face_shield,
        "Gloves": parameters.gloves,
        "Gowns": parameters.gowns,
        "OtherPPE": parameters.other_ppe,
        "MasksN95ICU": parameters.masks_n95_icu,
        "MasksSurgicalICU": parameters.masks_surgical_icu,
        "FaceShieldsICU": parameters.face_shield_icu,
        "GlovesICU": parameters.gloves_icu,
        "GownsICU": parameters.gowns_icu,
        "OtherPPEICU": parameters.other_ppe_icu,

        # Staffing Params
        # Non-ICU
        "PatientsPerNurse" : parameters.nurses,
        "PatientsPerPhysicians" : parameters.physicians,
        "PatientsPerAdvancedPraticeProviders" : parameters.advanced_practice_providers,
        "PatientsPerHealthcareAssistants": parameters.healthcare_assistants,
        "PatientsPerOtherStaff": parameters.other_staff,
        # ICU
        "PatientsPerNurseICU" : parameters.nurses_icu,
        "PatientsPerPhysiciansICU" : parameters.physicians_icu,
        "PatientsPerAdvancedPraticeProvidersICU" : parameters.advanced_practice_providers_icu,
        "PatientsPerHealthcareAssistantsICU": parameters.healthcare_assistants_icu,
        "PatientsPerOtherStaffICU": parameters.other_staff_icu,
        # Shift Duration
        "ShiftDuration" : parameters.shift_duration,

        # Population
        "OverridePopulation": parameters.override_population,
        "PopulationManualOverride": parameters.population_manual_override,

        # Section Display
        "ShowForecastMethods": parameters.show_forecast_methods,
        "ShowPPESection": parameters.show_ppe_section,
        "ShowStaffingSection": parameters.show_staffing_section,
    }
    out_json = json.dumps(out_obj)
    b64_json = base64.b64encode(out_json.encode()).decode()
    st.sidebar.markdown(
        """<a download="{filename}" href="data:text/plain;base64,{b64_json}" style="padding:.75em;border-radius:10px;background-color:#00aeff;color:white;font-family:sans-serif;text-decoration:none;">Save Scenario</a>"""
        .format(b64_json=b64_json,filename=filename), 
        unsafe_allow_html=True,
    )
