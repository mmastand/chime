import numpy as np
import pandas as pd

from penn_chime.models import build_census_df


def test_build_census_df():
    lengths_of_stay = {
        'hospitalized': 7,
        'icu': 8,
        'ventilated': 9,
    }
    admits_df = pd.DataFrame({                                        # Daily admissions for each category.
        'hospitalized': np.concatenate([np.ones(10),     [0, 0, 0]]), # [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
        'icu':          np.concatenate([np.ones(10) * 2, [0, 0, 0]]), # [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0]
        'ventilated':   np.concatenate([np.ones(10) * 5, [0, 0, 0]]), # [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 0, 0, 0]
    })

    census_df = build_census_df(admits_df, lengths_of_stay)

    # Expected Census
    expected_hospitalized = pd.Series([1, 2, 3, 4, 5, 6, 7, 7, 7, 7, 6, 5, 4])
    expected_icu          = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 7, 6, 5]) * 2
    expected_ventilators  = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 8, 7, 6]) * 5

    assert census_df['hospitalized'].astype(int).equals(expected_hospitalized)
    assert census_df['icu'].astype(int).equals(expected_icu)
    assert census_df['ventilated'].astype(int).equals(expected_ventilators)
