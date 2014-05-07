import os
from flask import Flask, request, send_from_directory

session = []

app = Flask(__name__)
@app.route("/profiles/", methods=["GET"])
def profile_index():
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), "index.json")

@app.route("/profiles/<path:profile_id>", methods=["GET"])
def profiles(profile_id):
  print (os.path.join(os.getcwd(), "profiles"), profile_id)
  return send_from_directory(os.path.join(os.getcwd(), "profiles"), profile_id)

@app.route("/submit_change", methods=["POST"])
def hello():
  print(request.data)
  session.append(data)
  return "{\"status\": \"ok\"}"

if __name__ == "__main__":
      app.run(port=8181)
