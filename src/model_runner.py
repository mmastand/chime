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
    model_input_dict = request.get_json()
    if method is None or metric is None or model_input_dict is None:
        return "Must supply 'method', 'metric', and 'df'.", 400
    model_input_df = pd.DataFrame(model_input_dict).assign(date=lambda d: pd.to_datetime(d.date))
    out_df = run_model(model_input_df, method, metric)
    return jsonify(out_df.to_json(orient="records", date_format='iso'))


def run_model(model_input_df, method, metric):
    with localconverter(ro.default_converter + pandas2ri.converter):
        r_input_df = ro.conversion.py2rpy(model_input_df)
    r.print(r.str(r_input_df))
    r_output_df = r(".fncCaseEst")(r_input_df, fcst=method, grw=metric)
    with localconverter(ro.default_converter + pandas2ri.converter):
        out_py_df = ro.conversion.rpy2py(r_output_df)
    return out_py_df
    
if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8086)))