from flask import Flask, send_file

app = Flask(__name__)

@app.route("/download-model")
def download_model():
    return send_file("phishing_model.pkl", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
