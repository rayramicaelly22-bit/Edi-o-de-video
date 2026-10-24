import React from "react";
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";
import {routeProgress} from "../scene/camera";
import {T} from "../timeline";
import {lineById, NARRATION, SCENE, wordTime} from "./data";
import {ArrowUp, Bike, Bookmark, Heart, Hospital, Paw, Pin, Roundabout, TurnLeft} from "./Icons";
import {projectAt, timeAtDistance} from "./projection";
import {COLORS, FONT} from "./theme";

const clamp = {extrapolateLeft: "clamp", extrapolateRight: "clamp"} as const;

const useTime = () => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  return {t: frame / fps, frame, fps, width, height};
};

const pop = (t: number, start: number, fps: number, damping = 13, stiffness = 170) =>
  spring({frame: Math.round((t - start) * fps), fps, config: {damping, stiffness, mass: 0.9}});

const fadeOut = (t: number, end: number, dur = 0.35) => interpolate(t, [end - dur, end], [1, 0], clamp);

const shadowText = "0 3px 0 rgba(0,0,0,0.35), 0 8px 26px rgba(0,0,0,0.55)";

// ------------------------------------------------------------------ abertura
export const Title: React.FC = () => {
  const {t, fps} = useTime();
  if (t > 4.9) return null;
  const out = interpolate(t, [4.1, 4.7], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const pill = pop(t, 0.2, fps, 14, 140);
  const line = (d: number) => spring({frame: Math.round((t - d) * fps), fps, config: {damping: 200}});
  const hl = pop(t, 0.85, fps, 11, 150);
  return (
    <AbsoluteFill style={{opacity: 1 - out, translate: `0px ${-70 * out}px`}}>
      <div style={{position: "absolute", top: 330, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", fontFamily: FONT}}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "14px 30px 14px 20px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.95)",
            color: COLORS.ink,
            fontWeight: 800,
            fontSize: 34,
            letterSpacing: 3,
            boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
            scale: pill,
            opacity: Math.min(1, pill * 1.5),
          }}
        >
          <Pin size={44} />
          PARAGOMINAS • PA
        </div>
        {[
          {text: "COMO", d: 0.42},
          {text: "CHEGAR", d: 0.55},
        ].map(({text, d}) => (
          <div key={text} style={{overflow: "hidden", marginTop: text === "COMO" ? 26 : -18, paddingBottom: 8}}>
            <div
              style={{
                color: COLORS.white,
                fontWeight: 900,
                fontSize: 168,
                lineHeight: 1,
                letterSpacing: -2,
                textShadow: shadowText,
                translate: `0px ${(1 - line(d)) * 110}%`,
              }}
            >
              {text}
            </div>
          </div>
        ))}
        <div
          style={{
            marginTop: 14,
            padding: "10px 30px",
            borderRadius: 22,
            background: COLORS.highlight,
            color: COLORS.ink,
            fontWeight: 900,
            fontSize: 64,
            letterSpacing: 1,
            rotate: "-2.5deg",
            boxShadow: "0 12px 30px rgba(0,0,0,0.35)",
            scale: hl,
          }}
        >
          NA NOSSA LOJA
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ etiqueta presa ao mapa 3D
type MapLabelProps = {
  anchor: [number, number];
  height?: number;
  start: number;
  end: number;
  kicker: string;
  title: string;
  icon: React.ReactNode;
  accent?: string;
  stem?: number;
  // "up": cartão acima do ponto, com haste vertical; "side": cartão ao lado, com linha-guia diagonal
  // (para pontos que, vistos pela câmera, ficam colados em outro elemento)
  layout?: "up" | "side";
};

export const MapLabel: React.FC<MapLabelProps> = ({anchor, height = 0, start, end, kicker, title, icon, accent = COLORS.route, stem = 120, layout = "up"}) => {
  const {t, fps, width, height: H} = useTime();
  if (t < start - 0.05 || t > end + 0.05) return null;
  const p = projectAt(t, SCENE, [anchor[0], height, anchor[1]], width, H);
  if (!p.visible) return null;
  const s = pop(t, start, fps);
  const o = fadeOut(t, end);
  const grow = interpolate(t, [start, start + 0.3], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  let attach: {x: number; y: number};
  let cardPos: React.CSSProperties;
  if (layout === "side") {
    // o lado é decidido no início e mantido: com a órbita o ponto cruza a tela, e o cartão não pode pular
    const right = projectAt(start, SCENE, [anchor[0], height, anchor[1]], width, H).x < width / 2;
    const cardW = 30 + 76 + 18 + title.length * 25 + 30; // largura aproximada do cartão, para não sair da tela
    const ax = p.x + (right ? stem : -stem);
    attach = {x: right ? Math.min(ax, width - 30 - cardW) : Math.max(ax, 30 + cardW), y: p.y + stem * 0.55};
    cardPos = {left: attach.x, top: attach.y, translate: right ? "0% -50%" : "-100% -50%", transformOrigin: right ? "0% 50%" : "100% 50%"};
  } else {
    attach = {x: p.x, y: p.y - stem};
    cardPos = {left: Math.min(width - 300, Math.max(300, p.x)), top: attach.y - 6, translate: "-50% -100%", transformOrigin: "50% 100%"};
  }
  const lx = attach.x - p.x;
  const ly = attach.y - p.y;
  const len = Math.hypot(lx, ly) * grow;
  return (
    <div style={{position: "absolute", inset: 0, opacity: o, fontFamily: FONT}}>
      <div
        style={{
          position: "absolute",
          left: p.x,
          top: p.y - 3,
          width: len,
          height: 6,
          borderRadius: 3,
          background: "#fff",
          boxShadow: "0 0 10px rgba(0,0,0,0.35)",
          transformOrigin: "0px 3px",
          rotate: `${Math.atan2(ly, lx)}rad`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: p.x - 13,
          top: p.y - 13,
          width: 26,
          height: 26,
          borderRadius: 13,
          background: accent,
          border: "5px solid #fff",
          boxShadow: "0 4px 14px rgba(0,0,0,0.45)",
          scale: s,
        }}
      />
      <div
        style={{
          position: "absolute",
          ...cardPos,
          scale: s,
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "18px 30px 18px 18px",
          borderRadius: 30,
          background: "#fff",
          boxShadow: "0 16px 40px rgba(0,0,0,0.35)",
          whiteSpace: "nowrap",
        }}
      >
        <div style={{width: 76, height: 76, borderRadius: 22, background: accent, display: "flex", alignItems: "center", justifyContent: "center"}}>{icon}</div>
        <div style={{display: "flex", flexDirection: "column"}}>
          <div style={{fontSize: 24, fontWeight: 800, letterSpacing: 2.5, color: accent, textTransform: "uppercase"}}>{kicker}</div>
          <div style={{fontSize: 44, fontWeight: 800, color: COLORS.ink, lineHeight: 1.1}}>{title}</div>
        </div>
      </div>
    </div>
  );
};

// ------------------------------------------------------------------ banner de navegação (estilo GPS)
type Step = {from: number; icon: "up" | "round" | "left" | "pin"; kicker: string; street: string};
const STEPS: Step[] = [
  {from: 0, icon: "up", kicker: "Saindo da", street: "Praça Célio Miranda"},
  {from: 330, icon: "round", kicker: "Na rotatória da", street: "PA-125"},
  {from: 560, icon: "up", kicker: "Siga pela", street: "Rua Equador"},
  {from: 950, icon: "up", kicker: "Continue na", street: "Av. Vinícius de Moraes"},
  {from: 1480, icon: "left", kicker: "Vire à esquerda na", street: "Av. Barão de Araruna"},
];
const ARRIVED: Step = {from: Infinity, icon: "pin", kicker: "Você chegou!", street: "Número 885"};

const StepIcon: React.FC<{icon: Step["icon"]}> = ({icon}) =>
  icon === "up" ? <ArrowUp size={74} /> : icon === "round" ? <Roundabout size={74} /> : icon === "left" ? <TurnLeft size={74} /> : <Pin size={74} color="#fff" hole={COLORS.pin} />;

const fmtDist = (m: number) => (m >= 995 ? `${(m / 1000).toFixed(1).replace(".", ",")} km` : `${Math.max(0, Math.round(m / 10) * 10)} m`);

export const NavBanner: React.FC = () => {
  const {t, fps} = useTime();
  const start = T.routeStart - 0.25;
  const end = T.arrive + 1.6;
  if (t < start || t > end + 0.1) return null;
  const route = SCENE.route;
  const s = routeProgress(route, t);
  const arrived = t >= T.arrive - 0.08;
  const idx = STEPS.reduce((acc, st, i) => (s >= st.from ? i : acc), 0);
  const steps = arrived ? [...STEPS, ARRIVED] : STEPS;
  const cur = arrived ? steps.length - 1 : idx;
  const curStart = arrived ? T.arrive - 0.08 : cur === 0 ? start : timeAtDistance(route, STEPS[cur].from);
  const c = interpolate(t, [curStart, curStart + 0.32], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const prev = cur > 0 ? steps[cur - 1] : null;
  const enter = pop(t, start, fps, 15, 150);
  const exit = interpolate(t, [end - 0.4, end], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const step = steps[cur];
  const textBlock = (st: Step, k: number, ty: number) => {
    const size = Math.min(50, 640 / (st.street.length * 0.62));
    return (
      <div key={k} style={{position: "absolute", left: 0, right: 0, top: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: "center", opacity: 1 - Math.abs(ty) / 40, translate: `0px ${ty}px`}}>
        <div style={{fontSize: 28, fontWeight: 700, color: arrived && st === ARRIVED ? COLORS.highlight : COLORS.muted}}>{st.kicker}</div>
        <div style={{fontSize: size, fontWeight: 800, color: "#fff", whiteSpace: "nowrap", lineHeight: 1.15}}>{st.street}</div>
      </div>
    );
  };
  const remaining = route.length - s;
  return (
    <div
      style={{
        position: "absolute",
        top: 262,
        left: 44,
        right: 44,
        height: 172,
        borderRadius: 42,
        background: COLORS.inkSoft,
        boxShadow: "0 18px 50px rgba(0,0,0,0.35)",
        display: "flex",
        alignItems: "center",
        padding: "0 30px 0 26px",
        gap: 24,
        fontFamily: FONT,
        translate: `0px ${(1 - enter) * -260 - exit * 260}px`,
        opacity: 1 - exit,
      }}
    >
      <div style={{width: 120, height: 120, borderRadius: 34, background: arrived ? COLORS.pin : COLORS.route, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, scale: 0.85 + 0.15 * c}}>
        <StepIcon icon={step.icon} />
      </div>
      <div style={{position: "relative", flex: 1, height: "100%", overflow: "hidden"}}>
        {prev && c < 1 ? textBlock(prev, 0, -40 * c) : null}
        {textBlock(step, 1, 40 * (1 - c))}
      </div>
      {!arrived ? (
        <div style={{display: "flex", flexDirection: "column", alignItems: "flex-end", flexShrink: 0, width: 170}}>
          <div style={{fontSize: 46, fontWeight: 800, color: "#fff"}}>{fmtDist(remaining)}</div>
          <div style={{fontSize: 22, fontWeight: 700, color: COLORS.muted, letterSpacing: 1}}>FALTAM</div>
        </div>
      ) : null}
    </div>
  );
};

// ------------------------------------------------------------------ legendas
export const Captions: React.FC = () => {
  const {t, fps} = useTime();
  if (t >= T.arrive - 0.35) return null;
  let active: (typeof NARRATION.lines)[number]["captions"][number] | null = null;
  for (const line of NARRATION.lines) {
    for (const cap of line.captions) {
      if (t >= cap.start - 0.06 && t < cap.end + 0.3) active = cap;
    }
  }
  if (!active) return null;
  const a = pop(t, active.start - 0.06, fps, 16, 260);
  return (
    <div style={{position: "absolute", left: 60, right: 60, top: 1440, display: "flex", justifyContent: "center", fontFamily: FONT}}>
      <div
        style={{
          padding: "14px 30px 18px",
          borderRadius: 26,
          background: "rgba(11,31,58,0.62)",
          boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
          fontSize: 62,
          fontWeight: 800,
          lineHeight: 1.15,
          textAlign: "center",
          color: "#fff",
          scale: 0.9 + 0.1 * a,
          opacity: Math.min(1, a * 1.4),
          textShadow: "0 3px 10px rgba(0,0,0,0.35)",
        }}
      >
        {active.words.map((w, i) => {
          const on = t >= w.start - 0.04 && t < w.end + 0.02;
          return (
            <span key={i} style={{color: on ? COLORS.highlight : "#fff"}}>
              {w.text}
              {i < active!.words.length - 1 ? " " : ""}
            </span>
          );
        })}
      </div>
    </div>
  );
};

// ------------------------------------------------------------------ chegada
const Star: React.FC<{size: number; color: string}> = ({size, color}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M12 0 C13 7 17 11 24 12 C17 13 13 17 12 24 C11 17 7 13 0 12 C7 11 11 7 12 0 Z" fill={color} />
  </svg>
);

const pinTopY = (dist: number) => Math.max(30, dist * 0.095) + 8;

export const ArrivalBurst: React.FC = () => {
  const {t, fps, width, height} = useTime();
  const start = T.arrive - 0.12;
  const end = T.arrive + 1.45;
  if (t < start || t > end) return null;
  const cam = projectAt(t, SCENE, [SCENE.pois.store[0], 0, SCENE.pois.store[1]], width, height);
  const top = projectAt(t, SCENE, [SCENE.pois.store[0], pinTopY(cam.dist), SCENE.pois.store[1]], width, height);
  const s = pop(t, start, fps, 9, 190);
  const o = fadeOut(t, end, 0.3);
  const cx = Math.min(width - 280, Math.max(280, top.x));
  const cy = Math.max(620, top.y - 120);
  const k = interpolate(t, [start, start + 1.1], [0, 1], {...clamp, easing: Easing.out(Easing.quad)});
  return (
    <div style={{position: "absolute", inset: 0, opacity: o, fontFamily: FONT}}>
      {Array.from({length: 14}).map((_, i) => {
        const ang = (i / 14) * Math.PI * 2 + 0.3;
        const r = 90 + 260 * k * (0.75 + 0.25 * ((i * 7) % 3));
        const size = 34 * (1 - k) + 6;
        return (
          <div key={i} style={{position: "absolute", left: cx + Math.cos(ang) * r - size / 2, top: cy + Math.sin(ang) * r * 0.8 - size / 2, rotate: `${k * 120 + i * 25}deg`}}>
            <Star size={size} color={i % 3 === 0 ? COLORS.pin : i % 3 === 1 ? COLORS.highlight : "#fff"} />
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: cx,
          top: cy,
          translate: "-50% -50%",
          rotate: "-6deg",
          scale: s,
          fontSize: 132,
          fontWeight: 900,
          color: COLORS.highlight,
          letterSpacing: -1,
          textShadow: "0 5px 0 #0b1f3a, 0 12px 34px rgba(0,0,0,0.5)",
          whiteSpace: "nowrap",
        }}
      >
        CHEGOU!
      </div>
    </div>
  );
};

// ------------------------------------------------------------------ cartão da loja
// item do cartão: entra junto com a fala e faz o cartão crescer (sem espaço vazio esperando)
const Chip: React.FC<{t: number; start: number; icon: React.ReactNode; color: string; text: React.ReactNode}> = ({t, start, icon, color, text}) => {
  const {fps} = useVideoConfig();
  const p = pop(t, start, fps, 14, 180);
  const h = 78 * interpolate(t, [start - 0.02, start + 0.28], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  if (h <= 0) return null;
  return (
    <div style={{display: "flex", alignItems: "center", gap: 18, height: h, overflow: "hidden", opacity: Math.min(1, p * 1.5), translate: `${(1 - p) * 60}px 0px`}}>
      <div style={{width: 66, height: 66, borderRadius: 20, background: color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0}}>{icon}</div>
      <div style={{fontSize: 38, fontWeight: 700, color: COLORS.ink}}>{text}</div>
    </div>
  );
};

export const StoreCard: React.FC = () => {
  const {t, fps} = useTime();
  const start = T.arrive + 0.85;
  const end = lineById("convite").start - 0.2;
  if (t < start - 0.05 || t > end + 0.05) return null;
  const p = pop(t, start, fps, 16, 140);
  const exit = interpolate(t, [end - 0.35, end], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const tHosp = start + 0.45; // o hospital acabou de ser citado ("Passou o Hospital São Paulo?")
  const tFrente = wordTime("endereco", "frente") - 0.08;
  const tLado = wordTime("endereco", "ladinho") - 0.08;
  return (
    <div
      style={{
        position: "absolute",
        left: 44,
        right: 44,
        top: 1078,
        padding: "34px 36px 26px",
        borderRadius: 46,
        background: "#fff",
        boxShadow: "0 24px 60px rgba(0,0,0,0.4)",
        fontFamily: FONT,
        translate: `0px ${(1 - p) * 420 + exit * 520}px`,
        opacity: 1 - exit,
      }}
    >
      <div style={{display: "flex", alignItems: "center", gap: 16}}>
        <Pin size={62} />
        <div>
          <div style={{fontSize: 44, fontWeight: 900, color: COLORS.ink, lineHeight: 1.05}}>Av. Barão de Araruna, 885</div>
          <div style={{fontSize: 28, fontWeight: 700, color: "#5d6f84", marginTop: 6}}>Promissão • Paragominas - PA</div>
        </div>
      </div>
      <div style={{height: 2, background: "#e6ebf1", margin: "22px 0 12px"}} />
      <Chip t={t} start={tHosp} color="#ff3b47" icon={<Hospital size={46} color="#ff3b47" />} text={<>Perto do <b style={{fontWeight: 900}}>Hospital São Paulo</b></>} />
      <Chip t={t} start={tFrente} color={COLORS.route} icon={<Bike size={44} />} text={<>Em frente à <b style={{fontWeight: 900}}>Júnior Bike</b></>} />
      <Chip t={t} start={tLado} color="#ff9f1c" icon={<Paw size={42} />} text={<>Do lado da <b style={{fontWeight: 900}}>Vila Pet</b></>} />
    </div>
  );
};

// ------------------------------------------------------------------ etiqueta "nossa loja" sobre o pin
export const StoreTag: React.FC = () => {
  const {t, fps, width, height} = useTime();
  const start = T.arrive + 1.25;
  const end = lineById("convite").start - 0.2;
  if (t < start - 0.05 || t > end + 0.05) return null;
  const base = projectAt(t, SCENE, [SCENE.pois.store[0], 0, SCENE.pois.store[1]], width, height);
  const top = projectAt(t, SCENE, [SCENE.pois.store[0], pinTopY(base.dist), SCENE.pois.store[1]], width, height);
  const s = pop(t, start, fps, 13, 170);
  const o = fadeOut(t, end);
  return (
    <div
      style={{
        position: "absolute",
        left: top.x,
        top: top.y - 18,
        translate: "-50% -100%",
        transformOrigin: "50% 100%",
        scale: s,
        opacity: o,
        padding: "12px 26px",
        borderRadius: 999,
        background: COLORS.pin,
        color: "#fff",
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: 34,
        letterSpacing: 2,
        boxShadow: "0 12px 30px rgba(0,0,0,0.35)",
        whiteSpace: "nowrap",
      }}
    >
      NOSSA LOJA • Nº 885
    </div>
  );
};

// ------------------------------------------------------------------ encerramento
export const EndCard: React.FC = () => {
  const {t, fps} = useTime();
  const start = lineById("convite").start - 0.25;
  if (t < start) return null;
  const dim = interpolate(t, [start, start + 0.6], [0, 1], clamp);
  const a = pop(t, start, fps, 12, 140);
  const b = pop(t, start + 0.25, fps, 14, 150);
  const c = pop(t, start + 0.55, fps, 15, 150);
  const d = pop(t, start + 1.1, fps, 16, 150);
  const beat = 1 + 0.08 * Math.max(0, Math.sin((t - start) * 7.5)) * Math.exp(-(t - start) * 0.4);
  return (
    <AbsoluteFill style={{fontFamily: FONT}}>
      <AbsoluteFill style={{background: "linear-gradient(180deg, rgba(11,31,58,0.15) 0%, rgba(11,31,58,0.62) 32%, rgba(11,31,58,0.72) 70%, rgba(11,31,58,0.5) 100%)", opacity: dim}} />
      <div style={{position: "absolute", top: 560, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 18}}>
        <div style={{scale: a * beat}}>
          <Heart size={130} />
        </div>
        <div style={{fontSize: 96, fontWeight: 900, color: "#fff", lineHeight: 1.02, textAlign: "center", textShadow: shadowText, scale: a, opacity: Math.min(1, a * 1.5)}}>
          Vem fazer
          <br />
          uma visita!
        </div>
        <div style={{fontSize: 54, fontWeight: 800, color: COLORS.highlight, textShadow: shadowText, scale: b, opacity: Math.min(1, b * 1.5)}}>A gente te espera</div>
        <div
          style={{
            marginTop: 26,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "18px 30px 18px 20px",
            borderRadius: 999,
            background: "#fff",
            boxShadow: "0 14px 36px rgba(0,0,0,0.35)",
            translate: `0px ${(1 - c) * 60}px`,
            opacity: Math.min(1, c * 1.4),
          }}
        >
          <Pin size={50} />
          <div style={{fontSize: 36, fontWeight: 800, color: COLORS.ink}}>Av. Barão de Araruna, 885</div>
        </div>
        <div style={{fontSize: 30, fontWeight: 700, color: "rgba(255,255,255,0.88)", opacity: Math.min(1, c * 1.4)}}>Promissão • perto do Hospital São Paulo</div>
        <div style={{marginTop: 34, display: "flex", alignItems: "center", gap: 12, fontSize: 30, fontWeight: 700, color: "#fff", opacity: Math.min(1, d * 1.4), translate: `0px ${(1 - d) * 30}px`}}>
          <Bookmark size={38} color={COLORS.highlight} />
          Salva esse vídeo pra não esquecer o caminho!
        </div>
      </div>
      <div style={{position: "absolute", left: 60, right: 60, top: 1478, textAlign: "center", fontSize: 19, fontWeight: 600, color: "rgba(255,255,255,0.7)", lineHeight: 1.35, opacity: dim}}>
        Mapa 3D: © colaboradores do OpenStreetMap, Overture Maps Foundation e Google Open Buildings.
        <br />
        Imagem de satélite: Copernicus Sentinel-2 (ESA), agosto de 2026.
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ degradês para legibilidade (e para a interface do Stories)
export const Shades: React.FC = () => {
  const {t} = useTime();
  const bottom = interpolate(t, [T.arrive - 0.6, T.arrive], [1, 0], clamp);
  return (
    <AbsoluteFill>
      <div style={{position: "absolute", top: 0, left: 0, right: 0, height: 480, background: "linear-gradient(180deg, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0) 100%)"}} />
      <div style={{position: "absolute", bottom: 0, left: 0, right: 0, height: 760, opacity: bottom, background: "linear-gradient(0deg, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0) 100%)"}} />
    </AbsoluteFill>
  );
};

// Pontos de referência ao longo do caminho
export const PRACA_LABEL = {start: T.descentEnd + 0.25, end: T.routeStart + 0.9};
export const HOSPITAL_LABEL = {start: timeAtDistance(SCENE.route, 1690), end: T.arrive - 0.2};
