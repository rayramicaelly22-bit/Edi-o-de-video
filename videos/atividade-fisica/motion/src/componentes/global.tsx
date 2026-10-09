import React from "react";
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from "remotion";
import {prog} from "../anim";
import {COR, FONTE, FPS, H, W} from "../tema";
import {TL} from "../tl";

// fundo que fica por baixo de todas as cenas: manchas de luz, grade de pontos e vinheta
export const Fundo: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const mancha = (cor: string, x: number, y: number, r: number, o: number): React.CSSProperties => ({
    position: "absolute",
    left: x - r,
    top: y - r,
    width: r * 2,
    height: r * 2,
    borderRadius: r,
    background: `radial-gradient(circle, ${cor} 0%, transparent 65%)`,
    opacity: o,
  });
  return (
    <AbsoluteFill style={{background: COR.fundo, overflow: "hidden"}}>
      <div style={mancha(COR.limao, 300 + 140 * Math.sin(t / 7), 240 + 90 * Math.cos(t / 9), 620, 0.11)} />
      <div style={mancha(COR.ciano, 1600 + 160 * Math.cos(t / 8), 820 + 100 * Math.sin(t / 6), 700, 0.12)} />
      <div style={mancha(COR.coral, 1500 + 120 * Math.sin(t / 10), 120 + 60 * Math.cos(t / 7), 420, 0.06)} />
      <AbsoluteFill
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.07) 1.6px, transparent 1.6px)",
          backgroundSize: "44px 44px",
          backgroundPosition: `${(t * 6) % 44}px ${(t * 3) % 44}px`,
        }}
      />
      <AbsoluteFill style={{background: "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.55) 100%)"}} />
    </AbsoluteFill>
  );
};

// transição entre cenas: painel inclinado com borda limão que cruza a tela
// (cobre a tela inteira no quadro do corte)
export const Cortina: React.FC<{dur: number}> = ({dur}) => {
  const frame = useCurrentFrame();
  const larg = 2700;
  const x = interpolate(frame, [0, dur], [-larg - 200, W + 200], {easing: Easing.inOut(Easing.cubic)});
  return (
    <AbsoluteFill style={{overflow: "hidden", pointerEvents: "none"}}>
      <div
        style={{
          position: "absolute",
          top: -200,
          left: x,
          width: larg,
          height: H + 400,
          transform: "skewX(-14deg)",
          background: COR.painel,
          display: "flex",
          justifyContent: "flex-end",
        }}
      >
        <div style={{width: 26, height: "100%", background: COR.ciano, marginRight: 30}} />
        <div style={{width: 70, height: "100%", background: COR.limao}} />
      </div>
    </AbsoluteFill>
  );
};

// legendas na parte de baixo, em blocos curtos sincronizados com a narração
export const Legendas: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const ls = TL.legendas;
  const i = ls.findIndex((l, k) => {
    const prox = ls[k + 1];
    // estica o bloco até o próximo quando a pausa é curta, para não piscar
    const fim = prox && prox.s - l.e < 0.7 ? prox.s : l.e + 0.25;
    return t >= l.s - 0.05 && t < fim;
  });
  if (i < 0) return null;
  const l = ls[i];
  const p = prog(frame, Math.round((l.s - 0.05) * FPS), 5);
  return (
    <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center", paddingBottom: 44}}>
      <div
        style={{
          opacity: p,
          transform: `translateY(${(1 - p) * 8}px)`,
          maxWidth: 1500,
          padding: "12px 28px 14px",
          borderRadius: 16,
          background: "rgba(6,10,22,0.78)",
          border: "1px solid rgba(255,255,255,0.06)",
          color: COR.texto,
          fontFamily: FONTE.texto,
          fontWeight: 600,
          fontSize: 38,
          lineHeight: 1.25,
          textAlign: "center",
        }}
      >
        {l.texto}
      </div>
    </AbsoluteFill>
  );
};
