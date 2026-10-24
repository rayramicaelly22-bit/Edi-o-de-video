// Exporta, para cada frame, a câmera (matriz do three.js) e os estados animados da cena.
// O render realista no Blender lê este arquivo: câmera e animações ficam idênticas às da Remotion,
// então as etiquetas do motion graphics continuam presas aos mesmos pontos do mapa.
// Uso: npx tsx scripts/export_frames.ts
import fs from "node:fs";
import path from "node:path";
import * as THREE from "three";
import {animState} from "../src/scene/animation";
import type {SceneJson} from "../src/scene/load";
import {FPS, T} from "../src/timeline";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const scene = JSON.parse(fs.readFileSync(path.join(root, "public/scene/scene.json"), "utf8")) as SceneJson;
const W = 1080;
const H = 1920;
const camera = new THREE.PerspectiveCamera();
const frames = [];
const total = Math.round(T.end * FPS);
for (let f = 0; f < total; f++) {
  const t = f / FPS;
  const a = animState(t, scene.route, scene.pois);
  camera.fov = a.cam.fov;
  camera.aspect = W / H;
  camera.near = a.cam.near;
  camera.far = a.cam.far;
  camera.position.set(...a.cam.position);
  camera.rotation.set(a.cam.rotation[0], a.cam.rotation[1], a.cam.rotation[2], "YXZ");
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld(true);
  const r = (x: number) => Math.round(x * 1e5) / 1e5;
  frames.push({
    f,
    t: r(t),
    cam: {matrixWorld: camera.matrixWorld.elements.map(r), fov: a.cam.fov, near: r(a.cam.near), far: r(a.cam.far), dist: r(a.cam.dist), target: a.cam.target.map(r)},
    routeProgress: r(a.routeProgress),
    ribbonHalfWidth: r(a.ribbonHalfWidth),
    pin: {scale: r(a.pin.scale), y: r(a.pin.y), yaw: r(a.pin.yaw)},
    storeRing: {opacity: r(a.storeRing.opacity), phase: r(a.storeRing.phase)},
    startRing: {opacity: r(a.startRing.opacity), phase: r(a.startRing.phase)},
    headGlow: {x: r(a.headGlow.x), z: r(a.headGlow.z), opacity: r(a.headGlow.opacity), size: r(a.headGlow.size)},
  });
}
fs.writeFileSync(path.join(root, "public/scene/frames.json"), JSON.stringify({fps: FPS, width: W, height: H, frames}));
console.log(`frames.json: ${frames.length} frames`);
