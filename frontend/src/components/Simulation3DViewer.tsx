import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Play, Pause, RotateCcw, Eye, Layers } from 'lucide-react';

export interface Simulation3DViewerProps {
  lab: string;
  tab: string;
  algorithm: string;
  data: unknown;
  height?: number;
}

const PROCESS_COLORS = [
  0x10b981, // Emerald green (P1)
  0x3b82f6, // Ocean blue (P2)
  0xa855f7, // Royal purple (P3)
  0xf59e0b, // Warm amber (P4)
  0xec4899, // Pink (P5)
  0x06b6d4, // Cyan (P6)
];

export const Simulation3DViewer: React.FC<Simulation3DViewerProps> = ({
  lab,
  tab,
  algorithm,
  data,
  height = 360,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [viewPreset, setViewPreset] = useState<'orbit' | 'top' | 'front'>('orbit');

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const rootGroupRef = useRef<THREE.Group | null>(null);
  const animFrameIdRef = useRef<number | null>(null);

  // Mouse drag orbit controls
  const isDraggingRef = useRef(false);
  const prevMousePosRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 640;
    const sceneHeight = height;

    // 1. Initialize Scene, Camera, Renderer
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / sceneHeight, 0.1, 1000);
    cameraRef.current = camera;
    camera.position.set(16, 14, 22);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current = renderer;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, sceneHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.appendChild(renderer.domElement);

    // 2. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight1.position.set(20, 30, 20);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const pointLight = new THREE.PointLight(0x6366f1, 2, 80);
    pointLight.position.set(-15, 10, -10);
    scene.add(pointLight);

    const groundGrid = new THREE.GridHelper(30, 30, 0x334155, 0x1e293b);
    groundGrid.position.y = -2;
    scene.add(groundGrid);

    // 3. Build Lab Specific 3D Models
    const rootGroup = new THREE.Group();
    rootGroupRef.current = rootGroup;
    scene.add(rootGroup);

    populate3DScene(rootGroup, lab, tab, algorithm, data);

    // 4. Animation Loop
    let lastTime = performance.now();
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = (now - lastTime) / 1000;
      lastTime = now;

      if (autoRotate && rootGroupRef.current && !isDraggingRef.current) {
        rootGroupRef.current.rotation.y += 0.4 * delta;
      }

      // Animate any pulsing elements inside the scene
      rootGroup.children.forEach((child) => {
        if (child.userData.isPulsing) {
          const s = 1 + 0.08 * Math.sin(now * 0.005);
          child.scale.set(s, s, s);
        }
        if (child.userData.isRotatingDisk) {
          child.rotation.y += 1.2 * delta;
        }
      });

      renderer.render(scene, camera);
    };
    animate();

    // 5. Handle Resize
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const newWidth = container.clientWidth || 640;
      camera.aspect = newWidth / sceneHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, sceneHeight);
    };
    window.addEventListener('resize', handleResize);

    // 6. Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      renderer.dispose();
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    };
  }, [lab, tab, algorithm, data, height]);

  // Adjust camera based on view preset
  const setCameraPreset = (preset: 'orbit' | 'top' | 'front') => {
    setViewPreset(preset);
    const camera = cameraRef.current;
    if (!camera) return;

    if (preset === 'top') {
      camera.position.set(0, 30, 0.01);
      camera.lookAt(0, 0, 0);
    } else if (preset === 'front') {
      camera.position.set(0, 4, 26);
      camera.lookAt(0, 0, 0);
    } else {
      camera.position.set(16, 14, 22);
      camera.lookAt(0, 0, 0);
    }
  };

  // Mouse Drag Handlers
  const handlePointerDown = (e: React.PointerEvent) => {
    isDraggingRef.current = true;
    prevMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDraggingRef.current || !rootGroupRef.current) return;
    const dx = e.clientX - prevMousePosRef.current.x;
    const dy = e.clientY - prevMousePosRef.current.y;
    prevMousePosRef.current = { x: e.clientX, y: e.clientY };

    rootGroupRef.current.rotation.y += dx * 0.01;
    rootGroupRef.current.rotation.x += dy * 0.01;
  };

  const handlePointerUp = () => {
    isDraggingRef.current = false;
  };

  return (
    <div className="three-simulation-card" style={{ position: 'relative', width: '100%', borderRadius: '14px', overflow: 'hidden', background: 'radial-gradient(circle at 50% 30%, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.95))', border: '1px solid var(--color-rule)' }}>
      {/* 3D Canvas Viewport */}
      <div
        ref={containerRef}
        style={{ width: '100%', height: `${height}px`, cursor: 'grab', touchAction: 'none' }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />

      {/* Floating 3D Controls Bar */}
      <div style={{ position: 'absolute', top: '12px', right: '12px', display: 'flex', gap: '6px', background: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(8px)', padding: '4px 8px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)', zIndex: 10 }}>
        <button
          type="button"
          className="button button-quiet"
          style={{ padding: '3px 8px', fontSize: '11px', height: '26px' }}
          onClick={() => setAutoRotate(!autoRotate)}
          title={autoRotate ? 'Pause 3D Rotation' : 'Resume 3D Rotation'}
        >
          {autoRotate ? <Pause size={12} /> : <Play size={12} />}
          <span>{autoRotate ? 'Pause' : 'Spin'}</span>
        </button>

        <button
          type="button"
          className={`button button-quiet ${viewPreset === 'orbit' ? 'active' : ''}`}
          style={{ padding: '3px 8px', fontSize: '11px', height: '26px' }}
          onClick={() => setCameraPreset('orbit')}
          title="3D Perspective"
        >
          <Eye size={12} /> 3D
        </button>

        <button
          type="button"
          className={`button button-quiet ${viewPreset === 'top' ? 'active' : ''}`}
          style={{ padding: '3px 8px', fontSize: '11px', height: '26px' }}
          onClick={() => setCameraPreset('top')}
          title="Top-down Ortho View"
        >
          <Layers size={12} /> Top
        </button>

        <button
          type="button"
          className="button button-quiet"
          style={{ padding: '3px 8px', fontSize: '11px', height: '26px' }}
          onClick={() => {
            if (rootGroupRef.current) {
              rootGroupRef.current.rotation.set(0, 0, 0);
            }
            setCameraPreset('orbit');
          }}
          title="Reset 3D Camera"
        >
          <RotateCcw size={12} /> Reset
        </button>
      </div>

      {/* Floating 3D Scene Badge */}
      <div style={{ position: 'absolute', bottom: '12px', left: '16px', background: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(6px)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.1)', pointerEvents: 'none' }}>
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6', display: 'inline-block' }} />
          Three.js 3D Virtual Lab: {lab} ({algorithm})
        </div>
        <div style={{ fontSize: '10.5px', color: '#94a3b8', marginTop: '2px' }}>
          Click & drag to rotate in 3D space · Real-time WebGL rendering
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------------------
// 3D Model Scene Population
// -------------------------------------------------------------------------

function populate3DScene(
  root: THREE.Group,
  lab: string,
  tab: string,
  _algorithm: string,
  rawResult: unknown
) {
  // Clear any existing children
  while (root.children.length > 0) {
    root.remove(root.children[0]);
  }

  const result = (rawResult as Record<string, unknown>) || {};

  // 1. OS CPU Scheduling (3D Gantt Execution Timeline & Process Core Blocks)
  if (tab === 'OS simulations' && lab === 'CPU Scheduling') {
    const gantt = (result.gantt_chart as Array<{ pid: number; start: number; end: number }>) || [
      { pid: 1, start: 0, end: 4 },
      { pid: 2, start: 4, end: 7 },
      { pid: 3, start: 7, end: 12 },
      { pid: 1, start: 12, end: 14 },
    ];

    const processes = (result.processes as Array<{ pid: number; waiting_time: number; turnaround_time: number }>) || [];

    // Base timeline runway
    const totalDuration = gantt.length > 0 ? gantt[gantt.length - 1].end : 14;
    const scale = 20 / Math.max(1, totalDuration);

    const runwayGeo = new THREE.BoxGeometry(24, 0.4, 4);
    const runwayMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.6, roughness: 0.3 });
    const runway = new THREE.Mesh(runwayGeo, runwayMat);
    runway.position.set(0, -1, 0);
    root.add(runway);

    // 3D Gantt blocks
    gantt.forEach((item, idx) => {
      const duration = Math.max(0.5, item.end - item.start);
      const width = duration * scale;
      const xPos = -10 + (item.start + duration / 2) * scale;
      const color = PROCESS_COLORS[(item.pid - 1) % PROCESS_COLORS.length];

      const blockGeo = new THREE.BoxGeometry(Math.max(0.4, width - 0.2), 1.6, 2.8);
      const blockMat = new THREE.MeshStandardMaterial({
        color,
        metalness: 0.2,
        roughness: 0.2,
        emissive: color,
        emissiveIntensity: 0.2,
      });
      const mesh = new THREE.Mesh(blockGeo, blockMat);
      mesh.position.set(xPos, 0, 0);
      mesh.castShadow = true;
      root.add(mesh);

      // Floating particle light above active block
      if (idx === gantt.length - 1) {
        mesh.userData.isPulsing = true;
      }
    });

    // 3D CPU Core Tower on the right
    const coreGeo = new THREE.CylinderGeometry(1.8, 2.2, 5, 16);
    const coreMat = new THREE.MeshStandardMaterial({ color: 0x4f46e5, metalness: 0.8, roughness: 0.2, emissive: 0x312e81 });
    const coreTower = new THREE.Mesh(coreGeo, coreMat);
    coreTower.position.set(13, 1, 0);
    root.add(coreTower);

    // Turnaround pillars at the back
    processes.slice(0, 5).forEach((p, idx) => {
      const pColor = PROCESS_COLORS[(p.pid - 1) % PROCESS_COLORS.length];
      const h = Math.max(1, p.turnaround_time * 0.4);
      const pilGeo = new THREE.CylinderGeometry(0.5, 0.5, h, 12);
      const pilMat = new THREE.MeshStandardMaterial({ color: pColor, roughness: 0.4 });
      const pillar = new THREE.Mesh(pilGeo, pilMat);
      pillar.position.set(-8 + idx * 3.5, -1 + h / 2, -6);
      root.add(pillar);
    });
    return;
  }

  // 2. OS Memory & Page Replacement (3D Frame Rack & Virtual Page Ingestion)
  if (tab === 'OS simulations' && lab === 'Memory & page replacement') {
    const numFrames = Number(result.num_frames || 3);
    const frameStates = (result.frame_states as Array<Array<number | null>>) || [
      [7, 0, 1],
      [2, 0, 1],
      [2, 0, 3],
      [2, 4, 3],
    ];

    const currentFrames = frameStates.length > 0 ? frameStates[frameStates.length - 1] : [7, 0, 1];

    // 3D Server Frame Rack
    const rackGeo = new THREE.BoxGeometry(16, 1.2, 8);
    const rackMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8, roughness: 0.2 });
    const rack = new THREE.Mesh(rackGeo, rackMat);
    rack.position.set(0, -1, 0);
    root.add(rack);

    // Physical Frames
    const slotSpacing = 14 / Math.max(1, numFrames);
    currentFrames.forEach((pageVal, idx) => {
      const xPos = -6 + idx * slotSpacing;

      // Slot border
      const slotGeo = new THREE.BoxGeometry(slotSpacing - 0.6, 0.4, 6);
      const slotMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.5 });
      const slot = new THREE.Mesh(slotGeo, slotMat);
      slot.position.set(xPos, -0.4, 0);
      root.add(slot);

      // Memory Page Block
      if (pageVal !== null && pageVal !== undefined && pageVal !== -1) {
        const pageColor = PROCESS_COLORS[Math.abs(Number(pageVal)) % PROCESS_COLORS.length];
        const pageGeo = new THREE.BoxGeometry(slotSpacing - 1.2, 3.2, 4.8);
        const pageMat = new THREE.MeshStandardMaterial({
          color: pageColor,
          metalness: 0.4,
          roughness: 0.2,
          emissive: pageColor,
          emissiveIntensity: 0.25,
        });
        const pageMesh = new THREE.Mesh(pageGeo, pageMat);
        pageMesh.position.set(xPos, 1.4, 0);
        pageMesh.castShadow = true;
        root.add(pageMesh);
      }
    });

    // Ingestion Laser Beam
    const laserGeo = new THREE.CylinderGeometry(0.15, 0.15, 12, 8);
    const laserMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    const laser = new THREE.Mesh(laserGeo, laserMat);
    laser.rotation.z = Math.PI / 2;
    laser.position.set(0, 5, 0);
    laser.userData.isPulsing = true;
    root.add(laser);
    return;
  }

  // 3. OS Deadlock Theory (Banker's Safe Path / RAG Network)
  if (tab === 'OS simulations' && lab === 'Deadlock theory') {
    const isSafe = result.is_safe !== false && result.deadlock_detected !== true;
    const safeSeq = (result.safe_sequence as number[]) || [0, 1, 2, 3, 4];
    const deadlocked = (result.deadlocked_processes as number[]) || [];

    // Central circular coordinator platform
    const platGeo = new THREE.CylinderGeometry(9, 10, 0.8, 32);
    const platMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.7, roughness: 0.3 });
    const platform = new THREE.Mesh(platGeo, platMat);
    platform.position.y = -1;
    root.add(platform);

    // Processes & Resources in a 3D orbit
    const count = safeSeq.length || 5;
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const x = Math.cos(angle) * 6.5;
      const z = Math.sin(angle) * 6.5;

      const isDead = deadlocked.includes(i);
      const nodeColor = isDead ? 0xef4444 : isSafe ? 0x10b981 : 0xf59e0b;

      // Process Sphere
      const procGeo = new THREE.SphereGeometry(1.2, 24, 24);
      const procMat = new THREE.MeshStandardMaterial({
        color: nodeColor,
        emissive: nodeColor,
        emissiveIntensity: 0.3,
        roughness: 0.2,
      });
      const procMesh = new THREE.Mesh(procGeo, procMat);
      procMesh.position.set(x, 1.2, z);
      procMesh.castShadow = true;
      if (isDead) procMesh.userData.isPulsing = true;
      root.add(procMesh);

      // Resource Cube in between
      const rAngle = angle + (Math.PI / count);
      const rx = Math.cos(rAngle) * 4.2;
      const rz = Math.sin(rAngle) * 4.2;

      const resGeo = new THREE.BoxGeometry(1.2, 1.2, 1.2);
      const resMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.5 });
      const resMesh = new THREE.Mesh(resGeo, resMat);
      resMesh.position.set(rx, 0.8, rz);
      root.add(resMesh);

      // Connecting 3D pipeline
      const path = new THREE.LineCurve3(new THREE.Vector3(x, 1.2, z), new THREE.Vector3(rx, 0.8, rz));
      const tubeGeo = new THREE.TubeGeometry(path, 8, 0.08, 6, false);
      const tubeMat = new THREE.MeshBasicMaterial({ color: isDead ? 0xef4444 : 0x64748b });
      const tube = new THREE.Mesh(tubeGeo, tubeMat);
      root.add(tube);
    }
    return;
  }

  // 4. OS Disk Scheduling (3D Magnetic Platter & Arm)
  if (tab === 'OS simulations' && lab === 'Disk scheduling') {
    // 3D Magnetic Platter
    const platterGeo = new THREE.CylinderGeometry(8.5, 8.5, 0.6, 48);
    const platterMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.9,
      roughness: 0.1,
    });
    const platter = new THREE.Mesh(platterGeo, platterMat);
    platter.position.set(0, -0.5, 0);
    platter.userData.isRotatingDisk = true;
    root.add(platter);

    // Spindle Hub
    const hubGeo = new THREE.CylinderGeometry(1.8, 2.0, 1.2, 24);
    const hubMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.95, roughness: 0.05 });
    const hub = new THREE.Mesh(hubGeo, hubMat);
    hub.position.set(0, 0.1, 0);
    root.add(hub);

    // Concentric Cylinder Track Rings
    [3.2, 5.0, 6.8].forEach((r) => {
      const ringGeo = new THREE.TorusGeometry(r, 0.05, 8, 48);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = -0.15;
      root.add(ring);
    });

    // Actuator Arm
    const armPivot = new THREE.Group();
    armPivot.position.set(-10, 0.4, -6);

    const baseGeo = new THREE.CylinderGeometry(1.4, 1.6, 2, 16);
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8 });
    const armBase = new THREE.Mesh(baseGeo, baseMat);
    armPivot.add(armBase);

    const armGeo = new THREE.BoxGeometry(10, 0.3, 0.8);
    const armMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.7 });
    const arm = new THREE.Mesh(armGeo, armMat);
    arm.position.set(5, 0.6, 1.5);
    arm.rotation.y = 0.35;
    armPivot.add(arm);

    // Read/Write Head emitter
    const headGeo = new THREE.SphereGeometry(0.35, 12, 12);
    const headMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.set(9.2, 0.6, 3.2);
    head.userData.isPulsing = true;
    armPivot.add(head);

    root.add(armPivot);
    return;
  }

  // 5. OS Synchronization (3D Bounded Buffer Carousel & Semaphores)
  if (tab === 'OS simulations' && lab === 'Synchronization') {
    // Conveyor Carousel
    const ringGeo = new THREE.TorusGeometry(7.5, 1.2, 16, 48);
    const ringMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.7, roughness: 0.3 });
    const conveyor = new THREE.Mesh(ringGeo, ringMat);
    conveyor.rotation.x = Math.PI / 2;
    conveyor.position.y = -0.5;
    conveyor.userData.isRotatingDisk = true;
    root.add(conveyor);

    // Buffer Item Slots & Cubes
    const slotCount = 8;
    for (let i = 0; i < slotCount; i++) {
      const angle = (i / slotCount) * Math.PI * 2;
      const bx = Math.cos(angle) * 7.5;
      const bz = Math.sin(angle) * 7.5;

      const itemGeo = new THREE.BoxGeometry(1.4, 1.4, 1.4);
      const itemMat = new THREE.MeshStandardMaterial({
        color: i % 2 === 0 ? 0x10b981 : 0xa855f7,
        emissive: i % 2 === 0 ? 0x064e3b : 0x581c87,
        roughness: 0.2,
      });
      const itemMesh = new THREE.Mesh(itemGeo, itemMat);
      itemMesh.position.set(bx, 0.8, bz);
      itemMesh.castShadow = true;
      root.add(itemMesh);
    }

    // Producer Tower (Green) on left
    const prodGeo = new THREE.CylinderGeometry(1.6, 2, 4.5, 16);
    const prodMat = new THREE.MeshStandardMaterial({ color: 0x10b981, metalness: 0.6, emissive: 0x064e3b });
    const producer = new THREE.Mesh(prodGeo, prodMat);
    producer.position.set(-11, 1.2, 0);
    root.add(producer);

    // Consumer Tower (Purple) on right
    const consGeo = new THREE.CylinderGeometry(1.6, 2, 4.5, 16);
    const consMat = new THREE.MeshStandardMaterial({ color: 0xa855f7, metalness: 0.6, emissive: 0x581c87 });
    const consumer = new THREE.Mesh(consGeo, consMat);
    consumer.position.set(11, 1.2, 0);
    root.add(consumer);

    // Floating MUTEX Lock Orb in the Center
    const lockGeo = new THREE.SphereGeometry(1.5, 24, 24);
    const lockMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, emissive: 0x1d4ed8, emissiveIntensity: 0.4 });
    const lockOrb = new THREE.Mesh(lockGeo, lockMat);
    lockOrb.position.set(0, 3.5, 0);
    lockOrb.userData.isPulsing = true;
    root.add(lockOrb);
    return;
  }

  // 6. DBMS Serializability (3D Transaction Precedence Graph)
  if (tab === 'DBMS simulations' && lab === 'Serializability') {
    const isSerializable = result.conflict_serializable !== false;
    const graph = (result.precedence_graph as Record<string, number[]>) || { '1': [2], '2': [] };
    const txNodes = Object.keys(graph);
    const totalTx = Math.max(3, txNodes.length);

    // 3D Orbital Plane
    const orbitGeo = new THREE.RingGeometry(6.8, 7.2, 48);
    const orbitMat = new THREE.MeshBasicMaterial({ color: isSerializable ? 0x10b981 : 0xef4444, side: THREE.DoubleSide });
    const orbit = new THREE.Mesh(orbitGeo, orbitMat);
    orbit.rotation.x = Math.PI / 2;
    orbit.position.y = -1;
    root.add(orbit);

    // Transaction Spheres in 3D
    txNodes.forEach((tId, idx) => {
      const angle = (idx / totalTx) * Math.PI * 2;
      const x = Math.cos(angle) * 7;
      const z = Math.sin(angle) * 7;

      const tColor = PROCESS_COLORS[idx % PROCESS_COLORS.length];
      const sphGeo = new THREE.SphereGeometry(1.5, 24, 24);
      const sphMat = new THREE.MeshStandardMaterial({
        color: tColor,
        emissive: tColor,
        emissiveIntensity: 0.3,
        roughness: 0.2,
      });
      const tMesh = new THREE.Mesh(sphGeo, sphMat);
      tMesh.position.set(x, 1, z);
      root.add(tMesh);

      // Draw directed conflict arcs to target transactions
      const targets = graph[tId] || [];
      targets.forEach((targetId) => {
        const targetIdx = txNodes.indexOf(String(targetId));
        if (targetIdx !== -1) {
          const tAngle = (targetIdx / totalTx) * Math.PI * 2;
          const tx = Math.cos(tAngle) * 7;
          const tz = Math.sin(tAngle) * 7;

          const midX = (x + tx) / 2;
          const midZ = (z + tz) / 2;
          const midY = 3.5;

          const curve = new THREE.QuadraticBezierCurve3(
            new THREE.Vector3(x, 1, z),
            new THREE.Vector3(midX, midY, midZ),
            new THREE.Vector3(tx, 1, tz)
          );

          const arcGeo = new THREE.TubeGeometry(curve, 16, 0.12, 8, false);
          const arcMat = new THREE.MeshBasicMaterial({ color: isSerializable ? 0x38bdf8 : 0xef4444 });
          const arc = new THREE.Mesh(arcGeo, arcMat);
          root.add(arc);
        }
      });
    });

    if (!isSerializable) {
      // Pulsing conflict cycle warning ring in center
      const cycleTorus = new THREE.TorusGeometry(3.5, 0.3, 16, 32);
      const cycleMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
      const cycleMesh = new THREE.Mesh(cycleTorus, cycleMat);
      cycleMesh.rotation.x = Math.PI / 2;
      cycleMesh.position.y = 1;
      cycleMesh.userData.isPulsing = true;
      root.add(cycleMesh);
    }
    return;
  }

  // 7. DBMS WAL Recovery (3D ARIES Log Stream & Data Page Replay)
  if (tab === 'DBMS simulations' && lab === 'WAL recovery') {
    const committed = (result.committed_transactions as number[]) || [2];
    const undone = (result.undone_transactions as number[]) || [1];

    // Left Page: Pre-Crash Dirty Page
    const page1Geo = new THREE.BoxGeometry(6, 0.4, 8);
    const page1Mat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.3 });
    const p1 = new THREE.Mesh(page1Geo, page1Mat);
    p1.position.set(-8, 0, 0);
    root.add(p1);

    // Right Page: Recovered Consistent Page
    const page2Geo = new THREE.BoxGeometry(6, 0.4, 8);
    const page2Mat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.3 });
    const p2 = new THREE.Mesh(page2Geo, page2Mat);
    p2.position.set(8, 0, 0);
    root.add(p2);

    // Central 3D WAL Log Stack Tower
    const stackCount = Math.max(4, committed.length + undone.length + 2);
    for (let i = 0; i < stackCount; i++) {
      const isCommit = i >= stackCount - Math.max(1, committed.length);
      const logGeo = new THREE.BoxGeometry(4.5, 0.7, 3);
      const logMat = new THREE.MeshStandardMaterial({
        color: isCommit ? 0x10b981 : 0x3b82f6,
        emissive: isCommit ? 0x059669 : 0x1d4ed8,
        emissiveIntensity: 0.25,
      });
      const logBlock = new THREE.Mesh(logGeo, logMat);
      logBlock.position.set(0, -0.5 + i * 1.1, 0);
      logBlock.castShadow = true;
      root.add(logBlock);
    }

    // Laser Redo Beam (Green) to right page
    const redoCurve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(0, 4, 0),
      new THREE.Vector3(4, 5, 0),
      new THREE.Vector3(8, 1, 0)
    );
    const redoGeo = new THREE.TubeGeometry(redoCurve, 12, 0.12, 8, false);
    const redoMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    const redoBeam = new THREE.Mesh(redoGeo, redoMat);
    redoBeam.userData.isPulsing = true;
    root.add(redoBeam);

    // Undo Return Arc (Red) on left page
    if (undone.length > 0) {
      const undoCurve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(0, 1.5, 0),
        new THREE.Vector3(-4, 3.5, 0),
        new THREE.Vector3(-8, 1, 0)
      );
      const undoGeo = new THREE.TubeGeometry(undoCurve, 12, 0.12, 8, false);
      const undoMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
      const undoBeam = new THREE.Mesh(undoGeo, undoMat);
      root.add(undoBeam);
    }
    return;
  }

  // 8. DBMS Strict 2PL & Deadlocks (3D Lock Chambers & Dependency Threads)
  if (tab === 'DBMS simulations' && lab === 'Strict 2PL & Deadlocks') {
    const hasDeadlock = result.deadlock_detected !== false;

    // Database Object Chambers
    [-5, 5].forEach((xPos, idx) => {
      const chamberGeo = new THREE.BoxGeometry(3.5, 3.5, 3.5);
      const chamberMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        metalness: 0.6,
        roughness: 0.2,
      });
      const chamber = new THREE.Mesh(chamberGeo, chamberMat);
      chamber.position.set(xPos, 1.5, 0);
      root.add(chamber);

      // Floating Lock Token above chamber
      const lockTokenGeo = new THREE.OctahedronGeometry(1.0);
      const lockTokenMat = new THREE.MeshStandardMaterial({
        color: idx === 0 ? 0xef4444 : 0x3b82f6,
        emissive: idx === 0 ? 0xb91c1c : 0x1d4ed8,
        emissiveIntensity: 0.35,
      });
      const lockToken = new THREE.Mesh(lockTokenGeo, lockTokenMat);
      lockToken.position.set(xPos, 4.2, 0);
      lockToken.userData.isPulsing = true;
      root.add(lockToken);
    });

    // Transaction Orbs (T1 and T2)
    const t1Geo = new THREE.SphereGeometry(1.4, 24, 24);
    const t1Mat = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x059669 });
    const t1 = new THREE.Mesh(t1Geo, t1Mat);
    t1.position.set(0, 1.5, 6);
    root.add(t1);

    const t2Geo = new THREE.SphereGeometry(1.4, 24, 24);
    const t2Mat = new THREE.MeshStandardMaterial({ color: 0xa855f7, emissive: 0x6b21a8 });
    const t2 = new THREE.Mesh(t2Geo, t2Mat);
    t2.position.set(0, 1.5, -6);
    root.add(t2);

    // Cross-connecting lock hold and wait arcs
    const arc1 = new THREE.LineCurve3(new THREE.Vector3(0, 1.5, 6), new THREE.Vector3(-5, 1.5, 0));
    const arcGeo1 = new THREE.TubeGeometry(arc1, 8, 0.1, 6, false);
    const arcMat1 = new THREE.MeshBasicMaterial({ color: hasDeadlock ? 0xef4444 : 0x10b981 });
    root.add(new THREE.Mesh(arcGeo1, arcMat1));

    const arc2 = new THREE.LineCurve3(new THREE.Vector3(0, 1.5, -6), new THREE.Vector3(5, 1.5, 0));
    const arcGeo2 = new THREE.TubeGeometry(arc2, 8, 0.1, 6, false);
    const arcMat2 = new THREE.MeshBasicMaterial({ color: hasDeadlock ? 0xef4444 : 0xa855f7 });
    root.add(new THREE.Mesh(arcGeo2, arcMat2));

    if (hasDeadlock) {
      // Warning cycle rings between T1 and T2
      const cyclePath = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(0, 3, 6),
        new THREE.Vector3(6, 4, 0),
        new THREE.Vector3(0, 3, -6)
      );
      const cycleGeo = new THREE.TubeGeometry(cyclePath, 16, 0.15, 8, false);
      const cycleMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
      const cycle = new THREE.Mesh(cycleGeo, cycleMat);
      cycle.userData.isPulsing = true;
      root.add(cycle);
    }
    return;
  }

  // Default fallback 3D platform with pulsing sphere
  const fallbackGeo = new THREE.SphereGeometry(3, 32, 32);
  const fallbackMat = new THREE.MeshStandardMaterial({ color: 0x6366f1, emissive: 0x4338ca, roughness: 0.3 });
  const fallbackMesh = new THREE.Mesh(fallbackGeo, fallbackMat);
  fallbackMesh.position.set(0, 2, 0);
  fallbackMesh.userData.isPulsing = true;
  root.add(fallbackMesh);
}
