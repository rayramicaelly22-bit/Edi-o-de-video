import React from "react";
import {AbsoluteFill} from "remotion";
import {Brain, Footprints, History} from "lucide-react";
import {mola, prog} from "../anim";
import {Cabecalho, Cartao, Contador, Entra, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

export const Cerebro: React.FC = () => {
  const {frame, em, fala} = useCena("cerebro");
  const l24 = fala("l24");
  const hipo = em("l24", "hipocampo");
  const dois = em("l24", "dois");
  const voltar = em("l24", "voltar");

  const brilho = prog(frame, hipo - 2, 10);
  const pulso = brilho * (0.75 + 0.25 * Math.sin((frame - hipo) / 4));

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="04 · Curiosidades" fonte="Erickson et al., PNAS, 2011" />

      {/* cérebro com o hipocampo aceso */}
      <div style={{position: "absolute", left: 150, top: 200, width: 640, height: 640, transform: `scale(${mola(frame, l24.s - 6, 14)})`}}>
        <div style={{position: "absolute", inset: 0, borderRadius: 320, background: `radial-gradient(circle, ${COR.limao}22, transparent 65%)`}} />
        <Brain size={600} color={COR.limao} strokeWidth={1.1} style={{position: "absolute", left: 20, top: 20, filter: `drop-shadow(0 0 18px ${COR.limao}77)`}} />
        <div
          style={{
            position: "absolute",
            left: 236,
            top: 380,
            width: 150,
            height: 74,
            borderRadius: "50%",
            background: `radial-gradient(ellipse, ${COR.amarelo} 0%, ${COR.amarelo}88 45%, transparent 72%)`,
            opacity: pulso,
            transform: `scale(${0.8 + 0.3 * pulso})`,
          }}
        />
        <div style={{position: "absolute", left: 161, top: 450, width: 300, opacity: brilho, display: "flex", flexDirection: "column", alignItems: "center", gap: 8}}>
          <div style={{width: 3, height: 150 * brilho, background: COR.amarelo}} />
          <span style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 32, color: COR.amarelo, background: "rgba(10,15,31,0.8)", padding: "2px 14px", borderRadius: 10}}>hipocampo</span>
        </div>
      </div>

      {/* informações à direita */}
      <Entra em={em("l24", "idosos") - 4} de="direita" style={{position: "absolute", left: 900, top: 210}}>
        <Cartao style={{display: "inline-flex", alignItems: "center", gap: 22, padding: "18px 34px 18px 18px", borderRadius: 60}}>
          <Selo cor={COR.ciano} tamanho={76}>
            <Footprints size={40} />
          </Selo>
          <span style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 38, color: COR.texto}}>
            Idosos · <span style={{color: COR.ciano}}>1 ano de caminhadas</span>
          </span>
        </Cartao>
      </Entra>

      <Entra em={dois - 4} quique style={{position: "absolute", left: 900, top: 360}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 210, lineHeight: 1, color: COR.limao, textShadow: `0 0 40px ${COR.limao}55`}}>
          <Contador ate={2} em={dois} dur={14} antes="+" depois="%" />
        </div>
        <div style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 40, color: COR.texto, marginTop: 6}}>
          de volume no hipocampo,
          <br />
          <span style={{color: COR.apagado}}>área ligada à memória</span>
        </div>
      </Entra>

      <Entra em={voltar - 4} de="direita" style={{position: "absolute", left: 900, top: 740, display: "flex", alignItems: "center", gap: 22}}>
        <History size={78} color={COR.amarelo} strokeWidth={2} style={{transform: `rotate(${-6 * Math.max(0, frame - voltar)}deg)`}} />
        <span style={{fontFamily: FONTE.titulo, fontWeight: 850, fontSize: 50, color: COR.amarelo, whiteSpace: "nowrap"}}>como voltar 1 a 2 anos no tempo</span>
      </Entra>

      <Som em={hipo - 2} arquivo="pop" volume={0.18} />
      <Som em={dois - 4} arquivo="pop" volume={0.22} />
    </AbsoluteFill>
  );
};
