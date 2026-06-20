from flask import Flask, request
import requests
import os
import logging
from google import genai

# إعداد الـ logging عشان نشوف أي خطأ بوضوح في Render Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3-flash"


def get_ai_response(text):
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=f"أنت مساعد ذكي لحساب ماستر سلايد على إنستغرام. رد باختصار وبشكل ودي على: {text}"
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "شكراً على تواصلك معنا! سنرد عليك قريباً 😊"


@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "خطأ", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logger.info(f"Incoming webhook payload: {data}")

    for entry in data.get("entry", []):
        for msg in entry.get("messaging", []):
            sender_id = msg["sender"]["id"]
            if "message" in msg and "text" in msg["message"]:
                text = msg["message"]["text"]
                logger.info(f"DM from {sender_id}: {text}")
                reply = get_ai_response(text)
                logger.info(f"AI reply: {reply}")
                send_dm(sender_id, reply)

        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") == "comments":
                comment_id = value.get("id")
                comment_text = value.get("text", "")
                logger.info(f"Comment {comment_id}: {comment_text}")
                reply = get_ai_response(comment_text)
                reply_comment(comment_id, reply)

    return "OK", 200


IG_ID = os.environ.get("IG_ID")  # Instagram Business Account ID: 17841480087963888


def send_dm(recipient_id, message):
    url = f"https://graph.instagram.com/v25.0/{IG_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    resp = requests.post(url, headers=headers, json=payload)
    logger.info(f"send_dm status={resp.status_code} body={resp.text}")


def reply_comment(comment_id, message):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/replies"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    payload = {
        "message": message
    }
    resp = requests.post(url, headers=headers, data=payload)
    logger.info(f"reply_comment status={resp.status_code} body={resp.text}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
