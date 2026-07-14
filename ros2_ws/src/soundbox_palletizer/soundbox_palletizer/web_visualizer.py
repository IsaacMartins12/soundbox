"""
SoundBox Palletizer - Web 3D Visualizer
========================================
Servidor web Flask que renderiza o robô GP88 + caixas no navegador via Three.js.
Acesse http://localhost:9090 no navegador Windows.
"""
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://host.docker.internal:5000")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SoundBox - Robô Paletizador GP88</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; }
        #info {
            position: absolute; top: 15px; left: 15px; color: #fff;
            background: rgba(10,10,30,0.85); padding: 18px 22px;
            border-radius: 10px; z-index: 100; min-width: 240px;
            border: 1px solid rgba(79,195,247,0.3);
            backdrop-filter: blur(8px);
        }
        #info h3 { margin: 0 0 10px 0; color: #4fc3f7; font-size: 16px; }
        #status { font-size: 13px; line-height: 1.6; }
        #progress-container {
            margin-top: 10px; background: rgba(255,255,255,0.1);
            border-radius: 6px; height: 8px; overflow: hidden;
        }
        #progress-bar {
            height: 100%; width: 0%; background: linear-gradient(90deg, #4fc3f7, #4caf50);
            border-radius: 6px; transition: width 0.3s ease;
        }
        #counter { margin-top: 6px; font-size: 12px; color: #aaa; }
        #controls {
            position: absolute; bottom: 25px; left: 50%;
            transform: translateX(-50%); z-index: 100;
            display: flex; gap: 12px;
        }
        #controls button {
            padding: 14px 28px; font-size: 14px; cursor: pointer;
            border: none; border-radius: 8px; font-weight: 600;
            transition: all 0.2s ease; text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        #startBtn { background: linear-gradient(135deg, #4caf50, #388e3c); color: white; }
        #resetBtn { background: linear-gradient(135deg, #ff5722, #d84315); color: white; }
        #startBtn:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(76,175,80,0.4); }
        #resetBtn:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(255,87,34,0.4); }
        #startBtn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }
    </style>
</head>
<body>
    <div id="info">
        <h3>&#129302; Yaskawa GP88 - Paletização</h3>
        <div style="margin-bottom:8px;">
            <select id="modelSelect" onchange="changeModel()" style="width:100%;padding:6px;border-radius:4px;border:1px solid #555;background:#222;color:#fff;font-size:12px;">
                <option value="">Carregando modelos...</option>
            </select>
        </div>
        <div id="status">Carregando...</div>
        <div id="progress-container"><div id="progress-bar"></div></div>
        <div id="counter"></div>
    </div>
    <div id="controls">
        <button id="startBtn" onclick="startPalletizing()">&#9654; Iniciar</button>
        <button id="resetBtn" onclick="resetScene()">&#8634; Reset</button>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script>
        // ===== GLOBALS =====
        let scene, camera, renderer, controls;
        let robotGroup, joints = [];
        let gripperGroup, gripperPads = [];
        let boxes = [], palletData = null;
        let animating = false, currentBoxIndex = 0;
        let carriedBox = null;
        let clock = new THREE.Clock();

        // Robot dimensions (meters, GP88 scale)
        const ROBOT_BASE_HEIGHT = 0.25;
        const LINK1_HEIGHT = 0.9;
        const LINK2_LENGTH = 1.0;
        const LINK3_LENGTH = 0.9;
        const WRIST_LENGTH = 0.25;

        // Positions in scene
        const ROBOT_POS = new THREE.Vector3(-1.2, 0, 0);
        const PALLET_POS = new THREE.Vector3(1.2, 0, 0.3);
        const CONVEYOR_POS = new THREE.Vector3(-1.2, 0, -1.8);

        // Joint home angles (radians)
        const HOME_ANGLES = [0, -0.3, 0.8, 0, -0.5, 0];

        init();
        animate();

        function init() {
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x2a2a3e);
            scene.fog = new THREE.FogExp2(0x2a2a3e, 0.035);

            // Camera
            camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
            camera.position.set(5, 3.5, 5);

            // Renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.2;
            document.body.appendChild(renderer.domElement);

            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.target.set(0, 0.8, 0);
            controls.enableDamping = true;
            controls.dampingFactor = 0.08;
            controls.minDistance = 2;
            controls.maxDistance = 15;

            // Lighting
            setupLighting();

            // Environment
            createFloor();
            createSafetyFence();
            createConveyor();
            createPallet();
            createRobot();

            // Load data
            loadBoxData();

            window.addEventListener('resize', onResize);
        }

        function setupLighting() {
            // Ambient for soft fill
            const ambient = new THREE.AmbientLight(0x8899bb, 0.6);
            scene.add(ambient);

            // Main directional (sun-like)
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
            dirLight.position.set(5, 12, 5);
            dirLight.castShadow = true;
            dirLight.shadow.mapSize.set(2048, 2048);
            dirLight.shadow.camera.left = -8;
            dirLight.shadow.camera.right = 8;
            dirLight.shadow.camera.top = 8;
            dirLight.shadow.camera.bottom = -8;
            dirLight.shadow.camera.near = 0.5;
            dirLight.shadow.camera.far = 25;
            dirLight.shadow.bias = -0.001;
            scene.add(dirLight);

            // Fill light from opposite side
            const fillLight = new THREE.DirectionalLight(0x99bbff, 0.3);
            fillLight.position.set(-5, 6, -3);
            scene.add(fillLight);

            // Warm accent from below-ish
            const warmLight = new THREE.PointLight(0xffaa44, 0.3, 10);
            warmLight.position.set(0, 0.5, 2);
            scene.add(warmLight);

            // Cool overhead highlight
            const spotLight = new THREE.SpotLight(0xaaccff, 0.5, 15, Math.PI/6, 0.5);
            spotLight.position.set(0, 8, 0);
            spotLight.castShadow = false;
            scene.add(spotLight);
        }

        function createFloor() {
            // Concrete floor
            const floorGeo = new THREE.PlaneGeometry(16, 16);
            const floorMat = new THREE.MeshStandardMaterial({
                color: 0x888888, roughness: 0.9, metalness: 0.0
            });
            const floor = new THREE.Mesh(floorGeo, floorMat);
            floor.rotation.x = -Math.PI / 2;
            floor.receiveShadow = true;
            scene.add(floor);

            // Subtle grid lines on floor
            const gridHelper = new THREE.GridHelper(16, 32, 0x666666, 0x555555);
            gridHelper.position.y = 0.001;
            gridHelper.material.opacity = 0.15;
            gridHelper.material.transparent = true;
            scene.add(gridHelper);
        }

        function createSafetyFence() {
            const fencePositions = [
                [-3.5, 0, -3.5], [3.5, 0, -3.5], [3.5, 0, 3.5], [-3.5, 0, 3.5],
                [0, 0, -3.5], [0, 0, 3.5], [-3.5, 0, 0], [3.5, 0, 0]
            ];

            fencePositions.forEach(pos => {
                createFencePost(pos[0], pos[2]);
            });

            // Horizontal rails
            const railMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.6, metalness: 0.7 });
            const railPositions = [
                [[-3.5, 0.5, -3.5], [3.5, 0.5, -3.5]],
                [[-3.5, 1.0, -3.5], [3.5, 1.0, -3.5]],
                [[-3.5, 0.5, 3.5], [3.5, 0.5, 3.5]],
                [[-3.5, 1.0, 3.5], [3.5, 1.0, 3.5]],
                [[-3.5, 0.5, -3.5], [-3.5, 0.5, 3.5]],
                [[-3.5, 1.0, -3.5], [-3.5, 1.0, 3.5]],
                [[3.5, 0.5, -3.5], [3.5, 0.5, 3.5]],
                [[3.5, 1.0, -3.5], [3.5, 1.0, 3.5]],
            ];

            railPositions.forEach(pair => {
                const start = new THREE.Vector3(...pair[0]);
                const end = new THREE.Vector3(...pair[1]);
                const dir = new THREE.Vector3().subVectors(end, start);
                const len = dir.length();
                const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);

                const rail = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.02, 0.02, len, 8),
                    railMat
                );
                rail.position.copy(mid);
                // Orient rail
                if (Math.abs(dir.x) > Math.abs(dir.z)) {
                    rail.rotation.z = Math.PI / 2;
                } else {
                    rail.rotation.x = Math.PI / 2;
                }
                rail.castShadow = true;
                scene.add(rail);
            });
        }

        function createFencePost(x, z) {
            const postGroup = new THREE.Group();
            // Yellow/black striped post
            const segHeight = 0.125;
            for (let i = 0; i < 9; i++) {
                const color = i % 2 === 0 ? 0xf5c300 : 0x222222;
                const seg = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.04, 0.04, segHeight, 12),
                    new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.3 })
                );
                seg.position.y = segHeight / 2 + i * segHeight;
                seg.castShadow = true;
                postGroup.add(seg);
            }
            postGroup.position.set(x, 0, z);
            scene.add(postGroup);
        }

        function createConveyor() {
            const convGroup = new THREE.Group();

            // Frame/legs
            const frameMat = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.6, metalness: 0.8 });
            const legGeo = new THREE.BoxGeometry(0.06, 0.45, 0.06);
            const legPositions = [[-1.0, 0.225, -0.28], [1.0, 0.225, -0.28], [-1.0, 0.225, 0.28], [1.0, 0.225, 0.28]];
            legPositions.forEach(p => {
                const leg = new THREE.Mesh(legGeo, frameMat);
                leg.position.set(...p);
                leg.castShadow = true;
                convGroup.add(leg);
            });

            // Side rails
            const sideGeo = new THREE.BoxGeometry(2.4, 0.06, 0.04);
            const side1 = new THREE.Mesh(sideGeo, frameMat);
            side1.position.set(0, 0.48, -0.30);
            convGroup.add(side1);
            const side2 = new THREE.Mesh(sideGeo, frameMat);
            side2.position.set(0, 0.48, 0.30);
            convGroup.add(side2);

            // Belt surface
            const beltMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.85, metalness: 0.1 });
            const belt = new THREE.Mesh(new THREE.BoxGeometry(2.3, 0.02, 0.52), beltMat);
            belt.position.set(0, 0.50, 0);
            convGroup.add(belt);

            // Visible rollers
            const rollerMat = new THREE.MeshStandardMaterial({ color: 0x999999, roughness: 0.3, metalness: 0.9 });
            for (let i = 0; i < 16; i++) {
                const roller = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.025, 0.025, 0.54, 12),
                    rollerMat
                );
                roller.rotation.x = Math.PI / 2;
                roller.position.set(-1.1 + i * 0.15, 0.46, 0);
                convGroup.add(roller);
            }

            convGroup.position.copy(CONVEYOR_POS);
            scene.add(convGroup);
        }

        function createPallet() {
            const palletGroup = new THREE.Group();
            const woodLight = new THREE.MeshStandardMaterial({ color: 0xC4A46B, roughness: 0.85, metalness: 0.0 });
            const woodDark = new THREE.MeshStandardMaterial({ color: 0x8B6F3A, roughness: 0.9, metalness: 0.0 });

            // Bottom boards (3 lengthwise)
            for (let i = 0; i < 3; i++) {
                const board = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.025, 0.12), woodDark);
                board.position.set(0, 0.0125, -0.4 + i * 0.4);
                board.receiveShadow = true;
                palletGroup.add(board);
            }

            // Blocks (9 blocks in 3x3)
            for (let i = 0; i < 3; i++) {
                for (let j = 0; j < 3; j++) {
                    const block = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.08, 0.1), woodDark);
                    block.position.set(-0.45 + i * 0.45, 0.065, -0.35 + j * 0.35);
                    block.castShadow = true;
                    palletGroup.add(block);
                }
            }

            // Top deck boards (7 cross boards)
            for (let i = 0; i < 7; i++) {
                const board = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.02, 1.0), woodLight);
                board.position.set(-0.52 + i * 0.175, 0.115, 0);
                board.receiveShadow = true;
                board.castShadow = true;
                palletGroup.add(board);
            }

            palletGroup.position.copy(PALLET_POS);
            palletGroup.position.y = 0;
            scene.add(palletGroup);
        }

        function createRobot() {
            robotGroup = new THREE.Group();
            robotGroup.position.copy(ROBOT_POS);

            const blueMat = new THREE.MeshStandardMaterial({ color: 0x0056A0, roughness: 0.4, metalness: 0.6 });
            const lightMat = new THREE.MeshStandardMaterial({ color: 0xDDDDDD, roughness: 0.3, metalness: 0.5 });
            const darkMat = new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.5, metalness: 0.8 });
            const orangeMat = new THREE.MeshStandardMaterial({ color: 0xF5A623, roughness: 0.4, metalness: 0.3 });

            // === BASE (fixed, J1 rotation) ===
            const baseGroup = new THREE.Group(); // J1 - rotates around Y
            joints.push(baseGroup);

            // Base pedestal
            const basePedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.40, 0.15, 32), darkMat);
            basePedestal.position.y = 0.075;
            basePedestal.castShadow = true;
            baseGroup.add(basePedestal);

            // Base body
            const baseBody = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.35, ROBOT_BASE_HEIGHT, 32), blueMat);
            baseBody.position.y = ROBOT_BASE_HEIGHT / 2 + 0.15;
            baseBody.castShadow = true;
            baseGroup.add(baseBody);

            // Yaskawa logo ring
            const logoRing = new THREE.Mesh(new THREE.TorusGeometry(0.30, 0.015, 8, 32), lightMat);
            logoRing.rotation.x = Math.PI / 2;
            logoRing.position.y = 0.30;
            baseGroup.add(logoRing);

            robotGroup.add(baseGroup);

            // === SHOULDER (J2 - rotates around Z) ===
            const shoulderGroup = new THREE.Group();
            shoulderGroup.position.y = ROBOT_BASE_HEIGHT + 0.15;
            joints.push(shoulderGroup);

            // Shoulder joint sphere
            const shoulderJoint = new THREE.Mesh(new THREE.SphereGeometry(0.18, 24, 24), darkMat);
            shoulderJoint.castShadow = true;
            shoulderGroup.add(shoulderJoint);

            // Link 1 (upper arm)
            const link1Group = new THREE.Group();
            const link1 = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, LINK1_HEIGHT, 20), blueMat);
            link1.position.y = LINK1_HEIGHT / 2;
            link1.castShadow = true;
            link1Group.add(link1);

            // Arm cover/accent
            const armCover = new THREE.Mesh(new THREE.BoxGeometry(0.10, LINK1_HEIGHT * 0.7, 0.18), lightMat);
            armCover.position.set(0.08, LINK1_HEIGHT * 0.5, 0);
            link1Group.add(armCover);

            shoulderGroup.add(link1Group);
            baseGroup.add(shoulderGroup);

            // === ELBOW (J3 - rotates around Z) ===
            const elbowGroup = new THREE.Group();
            elbowGroup.position.y = LINK1_HEIGHT;
            joints.push(elbowGroup);

            // Elbow joint
            const elbowJoint = new THREE.Mesh(new THREE.SphereGeometry(0.14, 20, 20), darkMat);
            elbowJoint.castShadow = true;
            elbowGroup.add(elbowJoint);

            // Link 2 (forearm)
            const link2Group = new THREE.Group();
            const link2 = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.11, LINK2_LENGTH, 18), blueMat);
            link2.position.y = LINK2_LENGTH / 2;
            link2.castShadow = true;
            link2Group.add(link2);

            // Forearm accent
            const forearmAccent = new THREE.Mesh(new THREE.BoxGeometry(0.08, LINK2_LENGTH * 0.6, 0.14), lightMat);
            forearmAccent.position.set(-0.06, LINK2_LENGTH * 0.4, 0);
            link2Group.add(forearmAccent);

            elbowGroup.add(link2Group);
            shoulderGroup.add(elbowGroup);

            // === WRIST PITCH (J4 - rotates around Y for twist) ===
            const wristPitchGroup = new THREE.Group();
            wristPitchGroup.position.y = LINK2_LENGTH;
            joints.push(wristPitchGroup);

            const wristJoint1 = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 16), darkMat);
            wristPitchGroup.add(wristJoint1);

            // Link 3 (wrist section)
            const link3 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, LINK3_LENGTH, 16), blueMat);
            link3.position.y = LINK3_LENGTH / 2;
            link3.castShadow = true;
            wristPitchGroup.add(link3);

            elbowGroup.add(wristPitchGroup);

            // === WRIST ROTATE (J5 - rotates around Z) ===
            const wristRotGroup = new THREE.Group();
            wristRotGroup.position.y = LINK3_LENGTH;
            joints.push(wristRotGroup);

            const wristJoint2 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.08, 16), darkMat);
            wristRotGroup.add(wristJoint2);

            wristPitchGroup.add(wristRotGroup);

            // === FLANGE (J6 - end rotation) ===
            const flangeGroup = new THREE.Group();
            flangeGroup.position.y = 0.06;
            joints.push(flangeGroup);

            const flange = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.06, 0.04, 20), lightMat);
            flangeGroup.add(flange);

            wristRotGroup.add(flangeGroup);

            // === GRIPPER (vacuum pad) ===
            gripperGroup = new THREE.Group();
            gripperGroup.position.y = -0.02;

            // Gripper mounting plate
            const mountPlate = new THREE.Mesh(new THREE.BoxGeometry(0.40, 0.03, 0.30), orangeMat);
            mountPlate.castShadow = true;
            gripperGroup.add(mountPlate);

            // Cross frame
            const crossBar1 = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.025, 0.04), darkMat);
            crossBar1.position.y = -0.03;
            gripperGroup.add(crossBar1);
            const crossBar2 = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.025, 0.28), darkMat);
            crossBar2.position.y = -0.03;
            gripperGroup.add(crossBar2);

            // Vacuum pads (4 suction cups)
            const padMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.9 });
            const padPositions = [[-0.12, -0.05, -0.08], [0.12, -0.05, -0.08], [-0.12, -0.05, 0.08], [0.12, -0.05, 0.08]];
            padPositions.forEach(p => {
                const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.03, 12), padMat);
                pad.position.set(...p);
                gripperGroup.add(pad);
                gripperPads.push(pad);
            });

            flangeGroup.add(gripperGroup);

            // Set initial pose
            setJointAngles(HOME_ANGLES);

            scene.add(robotGroup);
        }

        function setJointAngles(angles) {
            // J1: base rotation around Y
            if (joints[0]) joints[0].rotation.y = angles[0];
            // J2: shoulder pitch around Z
            if (joints[1]) joints[1].rotation.z = angles[1];
            // J3: elbow pitch around Z
            if (joints[2]) joints[2].rotation.z = angles[2];
            // J4: wrist twist around Y
            if (joints[3]) joints[3].rotation.y = angles[3];
            // J5: wrist pitch around Z
            if (joints[4]) joints[4].rotation.z = angles[4];
            // J6: flange rotation around Y
            if (joints[5]) joints[5].rotation.y = angles[5];
        }

        // Easing functions
        function easeInOutCubic(t) {
            return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        }
        function easeInOutQuad(t) {
            return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        }

        function lerpAngle(a, b, t) {
            return a + (b - a) * t;
        }

        function lerpAngles(from, to, t) {
            return from.map((a, i) => lerpAngle(a, to[i], t));
        }

        // Animate joint angles from current to target over duration (ms)
        function animateJoints(targetAngles, duration, startAngles) {
            return new Promise(resolve => {
                const start = performance.now();
                const fromAngles = startAngles || [
                    joints[0].rotation.y, joints[1].rotation.z,
                    joints[2].rotation.z, joints[3].rotation.y,
                    joints[4].rotation.z, joints[5].rotation.y
                ];
                function step(now) {
                    const elapsed = now - start;
                    const t = Math.min(elapsed / duration, 1);
                    const eased = easeInOutCubic(t);
                    const current = lerpAngles(fromAngles, targetAngles, eased);
                    setJointAngles(current);
                    if (t < 1) {
                        requestAnimationFrame(step);
                    } else {
                        setJointAngles(targetAngles);
                        resolve();
                    }
                }
                requestAnimationFrame(step);
            });
        }

        // Get world position of gripper tip
        function getGripperWorldPos() {
            const vec = new THREE.Vector3();
            gripperGroup.getWorldPosition(vec);
            return vec;
        }

        // Move a box from one world position to another with easing
        function animateBoxPosition(box, from, to, duration) {
            return new Promise(resolve => {
                const start = performance.now();
                function step(now) {
                    const elapsed = now - start;
                    const t = Math.min(elapsed / duration, 1);
                    const eased = easeInOutQuad(t);
                    box.position.lerpVectors(from, to, eased);
                    if (t < 1) {
                        requestAnimationFrame(step);
                    } else {
                        box.position.copy(to);
                        resolve();
                    }
                }
                requestAnimationFrame(step);
            });
        }

        // Compute approximate joint angles to reach a world point (simplified IK)
        function computeIK(worldTarget) {
            // Transform target to robot local space
            const localTarget = worldTarget.clone().sub(ROBOT_POS);

            // J1: base rotation (atan2 of x,z in robot base)
            const j1 = Math.atan2(localTarget.x, localTarget.z);

            // Distance in horizontal plane
            const hDist = Math.sqrt(localTarget.x * localTarget.x + localTarget.z * localTarget.z);
            const vDist = localTarget.y - (ROBOT_BASE_HEIGHT + 0.15);

            // Simple 2-link IK for shoulder + elbow
            const L1 = LINK1_HEIGHT;
            const L2 = LINK2_LENGTH + LINK3_LENGTH;
            const reach = Math.sqrt(hDist * hDist + vDist * vDist);
            const clampedReach = Math.min(reach, L1 + L2 - 0.1);

            // Law of cosines
            let cosAngle2 = (clampedReach * clampedReach - L1 * L1 - L2 * L2) / (2 * L1 * L2);
            cosAngle2 = Math.max(-1, Math.min(1, cosAngle2));
            const angle2 = Math.acos(cosAngle2);

            const alpha = Math.atan2(vDist, hDist);
            let cosAngle1 = (L1 * L1 + clampedReach * clampedReach - L2 * L2) / (2 * L1 * clampedReach);
            cosAngle1 = Math.max(-1, Math.min(1, cosAngle1));
            const angle1 = alpha + Math.acos(cosAngle1);

            // Convert to joint angles
            const j2 = -(Math.PI / 2 - angle1);
            const j3 = -(Math.PI - angle2);
            const j4 = 0;
            const j5 = -(j2 + j3); // Keep gripper pointing down
            const j6 = 0;

            return [j1, j2, j3, j4, j5, j6];
        }

        async function loadBoxData() {
            try {
                const response = await fetch('/api/pallet-data');
                palletData = await response.json();

                // Popular dropdown de modelos
                if (palletData.models && palletData.models.length > 0) {
                    const select = document.getElementById('modelSelect');
                    select.innerHTML = '';
                    palletData.models.forEach(m => {
                        const opt = document.createElement('option');
                        opt.value = m.id;
                        opt.textContent = m.name;
                        if (m.id === palletData.model_id) opt.selected = true;
                        select.appendChild(opt);
                    });
                }

                document.getElementById('status').innerHTML =
                    `Modelo: <strong>${palletData.model || 'N/A'}</strong><br>` +
                    `Caixas: <strong>${palletData.cases.length}</strong><br>` +
                    `Pronto para paletizar`;
                document.getElementById('counter').textContent =
                    `0 / ${palletData.cases.length} caixas`;

                // Pre-create box meshes (hidden)
                palletData.cases.forEach((c, i) => {
                    const w = c.sizex / 100, h = c.sizez / 100, d = c.sizey / 100;
                    const boxGeo = new THREE.BoxGeometry(w, h, d);

                    // Create cardboard-like material with edges
                    const boxMat = new THREE.MeshStandardMaterial({
                        color: 0xC8956C,
                        roughness: 0.85,
                        metalness: 0.0,
                    });
                    const box = new THREE.Mesh(boxGeo, boxMat);
                    box.castShadow = true;
                    box.receiveShadow = true;
                    box.visible = false;

                    // Add edge wireframe for box look
                    const edgeGeo = new THREE.EdgesGeometry(boxGeo);
                    const edgeMat = new THREE.LineBasicMaterial({ color: 0x8B5E3C, linewidth: 1 });
                    const edges = new THREE.LineSegments(edgeGeo, edgeMat);
                    box.add(edges);

                    scene.add(box);
                    boxes.push({ mesh: box, data: c, placed: false });
                });
            } catch (e) {
                document.getElementById('status').innerHTML =
                    '<span style="color:#ff5252;">Erro ao conectar ao backend.</span>';
            }
        }

        async function changeModel() {
            const modelId = document.getElementById('modelSelect').value;
            if (!modelId) return;

            // Limpar caixas anteriores
            boxes.forEach(b => { scene.remove(b.mesh); });
            boxes = [];
            currentBoxIndex = 0;
            animating = false;
            carriedBox = null;

            // Recarregar com novo modelo
            try {
                const response = await fetch('/api/pallet-data?model_id=' + modelId);
                palletData = await response.json();
                document.getElementById('status').innerHTML =
                    `Modelo: <strong>${palletData.model || 'N/A'}</strong><br>` +
                    `Caixas: <strong>${palletData.cases.length}</strong><br>` +
                    `Pronto para paletizar`;
                document.getElementById('counter').textContent =
                    `0 / ${palletData.cases.length} caixas`;
                document.getElementById('progress-bar').style.width = '0%';
                document.getElementById('startBtn').disabled = false;

                // Criar novas caixas
                palletData.cases.forEach((c, i) => {
                    const w = c.sizex / 100, h = c.sizez / 100, d = c.sizey / 100;
                    const boxGeo = new THREE.BoxGeometry(w, h, d);
                    const boxMat = new THREE.MeshStandardMaterial({ color: 0xC8956C, roughness: 0.85, metalness: 0.0 });
                    const box = new THREE.Mesh(boxGeo, boxMat);
                    box.castShadow = true;
                    box.receiveShadow = true;
                    box.visible = false;
                    const edgeGeo = new THREE.EdgesGeometry(boxGeo);
                    const edgeMat = new THREE.LineBasicMaterial({ color: 0x8B5E3C });
                    box.add(new THREE.LineSegments(edgeGeo, edgeMat));
                    scene.add(box);
                    boxes.push({ mesh: box, data: c, placed: false });
                });
            } catch(e) {
                document.getElementById('status').innerHTML = 'Erro ao carregar modelo.';
            }

            setJointAngles(HOME_ANGLES);
        }

        function startPalletizing() {
            if (animating || !palletData || palletData.cases.length === 0) return;
            animating = true;
            currentBoxIndex = 0;
            document.getElementById('startBtn').disabled = true;
            document.getElementById('status').innerHTML = '<strong>Paletizando...</strong>';
            runPickAndPlaceCycle();
        }

        async function runPickAndPlaceCycle() {
            if (currentBoxIndex >= boxes.length || !animating) {
                finishPalletizing();
                return;
            }

            const box = boxes[currentBoxIndex];
            const c = box.data;

            // Calculate target position on pallet
            const palletOffset = PALLET_POS.clone();
            palletOffset.y = 0.13; // top of pallet deck
            const targetX = palletOffset.x - 0.55 + c.x / 100 + c.sizex / 200;
            const targetY = palletOffset.y + c.z / 100 + c.sizez / 200;
            const targetZ = palletOffset.z - 0.45 + c.y / 100 + c.sizey / 200;
            const placePos = new THREE.Vector3(targetX, targetY, targetZ);

            // Pick position (on conveyor)
            const pickAbove = new THREE.Vector3(
                CONVEYOR_POS.x, CONVEYOR_POS.y + 1.0, CONVEYOR_POS.z
            );
            const pickPos = new THREE.Vector3(
                CONVEYOR_POS.x, CONVEYOR_POS.y + 0.55, CONVEYOR_POS.z
            );

            // Place approach (above target)
            const placeAbove = new THREE.Vector3(targetX, targetY + 0.4, targetZ);

            // Show box on conveyor
            box.mesh.visible = true;
            box.mesh.position.copy(pickPos);

            // Step 1: Move to above pick position
            const pickAboveAngles = computeIK(pickAbove);
            await animateJoints(pickAboveAngles, 600);

            // Step 2: Lower to pick
            const pickAngles = computeIK(pickPos);
            await animateJoints(pickAngles, 400);

            // Step 3: Grab (attach box to gripper conceptually)
            carriedBox = box.mesh;
            await sleep(150);

            // Step 4: Lift with box
            await animateJointsWithBox(pickAboveAngles, 500, box.mesh);

            // Step 5: Move to above place position
            const placeAboveAngles = computeIK(placeAbove);
            await animateJointsWithBox(placeAboveAngles, 700, box.mesh);

            // Step 6: Lower to place
            const placeAngles = computeIK(placePos);
            await animateJointsWithBox(placeAngles, 400, box.mesh);

            // Step 7: Release box at final position
            carriedBox = null;
            box.mesh.position.copy(placePos);
            box.placed = true;
            box.mesh.material.color.setHex(0xB8845A);
            await sleep(100);

            // Step 8: Lift away
            await animateJoints(placeAboveAngles, 350);

            // Step 9: Return home
            await animateJoints(HOME_ANGLES, 500);

            // Update UI
            currentBoxIndex++;
            const progress = (currentBoxIndex / boxes.length) * 100;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('counter').textContent =
                `${currentBoxIndex} / ${boxes.length} caixas`;
            document.getElementById('status').innerHTML =
                `<strong>Paletizando...</strong> ${currentBoxIndex}/${boxes.length}`;

            // Small pause then next cycle
            await sleep(100);
            runPickAndPlaceCycle();
        }

        // Animate joints while also moving the carried box to follow gripper
        function animateJointsWithBox(targetAngles, duration, boxMesh) {
            return new Promise(resolve => {
                const start = performance.now();
                const fromAngles = [
                    joints[0].rotation.y, joints[1].rotation.z,
                    joints[2].rotation.z, joints[3].rotation.y,
                    joints[4].rotation.z, joints[5].rotation.y
                ];
                function step(now) {
                    const elapsed = now - start;
                    const t = Math.min(elapsed / duration, 1);
                    const eased = easeInOutCubic(t);
                    const current = lerpAngles(fromAngles, targetAngles, eased);
                    setJointAngles(current);

                    // Update box position to follow gripper
                    if (boxMesh) {
                        const gripPos = getGripperWorldPos();
                        gripPos.y -= 0.05; // offset below gripper
                        boxMesh.position.copy(gripPos);
                    }

                    if (t < 1) {
                        requestAnimationFrame(step);
                    } else {
                        setJointAngles(targetAngles);
                        if (boxMesh) {
                            const gripPos = getGripperWorldPos();
                            gripPos.y -= 0.05;
                            boxMesh.position.copy(gripPos);
                        }
                        resolve();
                    }
                }
                requestAnimationFrame(step);
            });
        }

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        function finishPalletizing() {
            animating = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('status').innerHTML =
                `<span style="color:#4caf50;"><strong>&#10003; Paletização completa!</strong></span><br>` +
                `${boxes.length} caixas posicionadas`;
            document.getElementById('counter').textContent =
                `${boxes.length} / ${boxes.length} caixas - COMPLETO`;
        }

        function resetScene() {
            animating = false;
            carriedBox = null;
            currentBoxIndex = 0;

            boxes.forEach(b => {
                b.mesh.visible = false;
                b.placed = false;
                b.mesh.material.color.setHex(0xC8956C);
            });

            // Reset robot to home
            setJointAngles(HOME_ANGLES);

            document.getElementById('startBtn').disabled = false;
            document.getElementById('progress-bar').style.width = '0%';
            document.getElementById('counter').textContent =
                `0 / ${boxes.length} caixas`;
            document.getElementById('status').innerHTML =
                `Modelo: <strong>${palletData ? palletData.model : 'N/A'}</strong><br>` +
                `Caixas: <strong>${boxes.length}</strong><br>` +
                `Pronto para paletizar`;
        }

        function onResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/pallet-data')
def pallet_data():
    """Busca dados do backend SoundBox."""
    from flask import request as flask_request
    model_id = flask_request.args.get('model_id', None)

    try:
        # Buscar modelos do banco
        resp = requests.get(f'{BACKEND_URL}/api/boxes')
        if resp.status_code != 200:
            return jsonify({"cases": [], "model": "Erro", "models": []})

        models = resp.json()
        if not models:
            return jsonify({"cases": [], "model": "Sem modelos", "models": []})

        # Selecionar modelo pelo ID ou o primeiro
        if model_id:
            model = next((m for m in models if str(m['id']) == str(model_id)), models[0])
        else:
            model = models[0]

        # Calcular
        payload = {
            "pallet": {
                "sizex": model.get("pallet_sizex", 100),
                "sizey": model.get("pallet_sizey", 120),
                "sizez": model.get("pallet_sizez", 200),
                "max_weight": model.get("pallet_max_weight", 1200),
            },
            "cases": [{
                "code": model.get("code", "BOX"),
                "sizex": model.get("sizex", 60),
                "sizey": model.get("sizey", 40),
                "sizez": model.get("sizez", 20),
                "weight": model.get("weight", 5),
                "quantity": model.get("quantity", 10),
                "strength": model.get("strength", 10),
                "pallet_face": model.get("pallet_face", "xy"),
                "interlocking_type": model.get("interlocking_type", "mirror"),
            }],
            "overhang": model.get("overhang", 5),
        }

        resp = requests.post(f'{BACKEND_URL}/api/calculate', json=payload)
        if resp.status_code == 200:
            result = resp.json()
            return jsonify({
                "cases": result.get("cases", []),
                "model": model.get("name", "N/A"),
                "model_id": model.get("id"),
                "pallet": result.get("pallet", {}),
                "models": [{"id": m["id"], "name": m["name"]} for m in models],
            })

    except Exception as e:
        print(f"Erro: {e}")

    return jsonify({"cases": [], "model": "Erro de conexão", "models": []})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090, debug=False)
