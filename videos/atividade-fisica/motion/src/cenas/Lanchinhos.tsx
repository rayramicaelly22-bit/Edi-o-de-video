import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {Zap} from "lucide-react";
import {mola, prog} from "../anim";
import {Cabecalho, Contador, Destaque, Entra, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

// escada com uma bolinha subindo degrau por degrau
const Escada: React.FC<{frame: number; inicio: number}> = ({frame, inicio}) => {
  const DEG = 5;
  const L = 112;
  const A = 52;
  let d = `M 0 ${DEG * A}`;
  for (let i = 0; i < DEG; i++) d += ` L ${i * L} ${(DEG - i - 1) * A} L ${(i + 1) * L} ${(DEG - i - 1) * A}`;
  const passo = interpolate(frame, [inicio, inicio + 36], [0, DEG - 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const i = Math.floor(passo);
  const f = passo - i;
  const x = (i + f) * L + L / 2;
  const y = (DEG - 1 - i - f) * A - 34 - Math.sin(Math.PI * f) * 46;
  const comp = 1600;
  return (
    <svg width={DEG * L} height={DEG * A + 10} style={{overflow: "visible"}}>
      <path d={d} fill="none" stroke={COR.texto} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round"
        strokeDasharray={comp} strokeDashoffset={comp * (1 - prog(frame, inicio - 14, 18))} opacity={0.85} />
      <circle cx={x} cy={y} r={24} fill={COR.limao} opacity={prog(frame, inicio - 4, 6)} style={{filter: `drop-shadow(0 0 14px ${COR.limao})`}} />
    </svg>
  );
};

export const Lanchinhos: React.FC = () => {
  const {frame, em, fala} = useCena("lanchinhos");
  const l22 = fala("l22");
  const l23 = fala("l23");
  const tres = em("l23", "três");
  const escada = em("l23", "subir");
  const quarenta = em("l23", "quarenta");

  const pSobe = prog(frame, l23.s - 4, 22);

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="04 · Curiosidades" fonte="Stamatakis et al., Nature Medicine, 2022" />

      <div
        style={{
          position: "absolute",
          width: "100%",
          top: interpolate(pSobe, [0, 1], [330, 150]),
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 30,
          opacity: mola(frame, l22.s - 6, 14),
          transform: `scale(${1 - 0.45 * pSobe})`,
          transformOrigin: "50% 0%",
        }}
      >
        <Zap size={150} color={COR.amarelo} fill={COR.amarelo} style={{filter: `drop-shadow(0 0 30px ${COR.amarelo}99)`, transform: `rotate(${Math.sin(frame / 5) * 5}deg)`}} />
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 120, lineHeight: 1.05, color: COR.texto}}>
          Até <Destaque>lanchinhos</Destaque>
          <br />
          de exercício contam
        </div>
      </div>

      <Entra em={l23.s} de="esquerda" style={{position: "absolute", left: 180, top: 340}}>
        <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 34, color: COR.apagado}}>Em quem não treinava:</span>
      </Entra>

      {/* 3 explosões de 1–2 min */}
      <div style={{position: "absolute", left: 180, top: 410, display: "flex", gap: 34}}>
        {[0, 1, 2].map((i) => (
          <Entra key={i} em={tres - 2 + i * 6} de="escala" quique>
            <div style={{display: "flex", flexDirection: "column", alignItems: "center", gap: 12}}>
              <Selo cor={COR.amarelo} tamanho={150}>
                <Zap size={70} fill={COR.amarelo} />
              </Selo>
              <span style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 40, color: COR.texto}}>1–2 min</span>
            </div>
          </Entra>
        ))}
      </div>
      <Entra em={tres + 18} style={{position: "absolute", left: 180, top: 650}}>
        <span style={{fontFamily: FONTE.titulo, fontWeight: 900, fontSize: 56, color: COR.amarelo}}>3× por dia</span>
      </Entra>

      {/* escada */}
      <div style={{position: "absolute", left: 640, top: 600, opacity: prog(frame, escada - 16, 10)}}>
        <Escada frame={frame} inicio={escada} />
        <div style={{marginTop: 14, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 30, color: COR.apagado, textAlign: "right"}}>ex.: subir escada rápido</div>
      </div>

      {/* resultado */}
      <Entra em={quarenta - 4} quique dist={60} style={{position: "absolute", left: 1260, top: 380, width: 560, textAlign: "center"}}>
        <div style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 40, color: COR.apagado}}>até</div>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 190, lineHeight: 1, color: COR.limao, textShadow: `0 0 40px ${COR.limao}55`}}>
          <Contador ate={40} em={quarenta} dur={20} antes="−" depois="%" />
        </div>
        <div style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 40, color: COR.texto}}>de risco de morte</div>
      </Entra>

      {[0, 1, 2].map((i) => (
        <Som key={i} em={tres - 2 + i * 6} arquivo="pop" volume={0.18} />
      ))}
      <Som em={quarenta - 4} arquivo="pop" volume={0.22} />
    </AbsoluteFill>
  );
};
