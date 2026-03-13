from __future__ import annotations

from flask import Flask, request
from lambda_function import lambda_handler

app = Flask(__name__)

@app.route("/sobreviventes", methods=["POST", "GET", "DELETE"])
def invoke_lambda():
    event = request.get_json(silent=True) or {}
    response = lambda_handler(event, {})
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=True)