import io

import rpy2.robjects as ro
from rpy2.robjects import r
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
import pandas as pd
import streamlit as st


def do_r_stuff():
    return r("2 + 2")[0]

@st.cache(allow_output_mutation=True)
def get_county_data():
    # r("require(covdata)")
    # r_df = r("covdata::nytcovcounty")
    # with localconverter(ro.default_converter + pandas2ri.converter):
    #     out_df = ro.conversion.rpy2py(r_df)
    # return out_df

    return pd.read_csv("./src/nytcovcounty.csv")

    # data_string = io.StringIO(county_data)
    # return pd.read_csv(data_string)


