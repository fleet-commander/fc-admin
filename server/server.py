#!/usr/bin/python3
import os
import json
import requests
from flask import Flask, request, send_from_directory, render_template

changes = []

#Profile listing
app = Flask(__name__, template_folder="templates/")
@app.route("/profiles/", methods=["GET"])
def profile_index():
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), "index.json")

@app.route("/profiles/<path:profile_id>", methods=["GET"])
def profiles(profile_id):
  print (os.path.join(os.getcwd(), "profiles"), profile_id)
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), profile_id)

#Add a configuration change to a session
@app.route("/submit_change", methods=["POST"])
def submit_change():
  global changes
  changes.insert(0, json.loads(request.data))
  return "{\"status\": \"ok\"}"

#Static files
@app.route("/js/<path:js>", methods=["GET"])
def js_files(js):
  return send_from_directory(os.path.join(os.getcwd(), "js"), js)

@app.route("/css/<path:js>", methods=["GET"])
def css_files(js):
  return send_from_directory(os.path.join(os.getcwd(), "css"), js)

@app.route("/img/<path:img>", methods=["GEt"])
def img_files(img):
  return send_from_directory(os.path.join(os.getcwd(), "img"), img)

#View methods
@app.route("/", methods=["GET"])
def index():
  return render_template('index.html')

@app.route("/new_profile", methods=["GET"])
def new_profile():
  return render_template('new_profile.html')

#profile builder methods
@app.route("/session_changes", methods=["GET"])
def session_changes():
  global changes
  return json.dumps(changes)

@app.route("/session_start", methods=["GET"])
def session_start():
  req = requests.get("http://localhost:8182/start_session")
  return req.content, req.status_code

@app.route("/session_stop", methods=["GET"])
def session_stop():
  global changes
  changes = []
  req = requests.get("http://localhost:8182/stop_session")
  return req.content, req.status_code

if __name__ == "__main__":
      app.run(port=8181)
