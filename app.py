import os

from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "ok", "message": "Security Header Scanner - coming soon"}

if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=5000)
