import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {mola, prog} from "../anim";
import {Cabecalho, Contador, Entra, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

// Vigitel (Ministério da Saúde): adultos das capitais com 150+ min/semana de atividade no tempo livre
const ANTES = {ano: 2009, v: 30.3};
const AGORA = {ano: 2024, v: 42.3};

const Anel: React.FC<{frame: number; inicio: number}> = ({frame, inicio}) => {
  const r = 190;
  const c = 2 * Math.PI * r;
  const p = prog(frame, inicio, 30) * (AGORA.v / 100);
  return (
    <div style={{position: "relative", width: 460, height: 460}}>
      <svg width={460} height={460} style={{transform: "rotate(-90deg)"}}>
        <circle cx={230} cy={230} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={40} />
        <circle cx={230} cy={230} r={r} fill="none" stroke={COR.limao} strokeWidth={40} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - p)} style={{filter: `drop-shadow(0 0 14px ${COR.limao}88)`}} />
      </svg>
      <div style={{position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center"}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "100%", fontSize: 94, color: COR.texto}}>
          <Contador ate={AGORA.v} casas={1} em={inicio} dur={30} depois="%" />
        </div>
        <div style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 30, color: COR.apagado, letterSpacing: "0.12em"}}>EM 2024</div>
      </div>
    </div>
  );
};

export const Brasil: React.FC = () => {
  const {frame, em, fala} = useCena("brasil");
  const l15 = fala("l15");
  const l16 = fala("l16");
  const l17 = fala("l17");
  const quarenta = em("l16", "quarenta");
  const menos = em("l17", "menos");

  const pSobe = prog(frame, l16.s - 4, 22);
  const barras = prog(frame, l17.s - 4, 14);
  const ESC = 10; // px por ponto percentual
  const base = 820;

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="03 · Os dados · Brasil" fonte="Ministério da Saúde, Vigitel 2006–2024" />

      <div
        style={{
          position: "absolute",
          width: "100%",
          top: interpolate(pSobe, [0, 1], [360, 145]),
          textAlign: "center",
          opacity: mola(frame, l15.s - 6, 14),
          transform: `scale(${1 - 0.55 * pSobe})`,
          transformOrigin: "50% 0%",
        }}
      >
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "118%", fontSize: 170, color: COR.texto}}>
          E no{" "}
          <span style={{color: COR.amarelo, position: "relative", display: "inline-block"}}>
            Brasil
            <div style={{position: "absolute", left: 0, bottom: 6, width: `${100 * mola(frame, l15.s, 14)}%`, height: 14, borderRadius: 7, background: `linear-gradient(90deg, ${COR.limao}, ${COR.amarelo})`}} />
          </span>
          ?
        </div>
      </div>

      {/* anel com o percentual de 2024 */}
      <Entra em={quarenta - 8} de="escala" quique style={{position: "absolute", left: 220, top: 330}}>
        <Anel frame={frame} inicio={quarenta} />
      </Entra>

      {/* texto à direita, depois troca pelas barras */}
      <div style={{position: "absolute", left: 900, top: 380, width: 900, opacity: 1 - barras}}>
        <Entra em={quarenta + 4}>
          <div style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 66, lineHeight: 1.1, color: COR.texto}}>
            dos adultos das capitais
          </div>
          <div style={{marginTop: 16, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 42, lineHeight: 1.3, color: COR.texto}}>
            se exercitam o suficiente no <span style={{color: COR.limao}}>tempo livre</span>
          </div>
          <div style={{marginTop: 18, fontFamily: FONTE.texto, fontWeight: 500, fontSize: 28, color: COR.apagado}}>
            150 min ou mais de atividade moderada por semana
          </div>
        </Entra>
      </div>

      <div style={{position: "absolute", left: 0, top: 0, width: "100%", height: "100%", opacity: barras}}>
        {/* linha da metade */}
        <div
          style={{
            position: "absolute",
            left: 1010,
            top: base - 50 * ESC,
            width: 700,
            borderTop: `4px dashed ${frame >= menos ? COR.coral : "rgba(255,255,255,0.35)"}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 1010,
            top: base - 50 * ESC - 52,
            fontFamily: FONTE.texto,
            fontWeight: 700,
            fontSize: 30,
            color: frame >= menos ? COR.coral : COR.apagado,
            transform: `scale(${1 + 0.12 * Math.sin(Math.PI * prog(frame, menos, 12))})`,
            transformOrigin: "0% 100%",
          }}
        >
          {frame >= menos ? "metade (50%) · ainda abaixo dela" : "metade (50%)"}
        </div>
        {[
          {d: ANTES, em: em("l17", "dois"), x: 1080, cor: COR.apagado},
          {d: AGORA, em: em("l17", "Melhorou"), x: 1420, cor: COR.limao},
        ].map((b) => {
          const p = mola(frame, b.em, 15);
          const h = b.d.v * ESC * p;
          return (
            <div key={b.d.ano}>
              <div style={{position: "absolute", left: b.x, top: base - h, width: 200, height: h, borderRadius: "18px 18px 0 0", background: b.cor}} />
              <div style={{position: "absolute", left: b.x - 40, width: 280, textAlign: "center", top: base - h - 76, opacity: p,
                fontFamily: FONTE.titulo, fontWeight: 900, fontSize: 56, color: COR.texto}}>
                {b.d.v.toLocaleString("pt-BR")}%
              </div>
              <div style={{position: "absolute", left: b.x, width: 200, textAlign: "center", top: base + 14,
                fontFamily: FONTE.texto, fontWeight: 700, fontSize: 32, color: COR.apagado}}>
                {b.d.ano}
              </div>
            </div>
          );
        })}
        <div style={{position: "absolute", left: 1010, top: base, width: 700, height: 3, background: "rgba(255,255,255,0.3)"}} />
      </div>

      <Som em={quarenta - 8} arquivo="pop" volume={0.18} />
    </AbsoluteFill>
  );
};
