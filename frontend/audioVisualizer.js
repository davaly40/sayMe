class BlobVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.shrink = 1;
        this.radius = 50;
        this.state = 0; // 0: idle, 1: speaking, 2: listening, 3: thinking
        this.particles = [];
        this.lastTime = 0;
        this.isActive = false;
    }

    async init() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            // Initialize particles
            for (let i = 0; i < 12; i++) {
                this.particles.push({
                    angle: (i / 12) * Math.PI * 2,
                    radius: this.radius,
                    velocity: 0,
                    amplitude: 1
                });
            }
            
            return true;
        } catch (error) {
            console.error('Audio context initialization failed:', error);
            return false;
        }
    }

    setState(newState) {
        this.state = newState;
    }

    stopAllAudio() {
        if (this.audioContext) {
            this.analyser.disconnect();
        }
    }

    startVisualization() {
        this.isActive = true;
        this.animate();
    }

    stopVisualization() {
        this.isActive = false;
    }

    animate(currentTime = 0) {
        if (!this.isActive) return;

        const deltaTime = (currentTime - this.lastTime) / 1000;
        this.lastTime = currentTime;

        // Get audio data
        if (this.state === 1 && this.analyser) { // Only when speaking
            this.analyser.getByteFrequencyData(this.dataArray);
            // Normalize the data
            const average = Array.from(this.dataArray).reduce((a, b) => a + b, 0) / this.dataArray.length;
            this.radius = 50 + (average * 0.5); // Base radius + audio intensity
        }

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.save();
        this.ctx.translate(this.canvas.width / 2, this.canvas.height / 2);

        // Draw equalizer circles
        if (this.state === 1 && this.dataArray) {
            this.drawEqualizer();
        }

        // Draw base circle and particles
        this.ctx.beginPath();
        this.ctx.arc(0, 0, this.radius * this.shrink, 0, Math.PI * 2);
        this.ctx.fillStyle = 'rgba(0, 255, 149, 0.1)';
        this.ctx.fill();

        this.updateParticles(deltaTime);
        this.drawParticles();

        this.ctx.restore();
        requestAnimationFrame(this.animate.bind(this));
    }

    drawEqualizer() {
        const bands = 32; // Number of frequency bands to display
        const step = Math.floor(this.dataArray.length / bands);
        
        for (let i = 0; i < bands; i++) {
            const frequency = this.dataArray[i * step];
            const normalized = frequency / 256.0; // Normalize to 0-1
            const length = normalized * 50; // Max length of equalizer bars
            
            const angle = (i / bands) * Math.PI * 2;
            const x1 = Math.cos(angle) * (this.radius - 20);
            const y1 = Math.sin(angle) * (this.radius - 20);
            const x2 = Math.cos(angle) * (this.radius - 20 + length);
            const y2 = Math.sin(angle) * (this.radius - 20 + length);
            
            this.ctx.beginPath();
            this.ctx.moveTo(x1, y1);
            this.ctx.lineTo(x2, y2);
            this.ctx.strokeStyle = `rgba(0, 255, 149, ${normalized * 0.8})`;
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
        }
    }

    updateParticles(deltaTime) {
        const targetAmplitude = this.state === 1 ? 1.5 : 
                              this.state === 2 ? 1.2 :
                              this.state === 3 ? 1.3 : 1;

        this.particles.forEach((particle, i) => {
            // Oscillation frequency varies by state
            const frequency = this.state === 1 ? 2 : 
                            this.state === 2 ? 3 :
                            this.state === 3 ? 1.5 : 0.5;

            particle.amplitude += (targetAmplitude - particle.amplitude) * deltaTime * 2;
            particle.radius = this.radius * (1 + 
                Math.sin(Date.now() * 0.003 + i * 0.5) * 0.2 * particle.amplitude);

            if (this.state === 1) { // Speaking
                particle.angle += deltaTime * 0.5;
            } else if (this.state === 2) { // Listening
                particle.angle += deltaTime * 0.3;
            } else if (this.state === 3) { // Thinking
                particle.angle += Math.sin(Date.now() * 0.001 + i) * deltaTime * 0.5;
            }
        });
    }

    drawParticles() {
        this.ctx.beginPath();
        this.particles.forEach((particle, i) => {
            const x = Math.cos(particle.angle) * particle.radius;
            const y = Math.sin(particle.angle) * particle.radius;
            
            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        this.ctx.closePath();
        
        // Create gradient
        const gradient = this.ctx.createRadialGradient(0, 0, this.radius * 0.5, 0, 0, this.radius * 2);
        gradient.addColorStop(0, 'rgba(0, 255, 149, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 255, 149, 0.1)');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fill();
        
        // Add glow effect
        this.ctx.strokeStyle = 'rgba(0, 255, 149, 0.5)';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }

    triggerWord(intensity) {
        this.shrink = 0.8 + (intensity * 0.001);
        setTimeout(() => {
            this.shrink = 1;
        }, 100);
    }
}
