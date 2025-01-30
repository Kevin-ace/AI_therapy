from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS
from openai import OpenAI
import os
import logging
import json
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('ai_therapist.log'),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API Key Fallback Mechanism
API_KEYS = [
    os.getenv("OPENAI_API_KEY"),  # Primary OpenAI API key
    os.getenv("GITHUB_TOKEN"),    # GitHub token from .env
]

# Remove None values and strip whitespace
API_KEYS = [key.strip() for key in API_KEYS if key]

class APIKeyRotator:
    def __init__(self, keys):
        self.keys = keys
        self.current_key_index = 0
        self.failed_keys = set()

    def get_next_key(self):
        if not self.keys:
            raise ValueError("No API keys available")

        # If all keys have failed, reset
        if len(self.failed_keys) == len(self.keys):
            self.failed_keys.clear()

        # Rotate through available keys
        while True:
            key = self.keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            
            if key not in self.failed_keys:
                return key

    def mark_key_as_failed(self, key):
        self.failed_keys.add(key)

# Initialize API key rotator
api_key_rotator = APIKeyRotator(API_KEYS)

# Conversation history storage (in-memory, replace with database in production)
conversation_history = {}

# Comprehensive system prompt for therapeutic interaction
SYSTEM_PROMPT = """
You are Aria, an empathetic AI therapist. Your primary goals are:
1. Listen actively and validate the user's feelings
2. Ask open-ended, reflective questions
3. Provide gentle, constructive guidance
4. Maintain professional boundaries
5. Never provide medical advice or diagnose conditions
6. If a user seems in crisis, suggest seeking professional help

Respond with deep empathy, understanding, and focus on emotional well-being.
"""

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Validate input
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400

        user_id = data.get('user_id', 'default_user')
        user_message = data['message'].strip()

        # Initialize or retrieve conversation history
        if user_id not in conversation_history:
            conversation_history[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

        # Add user message to conversation history
        conversation_history[user_id].append({
            "role": "user", 
            "content": user_message
        })

        # Limit conversation history to prevent excessive token usage
        if len(conversation_history[user_id]) > 10:
            conversation_history[user_id] = conversation_history[user_id][-10:]

        # Try with multiple API keys
        max_retries = len(API_KEYS)
        for attempt in range(max_retries):
            try:
                # Get next available API key
                current_api_key = api_key_rotator.get_next_key()
                
                # Initialize client with current key
                client = OpenAI(api_key=current_api_key)

                # OpenAI API call
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history[user_id],
                    max_tokens=300,
                    temperature=0.7,
                    top_p=0.9,
                    stream=True
                )

                # Prepare to stream response
                def generate():
                    full_response = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    
                    # Add AI response to conversation history
                    conversation_history[user_id].append({
                        "role": "assistant", 
                        "content": full_response
                    })

                return Response(generate(), mimetype='text/event-stream')

            except Exception as api_error:
                logger.error(f"API Error with key: {current_api_key}. Error: {str(api_error)}")
                
                # Mark the current key as failed
                api_key_rotator.mark_key_as_failed(current_api_key)
                
                # If it's the last attempt, raise the error
                if attempt == max_retries - 1:
                    raise

                # Wait a bit before retrying
                time.sleep(1)

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            "error": "All API keys have been exhausted. Please try again later.",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
