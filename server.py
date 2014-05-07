import os
from flask import Flask, request, send_from_directory, render_template

session = []



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
  session.append(data)
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

if __name__ == "__main__":
      app.run(port=8181)
