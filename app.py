from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS
from openai import OpenAI
import anthropic
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

# AI Service Configuration
class AIServiceManager:
    def __init__(self):
        self.services = {
            'openai': {
                'api_key': os.getenv("OPENAI_API_KEY"),
                'client': None,
                'create_method': self._create_openai_response
            },
            'claude': {
                'api_key': os.getenv("CLAUDE_API_KEY"),
                'client': None,
                'create_method': self._create_claude_response
            }
        }
        self._initialize_clients()

    def _initialize_clients(self):
        # Initialize OpenAI client
        if self.services['openai']['api_key']:
            self.services['openai']['client'] = OpenAI(
                api_key=self.services['openai']['api_key']
            )
        
        # Initialize Claude client
        if self.services['claude']['api_key']:
            self.services['claude']['client'] = anthropic.Anthropic(
                api_key=self.services['claude']['api_key']
            )

    def _create_openai_response(self, client, messages, stream=True):
        return client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7,
            top_p=0.9,
            stream=stream
        )

    def _create_claude_response(self, client, messages, stream=True):
        # Convert messages to Claude's format
        claude_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            elif msg['role'] in ['user', 'assistant']:
                claude_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Claude doesn't natively support streaming, so we'll simulate it
        response = client.messages.create(
            model="claude-2.1",
            max_tokens=300,
            system=system_prompt,
            messages=claude_messages
        )
        
        # Simulate streaming by yielding character by character
        def stream_claude_response():
            for char in response.content[0].text:
                yield char

        return stream_claude_response()

    def get_ai_response(self, messages, service='openai', stream=True):
        service_config = self.services.get(service)
        
        if not service_config or not service_config['client']:
            raise ValueError(f"No client available for {service}")

        return service_config['create_method'](
            service_config['client'], 
            messages, 
            stream
        )

# Initialize AI Service Manager
ai_service_manager = AIServiceManager()

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
        ai_service = data.get('service', 'openai')  # Default to OpenAI

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

        # Get AI response
        response = ai_service_manager.get_ai_response(
            conversation_history[user_id], 
            service=ai_service
        )

        # Prepare to stream response
        def generate():
            full_response = ""
            
            # Handle different streaming behaviors
            if ai_service == 'claude':
                for char in response:
                    full_response += char
                    yield f"data: {json.dumps({'content': char})}\n\n"
            else:
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

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing your request.",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
