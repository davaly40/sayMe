class BlobVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.gl = this.canvas.getContext('webgl');
        if (!this.gl) {
            console.error('WebGL nije podržan');
            return;
        }
        this.isInitialized = false;
        this.shrink = 1.0; // 1 = full size, lower values mean smaller circle
        this.targetSize = 1.0;  // Target size for smooth animation
        this.currentSize = 1.0; // Current size of circle
        this.recoverySpeed = 0.02; // Speed at which circle grows back
        this.shrinkSpeed = 0.1;    // Speed at which circle shrinks
        this.rings = []; // Track active rings
        this.lastRingTime = 0;
        this.ringInterval = 300; // ms between ring spawns
        this.isActive = true; // Always animate, even when idle
        this.waves = [];  // Array to store active wave rings
        this.lastSize = 1.0;  // Track last frame's size
        this.sizeChangeThreshold = 0.01;  // Minimum size change to spawn wave
        this.maxWaves = 15;  // Maximum number of concurrent waves
        this.particles = []; // Za lebdeće čestice
        this.maxParticles = 20;
        this.glowIntensity = 0.0; // Za dinamički glow efekt
        this.audioInitialized = false;
        this.lastAudioLevel = 0;
        this.animationSpeed = 0.01;
        this.baseRadius = 0.6;
        this.currentRadius = this.baseRadius;
        this.targetRadius = this.baseRadius;
    }

    async init() {
        if (this.isInitialized) return;
        
        try {
            // Initialize WebGL first
            this.setupShaders();
            this.setupBuffers();
            this.resize();
            
            // Then initialize audio context
            await this.initAudioContext();
            if (this.analyser) {
                this.analyser.minDecibels = -90;
                this.analyser.maxDecibels = -10;
                this.analyser.smoothingTimeConstant = 0.85;
            }
            
            this.isInitialized = true;
            console.log('Visualizer initialized successfully');
        } catch (error) {
            console.error('Error initializing visualizer:', error);
            throw error;
        }
    }

    async initAudioContext() {
        try {
            if (this.audioContext) {
                await this.audioContext.close();
            }
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.7;
            this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
            
            // Ukloni oscilator
            this.gainNode = this.audioContext.createGain();
            this.gainNode.gain.value = 0.0; // Potpuno utišano
            
            this.gainNode.connect(this.analyser);
            this.audioInitialized = true;
        } catch (error) {
            console.error('Audio initialization error:', error);
        }
    }

    stopAllAudio() {
        if (this.audioContext) {
            this.gainNode.gain.value = 0;
            if (this.oscillator) {
                this.oscillator.stop();
                this.oscillator.disconnect();
            }
        }
    }

    setupShaders() {
        const vertexShader = this.gl.createShader(this.gl.VERTEX_SHADER);
        this.gl.shaderSource(vertexShader, `
            attribute vec2 position;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
            }
        `);
        this.gl.compileShader(vertexShader);

        const fragmentShader = this.gl.createShader(this.gl.FRAGMENT_SHADER);
        this.gl.shaderSource(fragmentShader, `
            precision highp float;
            uniform float time;
            uniform float circleSize;
            uniform float audioLevel;
            
            const vec3 COLOR1 = vec3(0.0, 1.0, 0.584);  // Primary green
            const vec3 COLOR2 = vec3(0.0, 0.8, 1.0);    // Accent blue
            const float PI = 3.14159265359;

            // Utility functions
            vec3 mod289(vec3 x) {
                return x - floor(x * (1.0 / 289.0)) * 289.0;
            }

            vec2 mod289(vec2 x) {
                return x - floor(x * (1.0 / 289.0)) * 289.0;
            }

            vec3 permute(vec3 x) {
                return mod289(((x*34.0)+1.0)*x);
            }

            // Simplified 3D noise
            float snoise(vec2 v) {
                const vec4 C = vec4(0.211324865405187,
                                  0.366025403784439,
                                 -0.577350269189626,
                                  0.024390243902439);
                
                vec2 i  = floor(v + dot(v, C.yy));
                vec2 x0 = v -   i + dot(i, C.xx);
                vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
                vec4 x12 = x0.xyxy + C.xxzz;
                x12.xy -= i1;
                
                i = mod289(i);
                vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                    + i.x + vec3(0.0, i1.x, 1.0));
                
                vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
                m = m*m;
                m = m*m;
                
                vec3 x = 2.0 * fract(p * C.www) - 1.0;
                vec3 h = abs(x) - 0.5;
                vec3 ox = floor(x + 0.5);
                vec3 a0 = x - ox;
                
                m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
                
                vec3 g;
                g.x  = a0.x  * x0.x  + h.x  * x0.y;
                g.yz = a0.yz * x12.xz + h.yz * x12.yw;
                return 130.0 * dot(m, g);
            }
            
            void main() {
                vec2 uv = (gl_FragCoord.xy / vec2(300.0)) * 2.0 - 1.0;
                float dist = length(uv);
                
                // Dynamic circle with noise distortion
                float noiseTime = time * 0.5;
                float noiseValue = snoise(uv + noiseTime) * 0.1 * audioLevel;
                
                // Base circle radius with audio reactivity
                float radius = 0.6 * circleSize;
                radius += audioLevel * 0.2 * sin(dist * 8.0 - time * 2.0);
                radius += noiseValue;
                
                // Smooth circle edge
                float circle = smoothstep(radius + 0.02, radius - 0.02, dist);
                
                // Energy waves
                float energy = 0.0;
                for(int i = 0; i < 3; i++) {
                    float angle = time * (0.5 + float(i) * 0.2) + float(i) * PI * 2.0 / 3.0;
                    vec2 dir = vec2(cos(angle), sin(angle));
                    float pulse = sin(dot(uv, dir) * 10.0 - time * 3.0) * 0.5 + 0.5;
                    energy += pulse * smoothstep(radius + 0.1, radius - 0.1, dist) * audioLevel;
                }
                
                // Ripple effect
                float ripple = sin(dist * 20.0 - time * 5.0) * audioLevel * 0.1;
                
                // Combine effects
                float alpha = circle + energy * 0.3 + ripple;
                
                // Color variation
                vec3 finalColor = mix(COLOR1, COLOR2, energy + noiseValue);
                
                // Add glow
                float glow = exp(-dist * 3.0) * (0.3 + audioLevel * 0.3);
                finalColor += glow * COLOR1;
                
                gl_FragColor = vec4(finalColor, alpha);
            }
        `);
        this.gl.compileShader(fragmentShader);

        this.program = this.gl.createProgram();
        this.gl.attachShader(this.program, vertexShader);
        this.gl.attachShader(this.program, fragmentShader);
        this.gl.linkProgram(this.program);
        this.gl.useProgram(this.program);

        // Add blend mode for glow effect
        this.gl.enable(this.gl.BLEND);
        this.gl.blendFunc(this.gl.SRC_ALPHA, this.gl.ONE_MINUS_SRC_ALPHA);

        // Add shader compilation check
        const vertStatus = this.gl.getShaderParameter(vertexShader, this.gl.COMPILE_STATUS);
        const fragStatus = this.gl.getShaderParameter(fragmentShader, this.gl.COMPILE_STATUS);
        
        if (!vertStatus) {
            throw new Error(this.gl.getShaderInfoLog(vertexShader));
        }
        if (!fragStatus) {
            throw new Error(this.gl.getShaderInfoLog(fragmentShader));
        }

        // Check program linking
        if (!this.gl.getProgramParameter(this.program, this.gl.LINK_STATUS)) {
            throw new Error(this.gl.getProgramInfoLog(this.program));
        }

        // Add state uniform location
        this.stateLocation = this.gl.getUniformLocation(this.program, 'state');
        this.gl.uniform1i(this.stateLocation, 0); // Default to idle state
        this.shrinkLocation = this.gl.getUniformLocation(this.program, 'shrink');  // New uniform location
        this.circleSizeLocation = this.gl.getUniformLocation(this.program, 'circleSize'); // Add size uniform location
        this.ringsLocation = this.gl.getUniformLocation(this.program, 'rings');
        this.activeRingsLocation = this.gl.getUniformLocation(this.program, 'activeRings');
        this.wavesLocation = this.gl.getUniformLocation(this.program, 'waves');
        this.activeWavesLocation = this.gl.getUniformLocation(this.program, 'activeWaves');
        this.glowIntensityLocation = this.gl.getUniformLocation(this.program, 'glowIntensity');
        this.audioLevelLocation = this.gl.getUniformLocation(this.program, 'audioLevel');
    }

    setupBuffers() {
        const vertices = new Float32Array([
            -1, -1,
            1, -1,
            -1, 1,
            1, 1
        ]);
        
        const buffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, buffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, vertices, this.gl.STATIC_DRAW);
        
        const position = this.gl.getAttribLocation(this.program, 'position');
        this.gl.enableVertexAttribArray(position);
        this.gl.vertexAttribPointer(position, 2, this.gl.FLOAT, false, 0, 0);
        
        this.timeLocation = this.gl.getUniformLocation(this.program, 'time');
        this.frequenciesLocation = this.gl.getUniformLocation(this.program, 'frequencies');
    }

    resize() {
        this.canvas.width = 300;
        this.canvas.height = 300;
        this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }

    connectAudioSource(source) {
        if (!this.isInitialized) {
            console.error('Visualizer not initialized');
            return;
        }
        
        try {
            // Disconnect any existing connections
            if (this.currentSource) {
                this.currentSource.disconnect();
            }
            
            this.currentSource = source;
            source.connect(this.audioGain);
            console.log('Audio source connected successfully');
        } catch (error) {
            console.error('Error connecting audio source:', error);
        }
    }

    // New method to trigger a word event.
    // wordLength: number of characters in the spoken word.
    triggerWord(wordLength) {
        // Calculate intensity factor: longer word -> lower circle (more shrink)
        const intensity = Math.min(wordLength * 0.05, 0.7); // cap intensity so circle not too small
        // Set shrink value to reflect shrink; lower value means smaller circle.
        this.shrink = Math.min(this.shrink, 1.0 - intensity);
    }

    // Called when a word starts
    onWordStart(wordLength) {
        // Calculate how much to shrink based on word length
        const shrinkAmount = Math.min(0.3 + (wordLength * 0.02), 0.7);
        this.targetSize = 1.0 - shrinkAmount;
    }

    // Called when there's silence
    onSilence() {
        this.targetSize = 1.0;
    }

    startVisualization() {
        if (!this.audioInitialized) {
            this.initAudioContext().catch(console.error);
        }
        this.isAnimating = true;
        // Resetiraj prethodne frekvencije za glatki početak
        this.prevFrequencies = null;
        this.animate();
    }

    stopVisualization() {
        // Postupno zaustavljanje
        const fadeOut = () => {
            if (this.prevFrequencies) {
                let allZero = true;
                for (let i = 0; i < this.prevFrequencies.length; i++) {
                    this.prevFrequencies[i] *= 0.95;
                    if (this.prevFrequencies[i] > 0.01) allZero = false;
                }
                if (!allZero) {
                    requestAnimationFrame(fadeOut);
                } else {
                    this.isAnimating = false;
                }
            }
        };
        fadeOut();
    }

    setState(state) {
        // 0: idle, 1: speaking, 2: listening
        this.gl.uniform1i(this.stateLocation, state);
    }

    spawnRing() {
        if (this.rings.length < 10) {
            this.rings.push({ radius: 0.6, speed: 0.003 });
        }
    }

    updateRings() {
        const now = performance.now();
        
        // Spawn new rings based on speech or periodic timing
        if (now - this.lastRingTime > this.ringInterval) {
            this.spawnRing();
            this.lastRingTime = now;
        }
        
        // Update and filter rings
        this.rings = this.rings
            .map(ring => ({
                ...ring,
                radius: ring.radius + ring.speed
            }))
            .filter(ring => ring.radius < 2.0); // Remove rings that are too big
    }

    spawnWave(intensity) {
        if (this.waves.length >= this.maxWaves) return;
        
        // Suptilniji valovi s manjom brzinom
        this.waves.push({
            radius: 0.6 * this.currentSize,
            intensity: Math.min(intensity * 1.5, 0.7),  // Smanjen intenzitet
            lifetime: 2.0,  // Duži životni vijek za glađi fade
            birthTime: performance.now() / 1000,
            speed: 0.3 + intensity * 0.2  // Sporije širenje
        });
    }

    updateWaves(currentTime) {
        // Remove dead waves
        this.waves = this.waves.filter(wave => {
            const age = currentTime - wave.birthTime;
            return age < wave.lifetime;
        });

        // Update remaining waves
        this.waves.forEach(wave => {
            wave.radius += wave.speed * (1/60);  // Assuming 60fps
        });
    }

    updateGlowIntensity() {
        // Dinamički mijenjaj intenzitet glowa
        this.glowIntensity = 0.3 + 0.2 * Math.sin(performance.now() / 1000);
        this.gl.uniform1f(this.glowIntensityLocation, this.glowIntensity);
    }

    updateAnimation() {
        // Update radius with smooth interpolation
        const diff = this.targetRadius - this.currentRadius;
        this.currentRadius += diff * this.animationSpeed;
        
        // Get audio data if available
        let audioLevel = 0;
        if (this.analyser && this.frequencyData) {
            this.analyser.getByteFrequencyData(this.frequencyData);
            const sum = this.frequencyData.reduce((a, b) => a + b, 0);
            audioLevel = sum / (this.frequencyData.length * 255); // Normalize to 0-1
        }
        
        // Set uniforms for shader
        this.gl.uniform1f(this.circleSizeLocation, this.currentRadius);
        this.gl.uniform1f(this.audioLevelLocation, audioLevel);
    }

    animate() {
        if (!this.isAnimating || !this.isInitialized) return;
        
        try {
            const currentTime = performance.now() / 1000;
            
            this.updateAnimation();
            
            // Update time uniform
            this.gl.uniform1f(this.timeLocation, currentTime);
            
            // Draw
            this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, 4);
        } catch (error) {
            console.error('Animation error:', error);
        }
        
        requestAnimationFrame(() => this.animate());
    }

    // Call this when words are being spoken
    triggerWord(wordLength) {
        const intensity = Math.min(wordLength * 0.05, 0.7);
        this.targetRadius = this.baseRadius * (1 - intensity);
        setTimeout(() => {
            this.targetRadius = this.baseRadius;
        }, 100);
    }
}
