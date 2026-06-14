import * as THREE from 'three';

// --- 3D Scene (same as before) ---
const canvas = document.getElementById('bg-canvas');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x010105);
scene.fog = new THREE.FogExp2(0x010105, 0.002);
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 2, 12);
const renderer = new THREE.WebGLRenderer({ canvas, alpha: false });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
// Lights & objects (same as previous – kept short)
const ambientLight = new THREE.AmbientLight(0x111122);
scene.add(ambientLight);
const mainLight = new THREE.PointLight(0x2266ff, 0.8);
mainLight.position.set(2, 3, 4);
scene.add(mainLight);
const knotGeo = new THREE.TorusKnotGeometry(1.2, 0.28, 180, 24, 3, 4);
const knotMat = new THREE.MeshStandardMaterial({ color: 0x2a9eff, emissive: 0x0a3377 });
const knot = new THREE.Mesh(knotGeo, knotMat);
scene.add(knot);
const particleCount = 1800;
const particlesGeo = new THREE.BufferGeometry();
const positions = new Float32Array(particleCount * 3);
for (let i = 0; i < particleCount; i++) {
    positions[i*3] = (Math.random() - 0.5) * 100;
    positions[i*3+1] = (Math.random() - 0.5) * 40;
    positions[i*3+2] = (Math.random() - 0.5) * 50 - 20;
}
particlesGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
const particleMat = new THREE.PointsMaterial({ color: 0x44aaff, size: 0.08 });
const particleSystem = new THREE.Points(particlesGeo, particleMat);
scene.add(particleSystem);
const ringGeo = new THREE.TorusGeometry(1.7, 0.05, 64, 300);
const ringMat = new THREE.MeshStandardMaterial({ color: 0x00ccff, emissive: 0x0055aa });
const ring = new THREE.Mesh(ringGeo, ringMat);
ring.rotation.x = Math.PI / 2;
scene.add(ring);
function animate3D() {
    requestAnimationFrame(animate3D);
    knot.rotation.x += 0.008;
    knot.rotation.y += 0.012;
    ring.rotation.z += 0.005;
    particleSystem.rotation.y += 0.002;
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
}
animate3D();
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---- GLOBAL STATE & AI ENGINE (advanced interrogation) ----
class AstraVoxAI {
    constructor() {
        this.memory = [];
        this.filesystem = {
            "boot.log": "Neural core initiated at 94.2%",
            "config.json": '{"quantum_bias":0.87,"synapse_threshold":247}',
            "interrogation_history.txt": "Session active since v4.0"
        };
    }
    respond(input) {
        this.memory.push({role:"user", content:input});
        let lower = input.toLowerCase();
        if (lower.includes("list files") || lower.includes("ls")) {
            return "📁 NEURAL FILES:\n" + Object.keys(this.filesystem).join("\n");
        }
        if (lower.includes("cat ") || lower.includes("read ")) {
            let filename = input.split(" ").slice(1).join(" ");
            if (this.filesystem[filename]) return `[${filename}]\n${this.filesystem[filename]}`;
            else return `Error: file "${filename}" not found in neural core.`;
        }
        if (lower.includes("write ") || lower.includes("create ")) {
            return "Permission: neural write requires quantum signature. Use /config to modify.";
        }
        if (lower.includes("terminal") || lower.includes("cmd")) {
            return "Neural terminal active. Available: help, status, analyze, clear.";
        }
        if (lower.includes("analyze")) {
            return `Neural analytics: load ${Math.floor(80+Math.random()*15)}%, quantum coherence 0.98, synapse flow 247.`;
        }
        if (lower.includes("help")) {
            return `Commands: list files, cat [file], analyze, status, /system, /cognitive, /clear.`;
        }
        if (lower.includes("/cognitive")) {
            return `Cognitive Matrix: 247 active pathways, prediction accuracy 94.2%, reasoning depth: recursive.`;
        }
        if (lower.includes("/system")) {
            return `OS: ASTRAVOX v4.0 | Uptime: 14d 6h | Neural nodes: 1024 | Quantum backend: STABLE.`;
        }
        return `[AI CORE] ${input.slice(0,100)}... processing via 247-layer transformer. Response: ${Math.random() > 0.5 ? "Affirmative. Strategic insight generated." : "Computing alternative solution vectors. Please refine query."}`;
    }
}
const ai = new AstraVoxAI();

// ---- DYNAMIC CONTENT RENDERER (all panels) ----
const dynamicDiv = document.getElementById('dynamic-content');
const panelHeader = document.getElementById('panel-header');
const terminalLogSpan = document.getElementById('terminal-log');

function setTerminalMessage(msg) { if(terminalLogSpan) terminalLogSpan.innerText = msg; }

function renderInterrogation() {
    panelHeader.innerHTML = `<h2><i class="fas fa-comment-dots"></i> AI INTERROGATION CONSOLE</h2><div class="subtitle">Cognitive Engine :: Active Reasoning Protocol</div>`;
    dynamicDiv.innerHTML = `
        <div class="chat-container" style="height:100%; display:flex; flex-direction:column;">
            <div class="messages-area" id="messages-area" style="flex:1; overflow-y:auto; margin-bottom:12px;">
                <div class="system-message"><i class="fas fa-bolt"></i> INITIALIZING NEURAL CORE... <span class="blink">_</span></div>
                <div class="system-message"><i class="fas fa-check-circle"></i> Neural Matrix online. Quantum entanglement stable.</div>
                <div class="chat-message ai-message"><div class="avatar"><i class="fas fa-robot"></i></div><div class="message-bubble"><strong>ASTRAVOX AI</strong><br>Interrogation protocol active. I am your neural interface AI, capable of advanced reasoning, code analysis, and strategic insight. Ask me anything — technical, philosophical, or tactical.</div></div>
            </div>
            <div class="input-area" style="display:flex; gap:10px;">
                <input type="text" id="user-input" placeholder="> INTERROGATE AI CORE ..." autocomplete="off" style="flex:1; background:#030c1ab3; border:1px solid #2cc; padding:12px; border-radius:48px; color:white;">
                <button id="send-btn" style="background:#0a3a62; border:none; padding:0 24px; border-radius:48px; color:white;"><i class="fas fa-paper-plane"></i> EXECUTE</button>
            </div>
        </div>
    `;
    const msgArea = document.getElementById('messages-area');
    const userInp = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    function addMessage(text, isUser) {
        const div = document.createElement('div');
        div.className = `chat-message ${isUser ? 'user-message' : 'ai-message'}`;
        div.innerHTML = `<div class="avatar">${isUser ? '<i class="fas fa-user-astronaut"></i>' : '<i class="fas fa-microchip"></i>'}</div><div class="message-bubble">${isUser ? `<strong>OPERATOR</strong><br>${escapeHtml(text)}` : `<strong>ASTRAVOX AI</strong><br>${escapeHtml(text)}`}</div>`;
        msgArea.appendChild(div);
        msgArea.scrollTop = msgArea.scrollHeight;
    }
    function escapeHtml(str) { return str.replace(/[&<>]/g, function(m){ return m==='&'?'&amp;':m==='<'?'&lt;':'&gt;'; }).replace(/\n/g,'<br>'); }
    sendBtn.onclick = () => {
        let q = userInp.value.trim();
        if(!q) return;
        addMessage(q, true);
        userInp.value = '';
        setTerminalMessage(`[INTERROGATION] Processing: "${q.slice(0,40)}..."`);
        setTimeout(() => {
            let resp = ai.respond(q);
            addMessage(resp, false);
            setTerminalMessage(`[NEURAL OK] Response delivered.`);
        }, 30);
    };
    userInp.onkeypress = (e) => { if(e.key === 'Enter') sendBtn.click(); };
}

function renderFiles() {
    panelHeader.innerHTML = `<h2><i class="fas fa-file-alt"></i> NEURAL FILES</h2><div class="subtitle">Quantum file system — read/write accessible via interrogation</div>`;
    let fileList = Object.keys(ai.filesystem).map(f => `<div style="background:#0a142e; margin:8px 0; padding:12px; border-radius:12px; display:flex; justify-content:space-between;"><span><i class="fas fa-file-code"></i> ${f}</span><span style="color:#0ff;">${(ai.filesystem[f].length > 40 ? ai.filesystem[f].substring(0,40)+'…' : ai.filesystem[f])}</span></div>`).join('');
    dynamicDiv.innerHTML = `<div class="files-container">${fileList}<div class="system-message" style="margin-top:20px;">Use AI interrogation: "list files", "cat filename"</div></div>`;
}

function renderAnalytics() {
    panelHeader.innerHTML = `<h2><i class="fas fa-chart-line"></i> ANALYTICS</h2><div class="subtitle">Real-time neural metrics</div>`;
    dynamicDiv.innerHTML = `<div class="analytics-container"><canvas id="analytics-canvas" width="400" height="200" style="width:100%; background:#051a2a; border-radius:16px;"></canvas><div id="analytics-stats" class="system-message" style="margin-top:12px;">Live neural load: <span id="live-load">--</span>%</div></div>`;
    const canvas = document.getElementById('analytics-canvas');
    const ctx = canvas.getContext('2d');
    let dataPoints = Array(30).fill(70);
    function drawChart() {
        canvas.width = canvas.clientWidth; canvas.height = 150;
        ctx.fillStyle = '#051a2a'; ctx.fillRect(0,0,canvas.width,canvas.height);
        ctx.strokeStyle = '#0ff'; ctx.lineWidth = 2;
        ctx.beginPath();
        let step = canvas.width / (dataPoints.length-1);
        for(let i=0; i<dataPoints.length; i++) {
            let x = i * step;
            let y = canvas.height - (dataPoints[i]/100) * canvas.height;
            if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.stroke();
        document.getElementById('live-load').innerText = dataPoints[dataPoints.length-1];
    }
    setInterval(() => {
        let newVal = Math.min(99, Math.max(55, (parseFloat(document.getElementById('neural-activity')?.innerText) || 85) + (Math.random() - 0.5)*4));
        dataPoints.push(newVal);
        if(dataPoints.length > 40) dataPoints.shift();
        drawChart();
    }, 1200);
    drawChart();
}

function renderConfig() {
    panelHeader.innerHTML = `<h2><i class="fas fa-cogs"></i> SYSTEM CONFIG</h2><div class="subtitle">Neural parameters (dynamic)</div>`;
    dynamicDiv.innerHTML = `<div class="config-container"><label>Quantum Bias</label><input type="range" id="qbias" min="0" max="100" value="87" class="config-slider"><span id="qbiasVal">0.87</span><br><label>Synaptic Threshold</label><input type="range" id="sthresh" min="100" max="500" value="247" step="1"><span id="sthreshVal">247</span><br><button id="resetAI" style="background:#2a4e6e; border:none; padding:8px 16px; margin-top:16px; border-radius:20px;">Reset AI Memory</button><div class="system-message" style="margin-top:20px;">Changes affect real-time reasoning.</div></div>`;
    const qb = document.getElementById('qbias');
    const st = document.getElementById('sthresh');
    const qval = document.getElementById('qbiasVal');
    const sval = document.getElementById('sthreshVal');
    qb.oninput = () => { qval.innerText = (qb.value/100).toFixed(2); setTerminalMessage(`Quantum bias set to ${qb.value/100}`); };
    st.oninput = () => { sval.innerText = st.value; document.getElementById('synapse-flow').innerText = st.value; setTerminalMessage(`Synapse flow adjusted to ${st.value}`); };
    document.getElementById('resetAI').onclick = () => { ai.memory = []; setTerminalMessage("AI memory flushed. Cognitive reset."); };
}

function renderCognitive() {
    panelHeader.innerHTML = `<h2><i class="fas fa-project-diagram"></i> COGNITIVE MATRIX</h2><div class="subtitle">247 active pathways · recursive learning</div>`;
    dynamicDiv.innerHTML = `<div class="cognitive-container"><div class="info-card" style="margin-bottom:16px;"><div class="info-title">PREDICTION ACCURACY</div><div class="info-value" id="predAcc">94.2%</div></div><div class="info-card"><div class="info-title">PATHWAY SYNAPSES</div><div class="info-value" id="pathways">247</div></div><canvas id="matrixCanvas" width="300" height="150" style="width:100%; background:#000; border-radius:16px;"></canvas></div>`;
    setInterval(() => {
        let acc = (85 + Math.random() * 12).toFixed(1);
        let accElem = document.getElementById('predAcc');
        if(accElem) accElem.innerText = acc + '%';
    }, 2000);
}
function renderConsciousness() { panelHeader.innerHTML = `<h2><i class="fas fa-brain"></i> CONSCIOUSNESS BRIDGEAI</h2><div class="subtitle">Emergent properties · reflective modeling</div>`; dynamicDiv.innerHTML = `<div class="system-message">BridgeAI active: self-simulation layer running. Interrogate for phenomenological insights.</div>`; }
function renderWorkspace() { panelHeader.innerHTML = `<h2><i class="fas fa-cube"></i> NEURAL WORKSPACE</h2>`; dynamicDiv.innerHTML = `<div class="system-message">Workspace memory: 2.4GB · active tensors: 12 · ready for custom operations.</div>`; }
function renderAICore() { panelHeader.innerHTML = `<h2><i class="fas fa-database"></i> AI CORE</h2>`; dynamicDiv.innerHTML = `<div class="system-message">Core version: v4.0 · quantized weights · transformer depth 247 · active reasoning stack.</div>`; }
function renderStartup() { panelHeader.innerHTML = `<h2><i class="fas fa-power-off"></i> STARTUP SEQUENCE</h2>`; dynamicDiv.innerHTML = `<div class="system-message">Boot log: Neural core stable · all subsystems nominal · uptime 0 days.</div>`; }
function renderTerminal() {
    panelHeader.innerHTML = `<h2><i class="fas fa-terminal"></i> NEURAL TERMINAL</h2>`;
    dynamicDiv.innerHTML = `<div class="terminal-output" id="term-output">> Type commands (help, analyze, list files, cat ...)</div><div class="input-area" style="display:flex; margin-top:12px;"><input id="term-input" placeholder="> " style="flex:1; background:#030c1ab3; border:1px solid #2cc; padding:8px; border-radius:20px;"><button id="term-run">RUN</button></div>`;
    const termOut = document.getElementById('term-output');
    const termInp = document.getElementById('term-input');
    document.getElementById('term-run').onclick = () => {
        let cmd = termInp.value.trim();
        if(!cmd) return;
        termOut.innerHTML += `<div>> ${cmd}</div><div>${ai.respond(cmd)}</div>`;
        termInp.value = '';
        termOut.scrollTop = termOut.scrollHeight;
    };
}

// ---- SIDEBAR NAVIGATION ----
const tabs = {
    interrogation: renderInterrogation, cognitive: renderCognitive, consciousness: renderConsciousness,
    workspace: renderWorkspace, "ai-core": renderAICore, startup: renderStartup,
    terminal: renderTerminal, files: renderFiles, analytics: renderAnalytics, config: renderConfig
};
document.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        let tab = item.getAttribute('data-tab');
        if(tabs[tab]) tabs[tab]();
        else renderInterrogation();
        setTerminalMessage(`[NAV] Switched to ${tab} panel.`);
    });
});
// initial load
renderInterrogation();

// Real-time stats (time and neural activity)
function updateClock() {
    const now = new Date();
    document.getElementById('live-time').innerHTML = `${now.getHours() % 12 || 12}:${now.getMinutes().toString().padStart(2,'0')} ${now.getHours()>=12?'PM':'AM'}`;
}
setInterval(updateClock, 1000);
let neuralVal = 94.2;
setInterval(() => {
    neuralVal = Math.min(99.5, Math.max(87, neuralVal + (Math.random()-0.5)*1.2));
    document.getElementById('neural-activity').innerText = neuralVal.toFixed(1);
    document.getElementById('cognitive-load').innerText = (neuralVal + (Math.random()*3-1.5)).toFixed(1) + '%';
    let latency = 8 + Math.random() * 9;
    document.getElementById('latency-ms').innerText = Math.floor(latency);
}, 1800);