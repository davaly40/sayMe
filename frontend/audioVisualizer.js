class BlobVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.isInitialized = false;
        this.isAnimating = false;
        this.radius = 90;
        this.baseRadius = 90;
        this.state = 0; // 0: idle, 1: speaking, 2: listening, 3: thinking
    }

    async init() {
        this.isInitialized = true;
        this.startVisualization();
    }

    setState(state) {
        this.state = state;
    }

    startVisualization() {
        if (!this.isAnimating) {
            this.isAnimating = true;
            this.animate();
        }
    }

    animate() {
        if (!this.isAnimating) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Centriranje
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;

        // Crtanje glavnog kruga
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, this.radius, 0, Math.PI * 2);
        this.ctx.strokeStyle = '#00ff95';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

        // Animacija ovisno o stanju
        if (this.state === 1) { // speaking
            this.radius = this.baseRadius + Math.sin(Date.now() / 200) * 10;
        } else if (this.state === 2) { // listening
            this.radius = this.baseRadius + Math.sin(Date.now() / 300) * 15;
        } else if (this.state === 3) { // thinking
            this.radius = this.baseRadius + Math.sin(Date.now() / 400) * 5;
        } else { // idle
            this.radius = this.baseRadius;
        }

        requestAnimationFrame(() => this.animate());
    }

    onWordStart(wordLength) {
        // Smanjenje kruga na početku riječi
        this.radius = this.baseRadius * 0.8;
    }

    onSilence() {
        // Vraćanje na normalnu veličinu
        this.radius = this.baseRadius;
    }
}
