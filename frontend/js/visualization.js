/**
 * SoundBox Pallet Optimizer - Módulo de Visualização 3D
 */

let scene, camera, renderer, palletGroup, controls;
let lastResultData = null;

function initVisualization() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa);

    camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50000);
    camera.position.set(200, 200, 200);

    renderer = new THREE.WebGLRenderer({
        canvas: document.getElementById("pallet-canvas"),
        antialias: true,
    });
    renderer.shadowMap.enabled = true;

    // Iluminação
    const ambientLight = new THREE.AmbientLight(0x404040, 1.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 100, 50);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
    fillLight.position.set(-50, 50, -50);
    scene.add(fillLight);

    palletGroup = new THREE.Group();
    scene.add(palletGroup);

    // OrbitControls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;

    window.addEventListener("resize", onWindowResize);

    // Botão de reset
    document.getElementById("reset-view").addEventListener("click", resetCamera);

    animate();
}

function resizeRenderer() {
    const container = document.getElementById("visualization-container");
    const width = container.clientWidth;
    const height = container.clientHeight;
    if (width > 0 && height > 0) {
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
    }
}

function onWindowResize() {
    resizeRenderer();
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
}

function resetCamera() {
    if (!lastResultData) return;
    const p = lastResultData.pallet;
    const maxDim = Math.max(p.sizex, p.sizey, p.sizez);
    camera.position.set(maxDim * 1.8, maxDim * 1.5, maxDim * 1.8);
    controls.target.set(0, p.sizez * 0.3, 0);
    controls.update();
}

// Paleta de cores para diferenciar tipos de caixa
const BOX_COLORS = [
    0xdeaa87, 0x8ecae6, 0x95d5b2, 0xffd166, 0xef476f,
    0x118ab2, 0x06d6a0, 0xfca311, 0xe76f51, 0x7209b7,
];

function getColorForCode(code, codeMap) {
    if (!codeMap.has(code)) {
        codeMap.set(code, BOX_COLORS[codeMap.size % BOX_COLORS.length]);
    }
    return codeMap.get(code);
}

function drawResult(data) {
    lastResultData = data;

    // Limpa grupo anterior
    while (palletGroup.children.length > 0) {
        const child = palletGroup.children[0];
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
        palletGroup.remove(child);
    }

    const p = data.pallet;

    // Desenha base do palete
    const palletThickness = Math.max(4, p.sizez * 0.03);
    const palletGeo = new THREE.BoxGeometry(p.sizex, palletThickness, p.sizey);
    const palletMat = new THREE.MeshLambertMaterial({ color: 0x8b4513 });
    const palletMesh = new THREE.Mesh(palletGeo, palletMat);
    palletMesh.position.y = -palletThickness / 2;
    palletMesh.receiveShadow = true;
    palletGroup.add(palletMesh);

    // Desenha grade no chão para referência
    const gridHelper = new THREE.GridHelper(
        Math.max(p.sizex, p.sizey) * 1.5,
        20,
        0xcccccc,
        0xe0e0e0
    );
    gridHelper.position.y = -palletThickness;
    palletGroup.add(gridHelper);

    // Desenha as caixas
    const codeMap = new Map();

    data.cases.forEach((box) => {
        const color = getColorForCode(box.code, codeMap);
        const gap = 0.3; // Pequeno gap visual entre caixas

        const boxGeo = new THREE.BoxGeometry(
            box.sizex - gap,
            box.sizez - gap,
            box.sizey - gap
        );
        const boxMat = new THREE.MeshLambertMaterial({
            color: color,
            transparent: false,
        });
        const boxMesh = new THREE.Mesh(boxGeo, boxMat);
        boxMesh.castShadow = true;

        // Posição: centraliza no palete
        boxMesh.position.set(
            box.x + box.sizex / 2 - p.sizex / 2,
            box.z + box.sizez / 2,
            box.y + box.sizey / 2 - p.sizey / 2
        );
        palletGroup.add(boxMesh);

        // Arestas
        const edges = new THREE.EdgesGeometry(boxGeo);
        const line = new THREE.LineSegments(
            edges,
            new THREE.LineBasicMaterial({ color: 0x333333, opacity: 0.4, transparent: true })
        );
        line.position.copy(boxMesh.position);
        palletGroup.add(line);

        // Ponto vermelho no centro da face superior (ponto de pega do robô)
        const pickPointGeo = new THREE.SphereGeometry(1.5, 16, 16);
        const pickPointMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const pickPoint = new THREE.Mesh(pickPointGeo, pickPointMat);
        pickPoint.position.set(
            box.x + box.sizex / 2 - p.sizex / 2,
            box.z + box.sizez,  // Topo da caixa
            box.y + box.sizey / 2 - p.sizey / 2
        );
        palletGroup.add(pickPoint);

        // Linha de junção para caixas em L (marca onde as 2 caixas se encaixam)
        if (box.code && box.code.startsWith("PAR-L")) {
            drawLJointLines(box, p, palletGroup);
        }
    });

    // Ajusta câmera e renderer
    resizeRenderer();
    resetCamera();
}


/**
 * Desenha o contorno verde do formato L nas faces do bloco PAR-L.
 * Mostra o perfil 2D da caixa L projetado nas faces laterais.
 */
function drawLJointLines(box, pallet, group) {
    // Coordenadas do bloco no espaço da cena
    const x0 = box.x - pallet.sizex / 2;
    const x1 = x0 + box.sizex;
    const yBottom = box.z;          // Base do bloco
    const yTop = box.z + box.sizez; // Topo do bloco
    const yMid = box.z + box.sizez / 2; // Metade = ponto de encaixe
    const z0 = box.y - pallet.sizey / 2;
    const z1 = z0 + box.sizey;

    const material = new THREE.LineBasicMaterial({
        color: 0x00cc44,
        linewidth: 2,
    });

    // Perfil L na face frontal (z = z0)
    // Forma do L: base inteira + braço só na metade esquerda
    const lProfileFront = [
        new THREE.Vector3(x0, yBottom, z0),
        new THREE.Vector3(x1, yBottom, z0),
        new THREE.Vector3(x1, yMid, z0),
        new THREE.Vector3(x0 + box.sizex / 2, yMid, z0),
        new THREE.Vector3(x0 + box.sizex / 2, yTop, z0),
        new THREE.Vector3(x0, yTop, z0),
        new THREE.Vector3(x0, yBottom, z0), // Fecha
    ];
    const geoFront = new THREE.BufferGeometry().setFromPoints(lProfileFront);
    group.add(new THREE.Line(geoFront, material));

    // Perfil L invertido (complemento) na face frontal
    const lProfileFrontInv = [
        new THREE.Vector3(x0, yBottom, z0),
        new THREE.Vector3(x1, yBottom, z0),
        new THREE.Vector3(x1, yTop, z0),
        new THREE.Vector3(x0 + box.sizex / 2, yTop, z0),
        new THREE.Vector3(x0 + box.sizex / 2, yMid, z0),
        new THREE.Vector3(x0, yMid, z0),
        new THREE.Vector3(x0, yBottom, z0),
    ];
    const geoFrontInv = new THREE.BufferGeometry().setFromPoints(lProfileFrontInv);
    group.add(new THREE.Line(geoFrontInv, material));

    // Perfil L na face traseira (z = z1)
    const lProfileBack = lProfileFront.map(p => new THREE.Vector3(p.x, p.y, z1));
    const geoBack = new THREE.BufferGeometry().setFromPoints(lProfileBack);
    group.add(new THREE.Line(geoBack, material));

    // Perfil L invertido na face traseira
    const lProfileBackInv = lProfileFrontInv.map(p => new THREE.Vector3(p.x, p.y, z1));
    const geoBackInv = new THREE.BufferGeometry().setFromPoints(lProfileBackInv);
    group.add(new THREE.Line(geoBackInv, material));

    // Linha de junção horizontal nas faces laterais (x = x0 e x = x1)
    const sideMid = [
        new THREE.Vector3(x0, yMid, z0),
        new THREE.Vector3(x0, yMid, z1),
    ];
    const geoSideL = new THREE.BufferGeometry().setFromPoints(sideMid);
    group.add(new THREE.Line(geoSideL, material));

    const sideMidR = [
        new THREE.Vector3(x1, yMid, z0),
        new THREE.Vector3(x1, yMid, z1),
    ];
    const geoSideR = new THREE.BufferGeometry().setFromPoints(sideMidR);
    group.add(new THREE.Line(geoSideR, material));

    // Linha vertical no meio da face frontal e traseira (onde o braço muda)
    const vertFront = [
        new THREE.Vector3(x0 + box.sizex / 2, yMid, z0),
        new THREE.Vector3(x0 + box.sizex / 2, yTop, z0),
    ];
    const geoVertF = new THREE.BufferGeometry().setFromPoints(vertFront);
    group.add(new THREE.Line(geoVertF, material));

    const vertBack = [
        new THREE.Vector3(x0 + box.sizex / 2, yMid, z1),
        new THREE.Vector3(x0 + box.sizex / 2, yTop, z1),
    ];
    const geoVertB = new THREE.BufferGeometry().setFromPoints(vertBack);
    group.add(new THREE.Line(geoVertB, material));
}
