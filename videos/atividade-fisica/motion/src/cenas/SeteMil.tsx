import React from "react";
import {AbsoluteFill, Easing, interpolate} from "remotion";
import {Footprints, FlaskConical} from "lucide-react";
import {mola, prog} from "../anim";
import {Cabecalho, Contador, Entra, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const X0 = 200;
const LARG = 1520;
const xPassos = (p: number) => X0 + (p / 10000) * LARG;

export const SeteMil: React.FC = () => {
  const {frame, em, fala} = useCena("setemil");
  const l21 = fala("l21");
  const estudo = em("l21", "Em");
  const quem = em("l21", "quem");
  const sete = em("l21", "sete");
  const quarenta = em("l21", "quarenta");

  const anda = interpolate(frame, [sete, sete + 26], [2000, 7000], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const marcador = mola(frame, quem - 4, 12);
  const yTrilho = 690;

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="04 · Curiosidades" fonte="Ding et al., The Lancet Public Health, 2025" />

      <Entra em={l21.s - 4} de="esquerda" style={{position: "absolute", left: 160, top: 170, display: "flex", alignItems: "center", gap: 24}}>
        <FlaskConical size={84} color={COR.ciano} strokeWidth={1.8} />
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 92, color: COR.texto}}>E a ciência?</div>
      </Entra>
      <Entra em={estudo} de="esquerda" style={{position: "absolute", left: 168, top: 300}}>
        <div style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 36, color: COR.apagado}}>
          Estudo de 2025 · mais de 160 mil pessoas
        </div>
      </Entra>

      {/* trilho de passos */}
      <div style={{opacity: prog(frame, estudo + 4, 14)}}>
        <div style={{position: "absolute", left: X0, top: yTrilho, width: LARG, height: 24, borderRadius: 12, background: "rgba(255,255,255,0.09)"}} />
        <div
          style={{
            position: "absolute",
            left: xPassos(2000),
            top: yTrilho,
            width: xPassos(anda) - xPassos(2000),
            height: 24,
            borderRadius: 12,
            background: `linear-gradient(90deg, ${COR.limao}66, ${COR.limao})`,
            boxShadow: `0 0 24px ${COR.limao}66`,
          }}
        />
        {[
          {p: 2000, nota: ""},
          {p: 7000, nota: ""},
          {p: 10000, nota: "a meta do marketing"},
        ].map((m) => (
          <div key={m.p} style={{position: "absolute", left: xPassos(m.p) - 150, width: 300, top: yTrilho + 34, textAlign: "center"}}>
            <div style={{margin: "0 auto", width: 4, height: 30, background: "rgba(255,255,255,0.35)", marginBottom: 14}} />
            <div style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 46, color: m.p === 7000 && frame >= sete + 20 ? COR.limao : COR.texto}}>
              {m.p.toLocaleString("pt-BR")}
            </div>
            {m.nota ? <div style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 26, color: COR.apagado}}>{m.nota}</div> : null}
          </div>
        ))}
        {/* marcador que anda */}
        <div
          style={{
            position: "absolute",
            left: xPassos(anda) - 42,
            top: yTrilho - 30,
            width: 84,
            height: 84,
            borderRadius: 42,
            background: COR.limao,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transform: `scale(${marcador})`,
            boxShadow: `0 0 40px ${COR.limao}88`,
          }}
        >
          <Footprints size={46} color={COR.fundo} strokeWidth={2.4} style={{transform: `rotate(${Math.sin(frame / 3) * 8}deg)`}} />
        </div>
        <Entra em={quem} style={{position: "absolute", left: xPassos(2000) - 200, top: yTrilho - 120, width: 400, textAlign: "center"}}>
          <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 30, color: COR.apagado}}>passos por dia</span>
        </Entra>
      </div>

      {/* resultado */}
      <Entra em={quarenta - 4} quique dist={60} style={{position: "absolute", left: xPassos(7000) - 380, top: 250, width: 760, textAlign: "center"}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 200, lineHeight: 1, color: COR.limao, textShadow: `0 0 40px ${COR.limao}55`}}>
          <Contador ate={47} em={quarenta} dur={20} antes="−" depois="%" />
        </div>
        <div style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 40, color: COR.texto}}>de risco de morte</div>
        <div style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 28, color: COR.apagado, marginTop: 4}}>comparado a 2.000 passos por dia</div>
      </Entra>

      <Som em={quarenta - 4} arquivo="pop" volume={0.22} />
      <Som em={sete - 4} arquivo="whoosh" volume={0.15} />
    </AbsoluteFill>
  );
};
