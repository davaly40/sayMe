let recognition;
let socket;
const audioCircle = document.getElementById('audioCircle');

function updateState(state) {
    updateVisualization(state);
    audioCircle.classList.remove('listening', 'speaking', 'thinking');
    const button = document.getElementById('startButton');
    
    if (state === 'listening') {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }
    
    if (state) {
        audioCircle.classList.add(state);
    }
}

function appendMessage(text, isUser = false) {
    console.log(`${isUser ? 'User' : 'SayMe'}: ${text}`);
}

function formatResponse(text) {
    return text;
}

// Add speech recognition initialization
async function initializeSpeechRecognition() {
    window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    try {
        // Prvo pokušaj dobiti dozvolu za mikrofon
        await navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                // Odmah zaustavi stream da spriječimo feedback
                stream.getTracks().forEach(track => track.stop());
            })
            .catch(err => {
                console.error('Microphone permission error:', err);
                alert('Molimo dozvolite pristup mikrofonu za korištenje aplikacije.');
                return;
            });

        recognition = new window.SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.lang = 'hr-HR';

        // Zaustavi prethodno prepoznavanje ako postoji
        recognition.onstart = () => {
            updateState('listening');
            console.log('Speech recognition started');
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'not-allowed') {
                alert('Molimo dozvolite pristup mikrofonu i osvježite stranicu.');
            } else if (event.error === 'network') {
                alert('Provjerite internetsku vezu.');
                setTimeout(() => {
                    recognition.stop();
                    recognition.start();
                }, 1000);
            } else if (event.error === 'no-speech') {
                console.log('No speech detected');
                // Tiho ponovno pokretanje na Samsung uređajima
                if (isSamsung) {
                    setTimeout(() => {
                        try {
                            recognition.start();
                        } catch (e) {
                            console.error('Restart error:', e);
                        }
                    }, 100);
                }
            } else {
                alert('Greška u prepoznavanju govora. Pokušajte ponovno.');
            }
            updateState(null);
        };

        // Posebno rukovanje za Samsung uređaje
        recognition.onend = () => {
            updateState(null);
            if (isSamsung && recognition.isListening) {
                try {
                    recognition.start();
                } catch (e) {
                    console.error('Restart error:', e);
                }
            }
        };

        recognition.onresult = async function(event) {
            const command = event.results[0][0].transcript.toLowerCase();
            console.log('Recognized:', command);
            
            // Dodaj vizualnu povratnu informaciju
            const button = document.getElementById('startButton');
            button.style.background = 'rgba(255, 255, 255, 0.2)';
            setTimeout(() => button.style.background = '', 200);
            
            appendMessage(command, true);
            updateState('thinking');
            
            // Provjeri je li vremenska prognoza
            if (command.match(/kakvo.*(vrijeme|prognoza|temperatura)/i)) {
                await handleWeatherRequest(command);
            } else if (socket && socket.readyState === WebSocket.OPEN) {
                try {
                    await socket.send(command);
                } catch (err) {
                    console.error('WebSocket send error:', err);
                    alert('Greška u komunikaciji. Molimo osvježite stranicu.');
                }
            } else {
                appendMessage("Nije moguće poslati poruku. Server nije dostupan.", false);
                updateState(null);
            }
        };

    } catch (error) {
        console.error('Recognition init error:', error);
        alert('Greška pri inicijalizaciji. Molimo osvježite stranicu.');
    }
}

// Dodaj novu funkciju za provjeru kompatibilnosti
function checkDeviceCompatibility() {
    const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    const isAndroid = /Android/.test(navigator.userAgent);
    const isSamsung = /Samsung/i.test(navigator.userAgent);
    
    if (isAndroid) {
        if (!isChrome) {
            alert('Za najbolje iskustvo, koristite Chrome browser na Android uređaju.');
        }
        if (isSamsung) {
            // Samsung uređaji često imaju problema s WebView-om
            console.log('Samsung device detected, using fallback mode');
        }
    }
    
    // Provjeri WebView verziju na Android uređajima
    const match = navigator.userAgent.match(/Chrome\/([0-9]+)/);
    if (match) {
        const version = parseInt(match[1]);
        if (version < 85) { // Minimalna verzija za pouzdano prepoznavanje govora
            alert('Ažurirajte Chrome browser ili Android System WebView za korištenje ove aplikacije.');
        }
    }
}

async function initializeWebSocket() {
    try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            console.log('WebSocket connected successfully');
        };
        
        socket.onmessage = async function(event) {
            try {
                // Prvo pokušaj parsirati kao JSON
                const data = JSON.parse(event.data);
                if (data.type === "openUrl") {
                    handleUrlOpen(data);
                    appendMessage(data.message, false);
                    await speak(data.message);
                    return;
                }
            } catch (e) {
                // Ako nije JSON, tretiraj kao običan tekst
                const response = formatResponse(event.data);
                appendMessage(response, false);
                await speak(response);
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            appendMessage("Greška u povezivanju. Pokušavam ponovno...", false);
        };

        socket.onclose = function() {
            console.log('WebSocket closed, attempting reconnect...');
            setTimeout(async () => {
                try {
                    await initializeWebSocket();
                } catch (e) {
                    console.error('Reconnect failed:', e);
                }
            }, 3000);
        };
    } catch (error) {
        console.error('Error initializing WebSocket:', error);
        setTimeout(initializeWebSocket, 5000);
    }
}

async function tryOpenApp(urls) {
    // Napravi nevidljivi iframe za pokušaj otvaranja aplikacije
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);

    for (const url of urls) {
        try {
            // Pokušaj otvoriti aplikaciju
            iframe.src = url;
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Ako smo došli do ovdje, vjerojatno je aplikacija otvorena
            return true;
        } catch (e) {
            console.log('Failed to open app:', e);
        }
    }
    
    // Ukloni iframe
    document.body.removeChild(iframe);
    return false;
}

function handleUrlOpen(data) {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile && data.mobileUrls) {
        // Ako su dostupni mobilni URL-ovi (za navigaciju)
        const urls = Object.values(data.mobileUrls);
        
        // Pokušaj otvoriti dostupne navigacijske aplikacije
        tryOpenApp(urls).then(success => {
            if (!success) {
                // Ako nije uspjelo otvaranje aplikacija, otvori web verziju
                window.location.href = data.url;
            }
        });
    } else if (isMobile && data.mobileUrl) {
        // Za ostale mobilne aplikacije (postojeća logika)
        window.location.href = data.mobileUrl;
        
        setTimeout(() => {
            window.location.href = data.url;
        }, 1000);
    } else {
        // Na desktopu otvori u novom tabu
        window.open(data.url, '_blank');
    }
}

async function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'hr-HR';
    
    try {
        if (recognition) {
            recognition.stop();
        }

        updateState('speaking');
        updateVisualization('speaking');

        await new Promise((resolve) => {
            utterance.onend = () => {
                setTimeout(() => {
                    updateState(null);
                    updateVisualization(null);
                    resolve();
                }, 500);
            };
            
            speechSynthesis.speak(utterance);
        });

    } catch (error) {
        console.error('Speak error:', error);
        updateState(null);
        updateVisualization(null);
    }
}

// Add this helper function to create audio stream from speech synthesis
async function createSpeechStream(utterance) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    utterance.onstart = () => {
        oscillator.start();
    };
    
    utterance.onend = () => {
        oscillator.stop();
    };
    
    utterance.onboundary = (event) => {
        // Modulate gain based on word boundaries
        gainNode.gain.setValueAtTime(0.8, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.2, audioContext.currentTime + 0.1);
    };
    
    const stream = audioContext.createMediaStreamDestination();
    gainNode.connect(stream);
    return stream.stream;
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

// Dodaj novu funkciju za provjeru i pripremu uređaja
async function prepareDevice() {
    const isSamsung = /Samsung|SM-/i.test(navigator.userAgent);
    const androidVersion = parseInt((navigator.userAgent.match(/Android ([0-9]+)/) || [])[1] || '0');
    
    if (isSamsung) {
        // Provjeri verziju Android System WebView
        try {
            const webviewInfo = await checkWebViewVersion();
            if (webviewInfo.needsUpdate) {
                alert('Molimo ažurirajte Android System WebView putem Google Play trgovine za bolje funkcioniranje aplikacije.');
            }
        } catch (e) {
            console.error('WebView check failed:', e);
        }
        
        // Posebne preporuke za Samsung uređaje
        if (androidVersion >= 12) {
            console.log('Modern Samsung device detected');
            // Dodatne optimizacije za novije uređaje
        } else {
            alert('Za najbolje iskustvo, preporučujemo korištenje Chrome preglednika na vašem Samsung uređaju.');
        }
    }
}

// Dodaj funkciju za provjeru WebView verzije
async function checkWebViewVersion() {
    const webviewVersion = (navigator.userAgent.match(/Chrome\/([0-9]+)/) || [])[1] || '0';
    return {
        version: parseInt(webviewVersion),
        needsUpdate: parseInt(webviewVersion) < 95
    };
}

// Update window.onload to handle AudioContext properly
window.onload = async function() {
    await prepareDevice();
    checkDeviceCompatibility();
    
    initializeWebSocket();
    initializeSpeechRecognition();
    
    document.getElementById('startButton').addEventListener('click', async function() {
        if (recognition && socket.readyState === WebSocket.OPEN) {
            recognition.start();
        } else if (socket.readyState !== WebSocket.OPEN) {
            appendMessage("Nije uspostavljena veza sa serverom. Molimo pričekajte...", false);
        }
    });

    await loadVoices();
    
    // Initialize visualization
    const audioCircle = document.querySelector('.audio-circle');
    if (audioCircle) {
        const visualizer = audioCircle.querySelector('.visualizer-container');
        if (visualizer) {
            visualizer.style.display = 'flex';
        }
    }
};

function initializeModals() {
    const shareButton = document.getElementById('shareButton');
    const shareModal = document.getElementById('shareModal');
    const helpButton = document.getElementById('helpButton');
    const helpModal = document.getElementById('helpModal');
    const copyButton = document.getElementById('copyButton');
    const shareLinkInput = document.getElementById('shareLink');

    if (!shareButton || !shareModal || !helpButton || !helpModal) {
        console.error('Modal elements not found');
        return;
    }

    // Postavi trenutnu URL adresu
    if (shareLinkInput) {
        shareLinkInput.value = window.location.href;
    }

    // Generiraj QR kod
    const qrCodeElement = document.getElementById('qrCode');
    if (qrCodeElement) {
        new QRCode(qrCodeElement, {
            text: window.location.href,
            width: 200,
            height: 200,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
    }

    // Event listeneri za modale
    shareButton.addEventListener('click', function(e) {
        e.stopPropagation();
        console.log('Share button clicked'); // Debug log
        helpModal.classList.remove('active');
        shareModal.classList.toggle('active');
    });

    helpButton.addEventListener('click', function(e) {
        e.stopPropagation();
        console.log('Help button clicked'); // Debug log
        shareModal.classList.remove('active');
        helpModal.classList.toggle('active');
    });

    // Kopiraj link
    if (copyButton) {
        copyButton.addEventListener('click', async function() {
            try {
                await navigator.clipboard.writeText(shareLinkInput.value);
                copyButton.textContent = 'Kopirano!';
                setTimeout(() => copyButton.textContent = 'Kopiraj', 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        });
    }

    // Zatvori modale klikom izvan
    document.addEventListener('click', function(e) {
        if (!shareButton.contains(e.target) && 
            !shareModal.contains(e.target) && 
            !helpButton.contains(e.target) && 
            !helpModal.contains(e.target)) {
            shareModal.classList.remove('active');
            helpModal.classList.remove('active');
        }
    });

    // Zatvori modale na ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            shareModal.classList.remove('active');
            helpModal.classList.remove('active');
        }
    });
}

// Dodajmo inicijalizaciju modala u DOMContentLoaded event
document.addEventListener('DOMContentLoaded', function() {
    initializeModals();
    // ...rest of your DOMContentLoaded code...
});

// ...existing code...

function handleServerResponse(response) {
    try {
        const data = JSON.parse(response);
        
        switch(data.type) {
            case "openCamera":
                openCamera(data.mode);
                break;
            case "setAlarm":
                setAlarm(data.hours, data.minutes);
                break;
            default:
                // Handle regular text response
                speak(data.message || response);
        }
    } catch (e) {
        // Not JSON, handle as regular text response
        speak(response);
    }
}

// ...rest of the existing code...

function updateVisualization(state) {
    const circle = document.querySelector('.audio-circle');
    if (!circle) return;

    // Reset all states
    circle.classList.remove('speaking', 'thinking', 'listening');
    
    if (state) {
        circle.classList.add(state);
    }
}

// Add to window.onload
window.addEventListener('load', () => {
    initializeVisualization();
});

function createSpectrumBars() {
    const container = document.querySelector('.spectrum-bars');
    const barCount = 32;
    const radius = 100;
    
    for (let i = 0; i < barCount; i++) {
        const bar = document.createElement('div');
        const angle = (i / barCount) * Math.PI * 2;
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        
        bar.className = 'spectrum-bar';
        bar.style.cssText = `
            position: absolute;
            left: 50%;
            top: 50%;
            width: 2px;
            height: 20px;
            background: var(--accent);
            transform: translate(-50%, -50%) rotate(${angle}rad) translateY(${radius}px);
            transform-origin: center ${-radius}px;
            opacity: 0.3;
        `;
        
        container.appendChild(bar);
    }
}

// Initialize spectrum bars on load
window.addEventListener('load', () => {
    createSpectrumBars();
});

// ...existing code...

async function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject('Geolokacija nije podržana');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                });
            },
            (error) => {
                reject(error.message);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }
        );
    });
}

async function handleWeatherRequest(command) {
    try {
        // Pokušaj dobiti lokaciju samo ako nije specificiran grad
        if (!command.match(/\b(u|za)\s+[a-zčćđšž]+/i)) {
            try {
                const location = await getCurrentLocation();
                // Promijenjeno formatiranje - dodajemo "coords:" prefix
                command = `${command} coords:${location.lat},${location.lon}`;
            } catch (error) {
                console.log('Nije moguće dobiti lokaciju:', error);
            }
        }
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            await socket.send(command);
        }
    } catch (error) {
        console.error('Error handling weather request:', error);
    }
}

// Modificiraj postojeći recognition.onresult handler
recognition.onresult = async function(event) {
    const command = event.results[0][0].transcript.toLowerCase();
    console.log('Recognized:', command);
    
    // Dodaj vizualnu povratnu informaciju
    const button = document.getElementById('startButton');
    button.style.background = 'rgba(255, 255, 255, 0.2)';
    setTimeout(() => button.style.background = '', 200);
    
    appendMessage(command, true);
    updateState('thinking');
    
    // Provjeri je li vremenska prognoza
    if (command.match(/kakvo.*(vrijeme|prognoza|temperatura)/i)) {
        await handleWeatherRequest(command);
    } else if (socket && socket.readyState === WebSocket.OPEN) {
        try {
            await socket.send(command);
        } catch (err) {
            console.error('WebSocket send error:', err);
            alert('Greška u komunikaciji. Molimo osvježite stranicu.');
        }
    } else {
        appendMessage("Nije moguće poslati poruku. Server nije dostupan.", false);
        updateState(null);
    }
};

// ...existing code...

async function handleMusicChoice(data) {
    // Prikaži opcije korisniku i čekaj odgovor
    appendMessage(data.message, false);
    
    // Nastavi slušati korisnikov govor za odabir
    if (recognition) {
        recognition.start();
    }
}

// Modificiraj postojeći socket.onmessage handler
socket.onmessage = async function(event) {
    try {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case "openUrl":
                handleUrlOpen(data);
                appendMessage(data.message, false);
                break;
            case "musicChoice":
                handleMusicChoice(data);
                appendMessage(data.message, false);
                break;
            default:
                const response = formatResponse(data.message || event.data);
                appendMessage(response, false);
                await speak(response);
        }
    } catch (e) {
        const response = formatResponse(event.data);
        appendMessage(response, false);
        await speak(response);
    }
};

// Modificiraj handleUrlOpen funkciju da bolje rukuje glazbenim aplikacijama
async function handleUrlOpen(data) {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile && data.mobileUrl) {
        // Pokušaj otvoriti nativnu aplikaciju
        try {
            // Prvo pokušaj otvoriti u aplikaciji
            window.location.href = data.mobileUrl;
            
            // Ako nakon 1 sekunde još uvijek nismo preusmjereni, 
            // vjerojatno aplikacija nije instalirana
            setTimeout(() => {
                if (document.hasFocus()) {
                    window.location.href = data.url;
                }
            }, 1000);
        } catch (e) {
            // Ako ne uspije, otvori web verziju
            window.location.href = data.url;
        }
    } else {
        // Na desktopu otvori u novom tabu
        window.open(data.url, '_blank');
    }
}

// ...rest of the existing code...
