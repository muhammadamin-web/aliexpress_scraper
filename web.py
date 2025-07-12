from flask import Flask, request, jsonify, send_file, render_template
import os
import threading
from scraper import run_scraper, LOG_FILE

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/scrap", methods=["POST"])
def scrap():
    data = request.json
    ids = data.get("ids", "").strip()

    # Eski fayllarni o‘chirish
    for f in ["aliexpress_products.csv", "reviews.csv", LOG_FILE]:
        if os.path.exists(f):
            os.remove(f)

    # Scraper'ni fon (thread) orqali ishga tushurish
    thread = threading.Thread(target=run_scraper, args=(ids,))
    thread.start()

    return jsonify({"message": "Scraping boshlandi"})

@app.route("/log")
def get_log():
    if not os.path.exists(LOG_FILE):
        return ""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()

@app.route("/download/<filename>")
def download_file(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "Fayl topilmadi", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # <-- Render yoki boshqa hosting portini oladi
    app.run(host="0.0.0.0", port=port)        # <-- Tashqi ulanishlar uchun ochiq
