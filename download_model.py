from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route("/")
def index():
    files = os.listdir(".")
    return f"""
    <h2>Файл модели:</h2>
    <ul>
        {''.join(f'<li>{f}</li>' for f in files)}
    </ul>
    <p>Скачать модель: <a href="/download-model">phishing_model.pkl</a></p>
    """

@app.route("/download-model", methods=["GET"])
def download_model():
    file_path = "phishing_model.pkl"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return f"Ошибка: файл '{file_path}' не найден на сервере.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
