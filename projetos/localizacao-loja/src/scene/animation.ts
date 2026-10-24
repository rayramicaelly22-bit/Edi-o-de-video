import {T} from "../timeline";
import {cameraAt, routeProgress, type ScenePois} from "./camera";
import {routePoint, type Route} from "./route";

// Estado animado da cena em função do tempo — compartilhado pelo render WebGL (World.tsx)
// e pelo exportador para o Blender (scripts/export_frames.ts).
export const animState = (t: number, route: Route, pois: ScenePois) => {
  const cam = cameraAt(t, route, pois);
  const s = routeProgress(route, t);
  const halfWidth = Math.max(4.2, cam.dist * 0.0105);

  // pin da loja: cai com um quique quando a rota começa, mantém tamanho legível de longe
  const store = pois.store;
  const pinH = Math.max(30, cam.dist * 0.095);
  const drop = Math.min(1, Math.max(0, (t - (T.routeStart + 0.2)) / 0.8));
  const easeOutBack = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
  const pop = 1 + 0.18 * Math.exp(-Math.pow((t - T.arrive) / 0.35, 2));
  const pinScale = pinH * (drop <= 0 ? 0 : easeOutBack(drop)) * pop;
  const pinY = 3 + pinH * 0.07 * Math.sin(t * 2.4) + (1 - Math.min(1, drop * 1.4)) * pinH * 2;
  const pinYaw = Math.atan2(cam.position[0] - store[0], cam.position[2] - store[1]);

  // anéis: na praça enquanto a narração fala do centro, na loja a partir da chegada
  const inStart = Math.min(1, Math.max(0, (t - (T.descentEnd - 0.6)) / 0.6));
  const outStart = Math.min(1, Math.max(0, (T.routeStart + 2.0 - t) / 1.0));
  const head = routePoint(route, s);
  const headOn = Math.min(1, Math.max(0, (t - T.routeStart) / 0.4)) * Math.min(1, Math.max(0, (T.arrive + 0.3 - t) / 0.5));

  return {
    cam,
    routeProgress: s,
    ribbonHalfWidth: halfWidth,
    pin: {scale: pinScale, y: pinY, yaw: pinYaw},
    storeRing: {opacity: Math.min(1, Math.max(0, (t - (T.arrive - 1.0)) / 1.0)), phase: (t * 0.45) % 1},
    startRing: {opacity: inStart * outStart, phase: (t * 0.6) % 1},
    headGlow: {x: head[0], z: head[1], opacity: headOn, size: halfWidth * 7},
  };
};
