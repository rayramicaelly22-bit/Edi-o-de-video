import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {prog} from "../anim";
import {Entra, Pulso} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const FONTES = [
  ["OMS", "Diretrizes sobre atividade física e comportamento sedentário (2020)"],
  ["OMS", "Atividade física: fact sheet e “Investing in physical activity”"],
  ["Strain et al.", "The Lancet Global Health (2024)"],
  ["Ministério da Saúde", "Vigitel Brasil 2006–2024"],
  ["Lee et al.", "JAMA Internal Medicine (2019)"],
  ["Ding et al.", "The Lancet Public Health (2025)"],
  ["Stamatakis et al.", "Nature Medicine (2022)"],
  ["Erickson et al.", "PNAS (2011)"],
  ["Ekelund et al.", "The Lancet (2016)"],
];

export const Fontes: React.FC = () => {
  const {frame, dur} = useCena("fontes");
  const escurece = interpolate(frame, [dur - 24, dur - 2], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  return (
    <AbsoluteFill>
      <Entra em={4} de="esquerda" style={{position: "absolute", left: 160, top: 120}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 76, color: COR.texto}}>
          Fontes
        </div>
      </Entra>
      <div style={{position: "absolute", left: 160, top: 250, width: 1600, display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 70, rowGap: 26}}>
        {FONTES.map(([quem, onde], i) => (
          <Entra key={i} em={8 + i * 2} dur={14}>
            <div style={{display: "flex", gap: 14, alignItems: "baseline"}}>
              <span style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 30, color: COR.limao, whiteSpace: "nowrap"}}>{quem}</span>
              <span style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 28, color: COR.texto, opacity: 0.85}}>{onde}</span>
            </div>
          </Entra>
        ))}
      </div>
      <Entra em={30} style={{position: "absolute", left: 160, top: 800}}>
        <span style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 26, color: COR.apagado}}>
          Narração com voz gerada por IA · Trilha sonora original · Os estudos mostram associações, não promessas individuais.
        </span>
      </Entra>
      <div style={{position: "absolute", left: 160, top: 880, opacity: prog(frame, 20, 10)}}>
        <Pulso em={20} largura={1600} altura={100} batidas={5} dur={60} espessura={4} cor={COR.ciano} />
      </div>
      <AbsoluteFill style={{background: COR.fundo, opacity: escurece}} />
    </AbsoluteFill>
  );
};
