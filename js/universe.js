// ============================================
// ASTRAVOX PRIME — 3D UNIVERSE BACKGROUND
// Sovereign AI Operating System
// ============================================

(function initUniverse() {
    const canvas = document.getElementById('universe-canvas');
    if (!canvas) return;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05050A);
    scene.fog = new THREE.FogExp2(0x05050A, 0.003);

    // Camera
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 1.5, 12);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Starfield
    const starCount = 4000;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
        starPositions[i*3] = (Math.random() - 0.5) * 200;
        starPositions[i*3+1] = (Math.random() - 0.5) * 100;
        starPositions[i*3+2] = (Math.random() - 0.5) * 80 - 40;
    }
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const stars = new THREE.Points(starGeometry, new THREE.PointsMaterial({ color: 0xffffff, size: 0.1, transparent: true, opacity: 0.6 }));
    scene.add(stars);

    // Galaxy Particles
    const galaxyCount = 5000;
    const galaxyGeometry = new THREE.BufferGeometry();
    const galaxyPositions = new Float32Array(galaxyCount * 3);
    const galaxyColors = new Float32Array(galaxyCount * 3);
    
    for (let i = 0; i < galaxyCount; i++) {
        const radius = 3 + Math.random() * 5;
        const angle = Math.random() * Math.PI * 2;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        const y = Math.sin(angle * 3) * 0.5;
        
        galaxyPositions[i*3] = x;
        galaxyPositions[i*3+1] = y;
        galaxyPositions[i*3+2] = z;
        
        const rand = Math.random();
        if (rand < 0.34) {
            galaxyColors[i*3] = 0.0; galaxyColors[i*3+1] = 0.8; galaxyColors[i*3+2] = 1.0;
        } else if (rand < 0.67) {
            galaxyColors[i*3] = 0.6; galaxyColors[i*3+1] = 0.3; galaxyColors[i*3+2] = 0.9;
        } else {
            galaxyColors[i*3] = 1.0; galaxyColors[i*3+1] = 0.2; galaxyColors[i*3+2] = 0.6;
        }
    }
    galaxyGeometry.setAttribute('position', new THREE.BufferAttribute(galaxyPositions, 3));
    galaxyGeometry.setAttribute('color', new THREE.BufferAttribute(galaxyColors, 3));
    const galaxy = new THREE.Points(galaxyGeometry, new THREE.PointsMaterial({ size: 0.06, vertexColors: true, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending }));
    scene.add(galaxy);

    // Central Core
    const coreGeo = new THREE.IcosahedronGeometry(0.8, 1);
    const coreMat = new THREE.MeshStandardMaterial({ color: 0x9B51E0, emissive: 0x2A1A4A, emissiveIntensity: 0.5, metalness: 0.8 });
    const core = new THREE.Mesh(coreGeo, coreMat);
    core.position.y = -0.2;
    scene.add(core);

    // Lights
    scene.add(new THREE.AmbientLight(0x303050, 0.5));
    const dirLight = new THREE.DirectionalLight(0xFFFFFF, 1);
    dirLight.position.set(2, 3, 4);
    scene.add(dirLight);
    scene.add(new THREE.PointLight(0x00F2FE, 0.6)).position.set(2, 2, 3);
    scene.add(new THREE.PointLight(0x9B51E0, 0.6)).position.set(-2, 1, 3);
    scene.add(new THREE.PointLight(0xFF007F, 0.4)).position.set(0, 2, -3);

    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.005;
        
        galaxy.rotation.y = time * 0.05;
        stars.rotation.y = time * 0.02;
        core.rotation.x = time * 0.3;
        core.rotation.y = time * 0.5;
        
        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
})();