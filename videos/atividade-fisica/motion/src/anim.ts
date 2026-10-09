import {Easing, interpolate, spring} from "remotion";
import {FPS} from "./tema";

const SUAVE = Easing.bezier(0.16, 1, 0.3, 1);
const ACELERA = Easing.bezier(0.7, 0, 0.84, 0);
const travar = {extrapolateLeft: "clamp", extrapolateRight: "clamp"} as const;

// 0 -> 1 a partir do quadro `inicio`
export const prog = (frame: number, inicio: number, dur = 18, easing = SUAVE) =>
  interpolate(frame, [inicio, inicio + dur], [0, 1], {easing, ...travar});

// 1 -> 0 a partir do quadro `inicio` (saída)
export const some = (frame: number, inicio: number, dur = 12) =>
  1 - interpolate(frame, [inicio, inicio + dur], [0, 1], {easing: ACELERA, ...travar});

// mola com um leve "quique"
export const mola = (frame: number, inicio: number, damping = 13) =>
  spring({frame: frame - inicio, fps: FPS, config: {damping, mass: 0.7, stiffness: 150}});

export const mapa = (v: number, de: [number, number], para: [number, number]) =>
  interpolate(v, de, para, travar);

// formatação de número em pt-BR
export const num = (v: number, casas = 0) =>
  v.toLocaleString("pt-BR", {minimumFractionDigits: casas, maximumFractionDigits: casas});
