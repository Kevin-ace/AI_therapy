document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    function addMessage(content, sender) {
        console.log(`Adding ${sender} message:`, content);
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        messageElement.textContent = content;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            // Add user message
            addMessage(message, 'user');

            // Send message to backend
            console.log('Sending message to server:', message);
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ message: message })
            })
            .then(response => {
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);
                
                if (!response.ok) {
                    return response.text().then(text => {
                        console.error('Error response body:', text);
                        throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Received data:', data);
                // Add AI response
                if (data.response) {
                    addMessage(data.response, 'ai');
                } else if (data.error) {
                    addMessage(data.error, 'ai');
                } else {
                    addMessage('Unexpected response format', 'ai');
                }
            })
            .catch(error => {
                console.error('Full error details:', error);
                addMessage(`Error: ${error.message}`, 'ai');
            });

            // Clear input
            userInput.value = '';
        }
    }

    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);

    // Send message on Enter key press
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Initial welcome message
    addMessage('Hello! I am your AI Therapist. How are you feeling today?', 'ai');
});