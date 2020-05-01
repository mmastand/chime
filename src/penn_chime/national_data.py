import os

import streamlit as st
import pandas as pd

FILEPATH = "./data/county_data.csv"

def get_national_data():
    file_reference = FileReference(FILEPATH)
    return fetch_county_data(file_reference)

class FileReference:
    def __init__(self, filename):
        self.filename = filename

def hash_file_reference(file_reference):
    filename = file_reference.filename
    return (filename, os.path.getmtime(filename))

@st.cache(hash_funcs={FileReference: hash_file_reference})
def fetch_county_data(file_reference):
    """The name of this function is displayed to the user when there is a cache miss."""
    path = file_reference.filename
    return (pd
            .read_csv(path)
            .assign(date = lambda d: pd.to_datetime(d.date))
    )