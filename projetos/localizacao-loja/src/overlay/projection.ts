import * as THREE from "three";
import {cameraAt, routeProgress} from "../scene/camera";
import type {Route, } from "../scene/route";
import type {SceneJson} from "../scene/load";
import {T} from "../timeline";

const camera = new THREE.PerspectiveCamera();
const v = new THREE.Vector3();

// Projeta um ponto da cena 3D (x, y, z em metros) para pixels do vídeo, com a MESMA câmera do render 3D.
export const projectAt = (
  t: number,
  scene: SceneJson,
  point: [number, number, number],
  width: number,
  height: number,
): {x: number; y: number; visible: boolean; dist: number} => {
  const cam = cameraAt(t, scene.route, scene.pois);
  camera.fov = cam.fov;
  camera.aspect = width / height;
  camera.near = cam.near;
  camera.far = cam.far;
  camera.position.set(...cam.position);
  camera.rotation.set(cam.rotation[0], cam.rotation[1], cam.rotation[2], "YXZ");
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld(true);
  v.set(...point).project(camera);
  return {
    x: ((v.x + 1) / 2) * width,
    y: ((1 - v.y) / 2) * height,
    visible: v.z < 1 && v.z > -1,
    dist: cam.dist,
  };
};

// Instante (s) em que a ponta da rota passa pela distância s (m). Busca binária na função de progresso.
export const timeAtDistance = (route: Route, s: number) => {
  let lo = T.routeStart;
  let hi = T.arrive;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (routeProgress(route, mid) < s) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
};
