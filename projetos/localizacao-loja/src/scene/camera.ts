import {ROUTE_TURN_M, T} from "../timeline";
import {Route, routeBearing, routePoint} from "./route";

// Câmera "drone": alvo no chão + distância + rumo (0 = norte) + inclinação abaixo do horizonte.
export type Rig = {tx: number; tz: number; dist: number; heading: number; pitch: number; fov: number; roll: number};

export type CameraState = {
  position: [number, number, number];
  // Euler YXZ (yaw, pitch, roll) em radianos
  rotation: [number, number, number];
  fov: number;
  near: number;
  far: number;
  dist: number;
  target: [number, number];
};

export type ScenePois = Record<string, [number, number]>;

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const smooth = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};
const smoother = (x: number) => {
  const t = clamp01(x);
  return t * t * t * (t * (t * 6 - 15) + 10);
};
const easeInOutSine = (x: number) => -(Math.cos(Math.PI * clamp01(x)) - 1) / 2;
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpLog = (a: number, b: number, t: number) => Math.exp(lerp(Math.log(a), Math.log(b), t));
const angleDiff = (a: number, b: number) => ((((b - a) % 360) + 540) % 360) - 180;
const lerpAngle = (a: number, b: number, t: number) => a + angleDiff(a, b) * t;

const blend = (a: Rig, b: Rig, w: number): Rig => ({
  tx: lerp(a.tx, b.tx, w),
  tz: lerp(a.tz, b.tz, w),
  dist: lerpLog(a.dist, b.dist, w),
  heading: lerpAngle(a.heading, b.heading, w),
  pitch: lerp(a.pitch, b.pitch, w),
  fov: lerp(a.fov, b.fov, w),
  roll: lerp(a.roll, b.roll, w),
});

// Hermite cúbico: posição na rota em função do tempo (parte e chega parado, desacelera na virada).
const hermite = (t: number, t0: number, t1: number, p0: number, p1: number, m0: number, m1: number) => {
  const dt = t1 - t0;
  const u = clamp01((t - t0) / dt);
  const u2 = u * u;
  const u3 = u2 * u;
  return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * dt * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * dt * m1;
};

export const routeProgress = (route: Route, t: number) => {
  const vTurn = 105; // m/s ao passar pela virada
  if (t <= T.routeStart) return 0;
  if (t <= T.turnAt) return hermite(t, T.routeStart, T.turnAt, 0, ROUTE_TURN_M, 0, vTurn);
  if (t <= T.arrive) return hermite(t, T.turnAt, T.arrive, ROUTE_TURN_M, route.length, vTurn, 0);
  return route.length;
};

const FOV = 58;

const descentRig = (t: number, pois: ScenePois): Rig => {
  const u = t / T.descentEnd;
  const praca = pois.praca;
  return {
    tx: lerp(praca[0] + 420, praca[0], smoother(u)),
    tz: lerp(praca[1] + 260, praca[1], smoother(u)),
    dist: lerpLog(14000, 980, easeInOutSine(u)),
    heading: lerp(-35, 18, smooth(u)),
    pitch: lerp(89.4, 61, smoother(u * 1.1 - 0.1)),
    fov: lerp(52, FOV, smooth(u)),
    roll: 0,
  };
};

const pracaRig = (t: number, pois: ScenePois): Rig => {
  const u = (t - T.descentEnd) / (T.routeStart - T.descentEnd);
  return {
    tx: pois.praca[0],
    tz: pois.praca[1],
    dist: lerpLog(980, 600, easeInOutSine(u)),
    heading: lerp(18, 8, easeInOutSine(u)),
    pitch: lerp(61, 52, easeInOutSine(u)),
    fov: FOV,
    roll: 0,
  };
};

const followRig = (t: number, route: Route): Rig => {
  const s = routeProgress(route, t);
  const [tx, tz] = routePoint(route, s + 70);
  const heading = routeBearing(route, s, 170, 340);
  // inclinação lateral proporcional à taxa de curva (inclina para dentro da curva)
  const dt = 0.25;
  const h0 = routeBearing(route, routeProgress(route, t - dt), 170, 340);
  const h1 = routeBearing(route, routeProgress(route, t + dt), 170, 340);
  const rate = angleDiff(h0, h1) / (2 * dt);
  const u = (t - T.routeStart) / (T.arrive - T.routeStart);
  return {
    tx,
    tz,
    dist: lerpLog(600, 480, smooth(u)),
    heading,
    pitch: lerp(52, 48, smooth(u)),
    fov: FOV,
    roll: Math.max(-5, Math.min(5, rate * 0.12)),
  };
};

const storeRig = (t: number, pois: ScenePois, arrivalHeading: number): Rig => {
  const u = (t - T.arrive) / (T.pullBack - T.arrive);
  const v = (t - T.pullBack) / (T.end - T.pullBack);
  const orbit = 95 * easeInOutSine(u) + 30 * smooth(v);
  return {
    tx: pois.store[0],
    tz: pois.store[1],
    dist: v > 0 ? lerpLog(250, 760, easeInOutSine(v)) : lerpLog(480, 250, easeInOutSine(u * 1.25)),
    heading: arrivalHeading + orbit,
    pitch: v > 0 ? lerp(38, 54, easeInOutSine(v)) : lerp(48, 38, easeInOutSine(u * 1.25)),
    fov: FOV,
    roll: 0,
  };
};

export const rigAt = (t: number, route: Route, pois: ScenePois): Rig => {
  const arrivalHeading = routeBearing(route, route.length, 170, 340);
  let rig: Rig;
  if (t < T.descentEnd - 0.6) {
    rig = descentRig(t, pois);
  } else if (t < T.descentEnd + 0.6) {
    rig = blend(descentRig(t, pois), pracaRig(t, pois), smooth((t - (T.descentEnd - 0.6)) / 1.2));
  } else if (t < T.routeStart - 0.5) {
    rig = pracaRig(t, pois);
  } else if (t < T.routeStart + 1.4) {
    rig = blend(pracaRig(Math.min(t, T.routeStart), pois), followRig(t, route), smooth((t - (T.routeStart - 0.5)) / 1.9));
  } else if (t < T.arrive - 1.2) {
    rig = followRig(t, route);
  } else if (t < T.arrive + 0.8) {
    rig = blend(followRig(t, route), storeRig(Math.max(t, T.arrive), pois, arrivalHeading), smooth((t - (T.arrive - 1.2)) / 2.0));
  } else {
    rig = storeRig(t, pois, arrivalHeading);
  }
  // respiração de drone: deriva lenta e determinística
  rig.heading += 0.35 * Math.sin(t * 0.71 + 1.3);
  rig.pitch += 0.22 * Math.sin(t * 0.53 + 0.4);
  rig.roll += 0.25 * Math.sin(t * 0.9 + 2.1);
  return rig;
};

const DEG = Math.PI / 180;

export const cameraFromRig = (rig: Rig): CameraState => {
  const h = rig.heading * DEG;
  const p = rig.pitch * DEG;
  const fx = Math.sin(h) * Math.cos(p);
  const fy = -Math.sin(p);
  const fz = -Math.cos(h) * Math.cos(p);
  const position: [number, number, number] = [rig.tx - fx * rig.dist, -fy * rig.dist, rig.tz - fz * rig.dist];
  const alt = position[1];
  return {
    position,
    rotation: [-p, -h, rig.roll * DEG],
    fov: rig.fov,
    near: Math.max(1.5, alt * 0.02),
    far: Math.max(30000, alt * 40),
    dist: rig.dist,
    target: [rig.tx, rig.tz],
  };
};

export const cameraAt = (t: number, route: Route, pois: ScenePois) => cameraFromRig(rigAt(t, route, pois));
