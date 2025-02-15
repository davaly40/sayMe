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

// Modificirajte appendMessage funkciju da samo logira poruke umjesto da ih prikazuje
function appendMessage(text, isUser = false) {
    console.log(`${isUser ? 'User' : 'SayMe'}: ${text}`);
}

function formatResponse(text) {
    // Uklonimo ovu funkciju koja je mijenjala tekst
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
            
            if (socket && socket.readyState === WebSocket.OPEN) {
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
        // Koristi relativnu putanju za WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            console.log('WebSocket connected successfully');
        };
        
        socket.onmessage = async function(event) {
            try {
                // Pokušaj parsirati kao JSON
                const data = JSON.parse(event.data);
                if (data.type === 'openUrl') {
                    handleUrlOpen(data);
                    appendMessage(data.message, false);
                    return;
                }
            } catch (e) {
                // Ako nije JSON, tretiraj kao običan tekst
                appendMessage(event.data, false);
            }
            const response = formatResponse(event.data);
            appendMessage(response, false);
            await speak(response);
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

function handleUrlOpen(data) {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile && data.mobileUrl) {
        // Pokušaj otvoriti mobilnu aplikaciju
        window.location.href = data.mobileUrl;
        
        // Ako mobilna aplikacija nije instalirana, otvori web verziju nakon 1 sekunde
        setTimeout(() => {
            window.open(data.url, '_blank');
        }, 1000);
    } else {
        // Na desktopu ili ako nema mobilne aplikacije, otvori u novom tabu
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

async function handleCameraRequest(isFrontCamera = false, withTimer = false) {
    try {
        const constraints = {
            video: {
                facingMode: isFrontCamera ? "user" : "environment"
            }
        };
        
        // Prvo zatvori postojeći stream ako postoji
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
        }

        // Stvori novi video element
        let video = document.createElement('video');
        video.style.position = 'fixed';
        video.style.top = '0';
        video.style.left = '0';
        video.style.width = '100%';
        video.style.height = '100%';
        video.style.objectFit = 'cover';
        video.style.zIndex = '1000';
        document.body.appendChild(video);

        // Dobavi stream kamere
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        cameraStream = stream;
        video.srcObject = stream;
        await video.play();

        if (withTimer) {
            // Dodaj timer overlay
            let timerDiv = document.createElement('div');
            timerDiv.style.position = 'fixed';
            timerDiv.style.top = '50%';
            timerDiv.style.left = '50%';
            timerDiv.style.transform = 'translate(-50%, -50%)';
            timerDiv.style.fontSize = '72px';
            timerDiv.style.color = 'white';
            timerDiv.style.zIndex = '1001';
            document.body.appendChild(timerDiv);

            // Timer countdown
            for (let i = 5; i > 0; i--) {
                timerDiv.textContent = i;
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            // Slikaj
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            
            // Spremi sliku
            const photo = canvas.toDataURL('image/jpeg');
            const link = document.createElement('a');
            link.download = 'selfie.jpg';
            link.href = photo;
            link.click();

            // Čišćenje
            timerDiv.remove();
        }

        // Dodaj gumb za zatvaranje
        const closeButton = document.createElement('button');
        closeButton.textContent = '✕';
        closeButton.style.position = 'fixed';
        closeButton.style.top = '20px';
        closeButton.style.right = '20px';
        closeButton.style.zIndex = '1001';
        closeButton.style.backgroundColor = 'rgba(0,0,0,0.5)';
        closeButton.style.color = 'white';
        closeButton.style.border = 'none';
        closeButton.style.borderRadius = '50%';
        closeButton.style.width = '40px';
        closeButton.style.height = '40px';
        closeButton.style.cursor = 'pointer';
        
        closeButton.onclick = () => {
            video.remove();
            closeButton.remove();
            stream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        };
        
        document.body.appendChild(closeButton);

    } catch (error) {
        console.error('Camera error:', error);
        alert('Greška pri pristupu kameri. Molimo dozvolite pristup kameri.');
    }
}

async function handleAlarmRequest(text) {
    try {
        // Izvuci vrijeme iz teksta
        const timeMatch = text.match(/(\d{1,2})(?::\d{2})?\s*(ujutro|navečer|navecer|popodne|predvečer|predvecer|noću|nocu|h)?/);
        if (!timeMatch) {
            throw new Error('Nije pronađeno vrijeme u zahtjevu');
        }

        let hours = parseInt(timeMatch[1]);
        const period = timeMatch[2];

        // Prilagodi sate prema periodu dana
        if (period) {
            if (period === 'popodne' || period === 'predvečer' || period === 'predvecer') {
                if (hours < 12) hours += 12;
            } else if ((period === 'navečer' || period === 'navecer' || period === 'noću' || period === 'nocu') && hours < 12) {
                hours += 12;
            } else if (period === 'ujutro' && hours === 12) {
                hours = 0;
            }
        }

        // Provjeri podržava li uređaj alarm API
        if ('wakeLock' in navigator || 'setAlarm' in navigator) {
            // Za moderne uređaje
            const timestamp = new Date();
            timestamp.setHours(hours, 0, 0, 0);
            
            if (timestamp < new Date()) {
                timestamp.setDate(timestamp.getDate() + 1);
            }

            // Pokušaj postaviti alarm
            if ('setAlarm' in navigator) {
                await navigator.setAlarm(timestamp.getTime());
            } else {
                // Fallback na notifications
                const notification = await requestNotificationPermission();
                if (notification) {
                    scheduleNotification(timestamp);
                }
            }
            
            return `Alarm postavljen za ${hours}:00h`;
        } else {
            // Fallback na sistemski kalendar
            const calendarUrl = createCalendarEvent(hours);
            window.open(calendarUrl, '_blank');
            return `Otvoreno je sučelje za postavljanje alarma za ${hours}:00h`;
        }
    } catch (error) {
        console.error('Alarm error:', error);
        return 'Nisam uspio postaviti alarm. Pokušajte ručno postaviti alarm na vašem uređaju.';
    }
}

async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        return false;
    }
    
    const permission = await Notification.requestPermission();
    return permission === 'granted';
}

function scheduleNotification(timestamp) {
    const now = new Date().getTime();
    const delay = timestamp.getTime() - now;
    
    setTimeout(() => {
        new Notification('Alarm', {
            body: 'Vrijeme je za buđenje!',
            icon: '/assets/logo.png'
        });
    }, delay);
}

function createCalendarEvent(hours) {
    const date = new Date();
    date.setHours(hours, 0, 0, 0);
    if (date < new Date()) {
        date.setDate(date.getDate() + 1);
    }
    
    const dateString = date.toISOString().replace(/[-:]/g, '').split('.')[0];
    return `data:text/calendar;charset=utf8,BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nDTSTART:${dateString}\nDURATION:PT10M\nSUMMARY:Alarm\nEND:VEVENT\nEND:VCALENDAR`;
}

// Modificiraj postojeći handleCommand da uključi nove komande
async function handleCommand(text) {
    // ...existing code...
    
    if (/^(upali kameru|kamera|fotoaparat)$/i.test(text)) {
        await handleCameraRequest();
        return "Kamera je upaljena";
    } else if (/^(zabilježi ovaj trenutak|selfi)$/i.test(text)) {
        await handleCameraRequest(true, true);
        return "Pripremam selfi s timerom...";
    } else if (/^(probudi me|navij alarm|namjesti budilicu)/i.test(text)) {
        return await handleAlarmRequest(text);
    }
    
    // ...existing code...
}

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

async function openCamera(mode) {
    try {
        const constraints = {
            video: {
                facingMode: mode === 'front' ? 'user' : 'environment'
            }
        };
        
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        const video = document.createElement('video');
        video.srcObject = stream;
        video.autoplay = true;
        video.style.position = 'fixed';
        video.style.top = '0';
        video.style.left = '0';
        video.style.width = '100%';
        video.style.height = '100%';
        video.style.zIndex = '1000';
        
        document.body.appendChild(video);
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.position = 'fixed';
        closeBtn.style.top = '20px';
        closeBtn.style.right = '20px';
        closeBtn.style.zIndex = '1001';
        closeBtn.onclick = () => {
            stream.getTracks().forEach(track => track.stop());
            video.remove();
            closeBtn.remove();
        };
        document.body.appendChild(closeBtn);
        
    } catch (err) {
        speak("Nažalost, ne mogu pristupiti kameri. Molim vas provjerite dozvole.");
    }
}

function setAlarm(hours, minutes) {
    // Check if the browser supports notifications
    if (!("Notification" in window)) {
        speak("Vaš preglednik ne podržava alarme.");
        return;
    }

    // Request notification permission
    Notification.requestPermission().then(function(permission) {
        if (permission === "granted") {
            const now = new Date();
            const alarmTime = new Date();
            alarmTime.setHours(hours);
            alarmTime.setMinutes(minutes);
            alarmTime.setSeconds(0);
            
            // If the time is in the past, set it for tomorrow
            if (alarmTime < now) {
                alarmTime.setDate(alarmTime.getDate() + 1);
            }
            
            const timeUntilAlarm = alarmTime - now;
            
            setTimeout(() => {
                new Notification("SayMe Alarm", {
                    body: `Vrijeme je ${hours}:${minutes.toString().padStart(2, '0')}!`,
                    icon: "/assets/logo.png"
                });
                
                // Also play a sound
                const audio = new Audio('/assets/alarm.mp3');
                audio.play();
            }, timeUntilAlarm);
            
            speak(`Alarm je postavljen za ${hours}:${minutes.toString().padStart(2, '0')}`);
        }
    });
}

// ...rest of the existing code...

function updateVisualization(state) {
    const circle = document.querySelector('.audio-circle');
    if (!circle) return;

    // Reset states
    circle.classList.remove('speaking', 'thinking', 'listening');
    
    if (state) {
        circle.classList.add(state);
        
        if (state === 'speaking') {
            animateVoiceDots();
        }
    }
}

function animateVoiceDots() {
    const dots = document.querySelectorAll('.voice-dots span');
    dots.forEach((dot, i) => {
        dot.style.animationDelay = `${i * 0.1}s`;
    });
}

function initializeVisualization() {
    const dots = document.querySelectorAll('.voice-dots span');
    dots.forEach((dot, i) => {
        dot.style.setProperty('--rotation', `${i * 45}deg`);
        dot.style.transform = `rotate(${i * 45}deg) translateY(-45px)`;
    });
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
