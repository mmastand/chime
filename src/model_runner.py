import os
import datetime
from typing import List
import json

import pandas as pd
import numpy as np
import scipy.stats as sps

from rpy2.robjects import r
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

r.source("./src/jason_model.R")

@app.route("/", methods=["POST"])
def listener():
    method = request.args.get("method", None)
    metric = request.args.get("metric", None)
    n_days = request.args.get("n_days", None)
    inf_days = request.args.get("inf_days", None)
    model_input_dict = request.get_json()
    if method is None or metric is None or model_input_dict is None or n_days is None or inf_days is None:
        return "Must supply 'method', 'metric', n_days, inf_days, and 'df'.", 400
    model_input_df = pd.DataFrame(model_input_dict).assign(date=lambda d: pd.to_datetime(d.date))
    out_df = run_model(model_input_df, method, metric, n_days, inf_days)
    if isinstance(out_df, str):
        return out_df, 400
    return jsonify(out_df.to_json(orient="records", date_format='iso'))


def run_model(model_input_df, method, metric, n_days, inf_days):
    with localconverter(ro.default_converter + pandas2ri.converter):
        r_input_df = ro.conversion.py2rpy(model_input_df)
    r_output_df = r(".fncCaseEst")(r_input_df, fcst=method, grw=metric, n_days=int(n_days), infect_dys=int(inf_days))
    with localconverter(ro.default_converter + pandas2ri.converter):
        out_py_df = ro.conversion.rpy2py(r_output_df)
    if isinstance(out_py_df, np.ndarray):
        return out_py_df[0].item()
    return out_py_df
    
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8765)))
