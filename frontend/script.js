let recognition;
let socket;
let visualizer;
const audioCircle = document.getElementById('audioCircle');

function updateState(state) {
    audioCircle.classList.remove('listening', 'speaking', 'thinking');
    const button = document.getElementById('startButton');
    
    if (state === 'listening') {
        button.classList.add('active');
        visualizer.setState(2);
    } else if (state === 'speaking') {
        visualizer.setState(1);
    } else if (state === 'thinking') {
        visualizer.setState(3);
    } else {
        button.classList.remove('active');
        visualizer.setState(0);
    }
    
    if (state) {
        audioCircle.classList.add(state);
    }
}

// Modificirajte appendMessage funkciju da samo logira poruke umjesto da ih prikazuje
function appendMessage(text, isUser = false) {
    console.log(`${isUser ? 'User' : 'SayMe'}: ${text}`);
}

function formatResponse(text) {
    // Uklonimo ovu funkciju koja je mijenjala tekst
    return text;
}

// Add speech recognition initialization
function initializeSpeechRecognition() {
    recognition = new webkitSpeechRecognition();
    recognition.lang = 'hr-HR';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        updateState('listening');
        console.log('Speech recognition started');
    };

    recognition.onend = () => {
        updateState(null);
        console.log('Speech recognition ended');
    };
    
    recognition.onresult = function(event) {
        const command = event.results[0][0].transcript.toLowerCase();
        console.log('Recognized:', command);
        appendMessage(command, true);
        updateState('thinking');
        
        if (socket.readyState === WebSocket.OPEN) {
            socket.send(command);
        } else {
            appendMessage("Nije moguće poslati poruku. Server nije dostupan.", false);
            updateState(null);
        }
    };

    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        updateState(null);
    };
}

async function initializeWebSocket() {
    try {
        // Koristi relativnu putanju za WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            console.log('WebSocket connected successfully');
        };
        
        socket.onmessage = async function(event) {
            const response = formatResponse(event.data);
            appendMessage(response, false);
            await speak(response);
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            appendMessage("Greška u povezivanju. Pokušavam ponovno...", false);
        };

        socket.onclose = function() {
            console.log('WebSocket closed. Attempting to reconnect...');
            setTimeout(initializeWebSocket, 5000); // Povećano na 5 sekundi
        };
    } catch (error) {
        console.error('Error initializing WebSocket:', error);
        setTimeout(initializeWebSocket, 5000);
    }
}

async function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'hr-HR';
    
    // Optimizirani parametri za hrvatski jezik
    utterance.pitch = 1.0;     // Neutralniji pitch
    utterance.rate = 1.0;      // Normalna brzina
    utterance.volume = 1.0;    // Puna glasnoća
    
    // Prilagodba intonacije bez usporavanja
    if (text.includes('?')) {
        utterance.pitch = 1.1;  // Suptilnija promjena za pitanja
    } else if (text.includes('!')) {
        utterance.pitch = 1.15; // Suptilnija promjena za uskličnike
    }

    // Prirodnije pauze
    text = text.replace(/([,.!?])/g, '$1 ');
    utterance.text = text;
    
    try {
        if (!visualizer.isInitialized) {
            await visualizer.init();
        }

        updateState('speaking');
        visualizer.startVisualization();

        return new Promise((resolve) => {
            let wordStart = 0;
            
            utterance.onboundary = (event) => {
                if (event.name === 'word') {
                    const wordLength = event.charIndex - wordStart;
                    wordStart = event.charIndex;
                    
                    // Trigger circle shrink for each word
                    visualizer.onWordStart(wordLength);
                    
                    // Schedule circle growth after estimated word duration
                    setTimeout(() => {
                        visualizer.onSilence();
                    }, wordLength * 50); // Rough estimate of word duration
                }
            };
            
            utterance.onend = () => {
                setTimeout(() => {
                    updateState(null);
                    resolve();
                }, 500);
            };
            
            speechSynthesis.speak(utterance);
        });
    } catch (error) {
        console.error('Error in speak function:', error);
    }
}

// Poboljšano učitavanje glasova
function loadVoices() {
    return new Promise((resolve) => {
        const loadVoicesInterval = setInterval(() => {
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                clearInterval(loadVoicesInterval);
                resolve(voices);
            }
        }, 100);

        // Backup timeout nakon 3 sekunde
        setTimeout(() => {
            clearInterval(loadVoicesInterval);
            resolve(speechSynthesis.getVoices());
        }, 3000);
    });
}

// Update window.onload to handle AudioContext properly
window.onload = async function() {
    if (!('webkitSpeechRecognition' in window)) {
        alert('Vaš preglednik ne podržava prepoznavanje govora.');
        document.getElementById('startButton').disabled = true;
        return;
    }

    // Initialize WebSocket and Speech Recognition first
    initializeWebSocket();
    initializeSpeechRecognition();

    // Wait for user interaction to initialize audio
    document.getElementById('startButton').addEventListener('click', async function() {
        if (!visualizer) {
            // Initialize visualizer on first click
            visualizer = new BlobVisualizer('visualizer');
            await visualizer.init();
            visualizer.startVisualization();
        }
        
        if (recognition && socket.readyState === WebSocket.OPEN) {
            recognition.start();
        } else if (socket.readyState !== WebSocket.OPEN) {
            appendMessage("Nije uspostavljena veza sa serverom. Molimo pričekajte...", false);
        }
    });

    // Load voices
    await loadVoices();
};
