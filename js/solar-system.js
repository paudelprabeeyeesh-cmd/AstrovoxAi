(function() {
    const canvas = document.getElementById('solar-canvas');
    if (!canvas) return;

    // --- Setup Three.js ---
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05050A);
    scene.fog = new THREE.FogExp2(0x05050A, 0.0008);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 5, 22);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // --- Starfield (distant stars) ---
    const starCount = 2500;
    const starGeo = new THREE.BufferGeometry();
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
        starPos[i*3] = (Math.random() - 0.5) * 400;
        starPos[i*3+1] = (Math.random() - 0.5) * 200;
        starPos[i*3+2] = (Math.random() - 0.5) * 100 - 50;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.2, transparent: true, opacity: 0.6 }));
    scene.add(stars);

    // --- Sun light ---
    const sunLight = new THREE.PointLight(0xffaa66, 1.2);
    sunLight.position.set(0, 0, 0);
    scene.add(sunLight);
    const ambientLight = new THREE.AmbientLight(0x22223b);
    scene.add(ambientLight);

    // --- Sun mesh ---
    const sunGeo = new THREE.SphereGeometry(1.6, 64, 64);
    const sunMat = new THREE.MeshStandardMaterial({ color: 0xffaa66, emissive: 0xff4422, emissiveIntensity: 0.4 });
    const sunMesh = new THREE.Mesh(sunGeo, sunMat);
    scene.add(sunMesh);

    // --- Planets (simplified for speed and visibility) ---
    const planets = [
        { color: 0xbc9a6c, size: 0.32, dist: 3.8, speed: 0.022 },
        { color: 0xe6b800, size: 0.38, dist: 5.2, speed: 0.017 },
        { color: 0x2e86c1, size: 0.44, dist: 7.0, speed: 0.013 },
        { color: 0xc4553c, size: 0.42, dist: 8.8, speed: 0.011 },
        { color: 0xd8a27a, size: 0.85, dist: 12.0, speed: 0.0075 },
        { color: 0xe8cfaa, size: 0.78, dist: 14.5, speed: 0.0065 },
        { color: 0x9fd9e8, size: 0.64, dist: 17.5, speed: 0.0055 },
        { color: 0x3b5fe0, size: 0.62, dist: 20.5, speed: 0.0045 }
    ];

    const planetMeshes = [];
    const angles = planets.map(() => Math.random() * Math.PI * 2);

    planets.forEach((p, i) => {
        const geo = new THREE.SphereGeometry(p.size, 64, 64);
        const mat = new THREE.MeshStandardMaterial({ color: p.color });
        const mesh = new THREE.Mesh(geo, mat);
        scene.add(mesh);
        planetMeshes.push({ mesh, dist: p.dist, speed: p.speed, angle: angles[i] });
    });

    // --- Asteroid belt (decorative) ---
    const astCount = 1200;
    const astGeo = new THREE.BufferGeometry();
    const astPos = new Float32Array(astCount * 3);
    for (let i = 0; i < astCount; i++) {
        const r = 9.5 + Math.random() * 2.5;
        const a = Math.random() * Math.PI * 2;
        astPos[i*3] = Math.cos(a) * r;
        astPos[i*3+1] = (Math.random() - 0.5) * 0.6;
        astPos[i*3+2] = Math.sin(a) * r;
    }
    astGeo.setAttribute('position', new THREE.BufferAttribute(astPos, 3));
    const asteroidField = new THREE.Points(astGeo, new THREE.PointsMaterial({ color: 0xaa8866, size: 0.06 }));
    scene.add(asteroidField);

    // --- Mouse parallax (gentle movement) ---
    let targetX = 0, curX = 0;
    document.addEventListener('mousemove', (e) => {
        targetX = (e.clientX / window.innerWidth - 0.5) * 2.5;
        curX += (targetX - curX) * 0.05;
        camera.position.x = curX;
        camera.lookAt(0, 0, 0);
    });

    // --- Animation loop ---
    let time = 0;
    function animate() {
        requestAnimationFrame(animate);
        time += 0.006;

        stars.rotation.y = time * 0.01;
        asteroidField.rotation.y = time * 0.004;

        planetMeshes.forEach(p => {
            p.angle += p.speed;
            p.mesh.position.x = Math.cos(p.angle) * p.dist;
            p.mesh.position.z = Math.sin(p.angle) * p.dist;
            p.mesh.rotation.y += 0.01;
        });

        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    console.log('3D Solar System active');
})();