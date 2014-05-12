import os
import json
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
  print(request.data)
  changes.insert(0, json.loads(request.data))
  return "{\"status\": \"ok\"}"

#Static files
@app.route("/js/<path:js>", methods=["GET"])
def js_files(js):
  return send_from_directory(os.path.join(os.getcwd(), "js"), js)

@app.route("/css/<path:js>", methods=["GET"])
def css_files(js):
  return send_from_directory(os.path.join(os.getcwd(), "css"), js)

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
  return json.dumps(changes)

if __name__ == "__main__":
      app.run(port=8181)
