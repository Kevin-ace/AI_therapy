from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Print environment variable for debugging
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))

# Explicitly check for API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in .env file.")

# Use environment variable for API key
client = OpenAI(api_key=api_key)

app = Flask(__name__)

# OpenAI API Key

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # GPT API call
    response = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a kind and empathetic therapist. Help users feel heard and understood."},
        {"role": "user", "content": user_message},
    ])

    reply = response.choices[0].message.content
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)
