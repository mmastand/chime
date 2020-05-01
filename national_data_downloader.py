import io
import time
import traceback

import requests
import pandas as pd

SLACK_URL = "https://hooks.slack.com/services/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"
DATA_URL = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv"
COUNTY_DATA_FILEPATH = "./data/county_data.csv"

def fetch_data():
    response=requests.get(DATA_URL)
    try:
        response.raise_for_status()
    except:
        message = f"Error retrieving data from github: {traceback.format_exc()}"
        payload = {'text': message}
        requests.post(SLACK_URL, json=payload)
    try:
        county_df_raw = pd.read_csv(io.StringIO(response.content.decode('utf-8')))

        NEW_YORK_CITY_DUMMY_FIPS = 9999
        NEW_YORK_CITY_2019_POPULATION = 8399000
        RHODE_ISLAND_DUMMY_FIPS = 9998
        RHODE_ISLAND_2019_POPULATION = 1059000

        county_df = county_df_raw.copy()
        # Assign dummy FIPS
        county_df.loc[county_df.state == "Rhode Island", "fips"] = RHODE_ISLAND_DUMMY_FIPS
        county_df.loc[county_df.county == "New York City", "fips"] = NEW_YORK_CITY_DUMMY_FIPS
        # drop rows that don't have a FIPS value
        # these are all the rows where the county is "Unknown" except for Rhode Island and New York City
        county_df = (county_df[['date', 'county', 'state', 'fips', 'cases']]
                    .dropna(subset=["fips"])
                    .assign(
                        date = lambda d: pd.to_datetime(d.date),
                        fips = lambda d: d.fips.astype('int'),
                    )
                    )
        # Combine Rhode Island counties into single county
        rh_agg_df = (county_df
                    .loc[county_df.state == "Rhode Island"]
                    .groupby("date")
                    .agg({
                        'county': lambda d: 'Rhode Island',
                        'state': lambda d: 'Rhode Island',
                        'fips': 'max',
                        'cases': 'sum',
                    })
                    .reset_index()
                    )
        # Remove old Rhode Island rows and append the new aggregated rows
        old_rh_rows = county_df.loc[county_df.state == "Rhode Island"]
        county_df = (county_df
                    .drop(old_rh_rows.index)
                    .append(rh_agg_df)
                    )

        # Add Populations from Jason's Script
        pop_df_raw = pd.read_csv("./data/county_populations.csv")
        pop_df = (pop_df_raw
            .dropna()
            .assign(fips=lambda d: d.fips.astype('int'))
            [['fips', 'pop_est2019']]
        )
        county_df = county_df.merge(pop_df, on="fips", how="left")
        # Fill in the populations of New York City and Rhode Island since they are not in the county-level population data.
        county_df.loc[county_df.county == "New York City", 'pop_est2019'] = NEW_YORK_CITY_2019_POPULATION
        county_df.loc[county_df.county == "Rhode Island", 'pop_est2019'] = RHODE_ISLAND_2019_POPULATION
        county_df.to_csv(COUNTY_DATA_FILEPATH, index=False)
    except:
        message = f"Error processing github data: {traceback.format_exc()}"
        payload = {'text': message}
        requests.post(SLACK_URL, json=payload)

def main():
    one_hour = 60 * 60
    while True:
        fetch_data()
        time.sleep(one_hour)

if __name__ == "__main__":
    main()