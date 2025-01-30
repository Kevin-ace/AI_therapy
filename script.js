document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const responseElement = document.getElementById('response');

    // Generate a unique user ID
    const getUserId = () => {
        if (!localStorage.getItem('user_id')) {
            localStorage.setItem('user_id', 'user_' + Math.random().toString(36).substr(2, 9));
        }
        return localStorage.getItem('user_id');
    };

    // Typing animation for AI responses
    function typeResponse(text, element) {
        element.innerHTML = '';
        let index = 0;
        const typingInterval = setInterval(() => {
            if (index < text.length) {
                element.innerHTML += text.charAt(index);
                index++;
            } else {
                clearInterval(typingInterval);
            }
        }, 20);
    }

    // Disable send button during processing
    function setButtonState(disabled) {
        sendButton.disabled = disabled;
        sendButton.style.opacity = disabled ? '0.5' : '1';
    }

    async function sendMessage() {
        const message = userInput.value.trim();

        // Input validation
        if (!message) {
            responseElement.innerHTML = '<p class="error">Please share your thoughts before sending.</p>';
            return;
        }

        // Clear previous response and prepare for new message
        responseElement.innerHTML = '';
        setButtonState(true);

        try {
            const response = await fetch('http://localhost:5000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify({ 
                    message: message,
                    user_id: getUserId()
                })
            });

            // Check if the response is successful
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            // Create a reader for streaming
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            // Stream the response
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value);
                const events = chunk.split('\n\n');
                
                events.forEach(event => {
                    if (event.startsWith('data: ')) {
                        try {
                            const parsedEvent = JSON.parse(event.replace('data: ', ''));
                            if (parsedEvent.content) {
                                fullResponse += parsedEvent.content;
                                responseElement.innerHTML += parsedEvent.content;
                            }
                        } catch (e) {
                            console.error('Error parsing event:', e);
                        }
                    }
                });
            }

            userInput.value = ''; // Clear input after sending
        } catch (error) {
            console.error('Error:', error);
            responseElement.innerHTML = `<p class="error">Oops! ${error.message}. Please try again.</p>`;
        } finally {
            setButtonState(false);
        }
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Initial welcome message
    typeResponse("Hello, I'm Aria. I'm here to listen and support you. How are you feeling today?", responseElement);
});