from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import logging
import traceback
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes

# Mock response function
def get_ai_response(message):
    responses = [
        "I understand you're feeling stressed. It's normal to experience stress, and recognizing it is the first step towards managing it effectively.",
        "Thank you for sharing. Can you tell me more about what's been on your mind lately?",
        "It sounds like you're going through a challenging time. Remember, your feelings are valid.",
        "Talking about your emotions is a great way to process them. I'm here to listen without judgment.",
        "Every challenge is an opportunity for growth. Let's explore your thoughts together."
    ]
    import random
    return random.choice(responses)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response

    try:
        # Log incoming request details
        logger.debug(f"Received request method: {request.method}")
        logger.debug(f"Received request data: {request.data}")

        # Safely parse JSON
        try:
            request_data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            return jsonify({"error": "Invalid JSON"}), 400

        user_message = request_data.get("message")
        if not user_message:
            logger.error("No message provided")
            return jsonify({"error": "Message is required"}), 400

        # Get AI response (mock for now)
        ai_response = get_ai_response(user_message)
        
        logger.debug(f"Sending response: {ai_response}")
        return jsonify({
            "response": ai_response
        })
    
    except Exception as e:
        # Log the full error traceback
        logger.error(f"Error processing chat request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"An unexpected error occurred: {str(e)}"
        }), 500

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
