// Linha do tempo do vídeo (segundos). Fonte única para câmera 3D, motion graphics e áudio.
// Os valores ficam em timeline.json porque scripts/narration.py ajusta o fim do vídeo à narração.
import timeline from "./timeline.json";

export const FPS = timeline.fps;

export const T = {
  // A: descida do alto até o centro
  descentEnd: timeline.descentEnd,
  // B: sobrevoo da Praça Célio Miranda; C: segue a rota até a virada na Barão de Araruna e até a loja
  routeStart: timeline.routeStart,
  turnAt: timeline.turnAt,
  arrive: timeline.arrive,
  // D: órbita na loja; E: afastamento final
  pullBack: timeline.pullBack,
  end: timeline.end,
};

// Distância ao longo da rota (m) da virada na Barão de Araruna (scene.json -> route.steps)
export const ROUTE_TURN_M = 1645.2;
