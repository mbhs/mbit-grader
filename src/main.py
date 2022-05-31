from flask import Flask, request
import os
import tempfile
from jail import *
import json

secret = os.environ.get("SECRET", "secret")


def run_pretests(lang, prog, opts, prob):
    with tempfile.NamedTemporaryFile() as f:
        p = prep_jail(lang, prog, opts, f)
        files = os.listdir(f"/cases/p_{prob}")
        if "check" in files:
            verifier = f"/cases/p_{prob}/check"
        else:
            verifier = None
        inps = [
            f"/cases/p_{prob}/{x}"
            for x in files
            if x.endswith(".in") and x.startswith("p")
        ]
        inps.sort()
        outs = [x.replace(".in", ".out") for x in inps]
        return [
            run_one_test(lang, f.name, opts, i, o, verifier)
            if p["type"] != "error"
            else p
            for (i, o) in zip(inps, outs)
        ]


def run_tests(lang, prog, opts, prob):
    with tempfile.NamedTemporaryFile() as f:
        p = prep_jail(lang, prog, opts, f)
        files = os.listdir(f"/cases/p_{prob}")
        if "check" in files:
            verifier = f"/cases/p_{prob}/check"
        else:
            verifier = None
        inps = [
            f"/cases/p_{prob}/{x}"
            for x in files
            if x.endswith(".in") and x.startswith("t")
        ]
        inps.sort()
        outs = [x.replace(".in", ".out") for x in inps]
        return [
            run_one_test(lang, f.name, opts, i, o, verifier)
            if p["type"] != "error"
            else p
            for (i, o) in zip(inps, outs)
        ]


app = Flask(__name__)


@app.post("/pretest")
def pretest_route():
    b = request.get_json()
    if b["secret"] != secret:
        return json.dumps({"type": "error", "msg": "invalid secret"})
    return json.dumps(run_pretests(b["lang"], b["prog"].encode(), b["opts"], b["prob"]))


@app.post("/test")
def test_route():
    b = request.get_json()
    if b["secret"] != secret:
        return json.dumps({"type": "error", "msg": "invalid secret"})
    return json.dumps(run_tests(b["lang"], b["prog"].encode(), b["opts"], b["prob"]))


@app.get("/")
def homepage():
    return "Grader is up!"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
