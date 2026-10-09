import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {Globe, User} from "lucide-react";
import {mola, prog, some} from "../anim";
import {Cabecalho, Contador, Destaque, Entra, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

// 31 de 100 pessoas, numa ordem embaralhada fixa
const DESTACADOS = (() => {
  const idx = Array.from({length: 100}, (_, i) => i);
  let semente = 42;
  for (let i = idx.length - 1; i > 0; i--) {
    semente = (semente * 1103515245 + 12345) % 2147483648;
    const j = semente % (i + 1);
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx.slice(0, 31);
})();

// série da OMS / Lancet Global Health (2024): % de adultos com atividade insuficiente
const SERIE = [
  {ano: 2000, v: 23.4},
  {ano: 2010, v: 26.4},
  {ano: 2022, v: 31.3},
  {ano: 2030, v: 35},
];

const Grafico: React.FC<{frame: number; inicio: number; projecao: number}> = ({frame, inicio, projecao}) => {
  const L = 640;
  const A = 420;
  const x = (ano: number) => 60 + ((ano - 2000) / 30) * (L - 60);
  const y = (v: number) => A - ((v - 20) / 16) * A;
  const pts = SERIE.map((p) => ({...p, x: x(p.ano), y: y(p.v)}));
  const solido = pts.slice(0, 3);
  const linha = solido.map((p, i) => `${i ? "L" : "M"} ${p.x} ${p.y}`).join(" ");
  const comp = 900;
  const p1 = prog(frame, inicio, 26);
  const p2 = prog(frame, projecao, 16);
  return (
    <svg width={L + 120} height={A + 110} style={{overflow: "visible"}}>
      {[20, 25, 30, 35].map((v) => (
        <g key={v}>
          <line x1={0} x2={L} y1={y(v)} y2={y(v)} stroke="rgba(255,255,255,0.08)" strokeWidth={2} />
          <text x={-18} y={y(v) + 9} textAnchor="end" fill={COR.apagado} style={{fontFamily: FONTE.texto, fontSize: 24, fontWeight: 600}}>
            {v}%
          </text>
        </g>
      ))}
      <path d={linha} fill="none" stroke={COR.coral} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray={comp} strokeDashoffset={comp * (1 - p1)} />
      <line x1={pts[2].x} y1={pts[2].y} x2={pts[2].x + (pts[3].x - pts[2].x) * p2} y2={pts[2].y + (pts[3].y - pts[2].y) * p2}
        stroke={COR.coral} strokeWidth={8} strokeDasharray="4 18" strokeLinecap="round" />
      {pts.map((p, i) => {
        const s = i < 3 ? mola(frame, inicio + i * 8, 12) : mola(frame, projecao + 12, 12);
        return (
          <g key={p.ano} transform={`translate(${p.x} ${p.y}) scale(${s})`}>
            <circle r={14} fill={i < 3 ? COR.coral : COR.fundo} stroke={COR.coral} strokeWidth={5} />
            <text y={-30} textAnchor="middle" fill={COR.texto} style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 34}}>
              {p.v.toLocaleString("pt-BR")}%
            </text>
          </g>
        );
      })}
      {pts.map((p) => (
        <text key={p.ano} x={p.x} y={A + 56} textAnchor="middle" fill={COR.apagado} style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 28}}>
          {p.ano === 2030 ? "2030*" : p.ano}
        </text>
      ))}
    </svg>
  );
};

export const Mundo: React.FC = () => {
  const {frame, em, fala} = useCena("mundo");
  const l11 = fala("l11");
  const l12 = fala("l12");
  const l13 = fala("l13");
  const l14 = fala("l14");
  const quase = em("l12", "quase");
  const trinta = em("l13", "trinta");
  const oito = em("l14", "oito");

  const pSobe = prog(frame, l12.s - 4, 22);
  const sai12 = some(frame, l14.s - 6);
  const troca = prog(frame, l13.s, 14);

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="03 · Os dados" fonte="OMS / The Lancet Global Health, 2024" />

      {/* manchete */}
      <div style={{position: "absolute", width: "100%", top: 190, textAlign: "center", opacity: mola(frame, l11.s - 6, 14) * (1 - pSobe)}}>
        <Globe size={150} color={COR.ciano} strokeWidth={1.5} style={{transform: `rotate(${frame * 0.6}deg)`}} />
      </div>
      <div
        style={{
          position: "absolute",
          width: "100%",
          top: interpolate(pSobe, [0, 1], [400, 150]),
          textAlign: "center",
          opacity: mola(frame, l11.s - 6, 14) * sai12,
          transform: `scale(${1 - 0.45 * pSobe})`,
          transformOrigin: "50% 0%",
        }}
      >
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "100%", fontSize: 100, color: COR.texto}}>
          O mundo anda <Destaque cor={COR.coral}>parado</Destaque> demais
        </div>
      </div>

      {/* grade de 100 pessoas */}
      <div
        style={{
          position: "absolute",
          left: 190,
          top: 320,
          display: "grid",
          gridTemplateColumns: "repeat(10, 54px)",
          gap: 4,
          opacity: prog(frame, l12.s, 14) * (1 - troca),
        }}
      >
        {Array.from({length: 100}, (_, i) => {
          const ordem = DESTACADOS.indexOf(i);
          const aceso = ordem >= 0 ? prog(frame, quase + ordem, 6) : 0;
          return (
            <div key={i} style={{width: 54, height: 54, display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${1 + 0.15 * aceso})`}}>
              <User size={44} strokeWidth={2.4} color={aceso > 0.5 ? COR.coral : "rgba(255,255,255,0.28)"} fill={aceso > 0.5 ? COR.coral : "none"} />
            </div>
          );
        })}
      </div>

      {/* gráfico da tendência */}
      <div style={{position: "absolute", left: 250, top: 330, opacity: troca * sai12}}>
        <Grafico frame={frame} inicio={l13.s + 4} projecao={trinta - 6} />
        <div style={{marginTop: 4, fontFamily: FONTE.texto, fontWeight: 500, fontSize: 22, color: COR.apagado}}>* projeção se nada mudar</div>
      </div>

      {/* números à direita */}
      <div style={{position: "absolute", left: 1010, top: 300, width: 800, opacity: sai12}}>
        <div style={{opacity: 1 - troca}}>
          <Entra em={quase - 2}>
            <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 230, lineHeight: 1, color: COR.coral}}>
              <Contador ate={31} em={quase} depois="%" />
            </div>
            <div style={{marginTop: 8, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 40, lineHeight: 1.25, color: COR.texto}}>
              dos adultos do mundo não chegaram
              <br />
              ao mínimo recomendado em 2022
            </div>
          </Entra>
          <Entra em={em("l12", "vírgula") - 8} style={{marginTop: 34}}>
            <div style={{display: "inline-flex", alignItems: "baseline", gap: 18, padding: "14px 30px", borderRadius: 24, background: COR.painel, border: `1.5px solid ${COR.borda}`}}>
              <span style={{fontFamily: FONTE.titulo, fontWeight: 900, fontSize: 76, color: COR.texto}}>
                ≈ <Contador ate={1.8} casas={1} em={em("l12", "vírgula") - 6} dur={20} />
              </span>
              <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 38, color: COR.apagado}}>bilhão de pessoas</span>
            </div>
          </Entra>
        </div>
        <div style={{position: "absolute", top: 0, opacity: prog(frame, trinta - 4, 14)}}>
          <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 230, lineHeight: 1, color: COR.coral}}>35%</div>
          <div style={{marginTop: 8, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 40, lineHeight: 1.25, color: COR.texto}}>
            em 2030, se nada mudar
          </div>
        </div>
      </div>

      {/* adolescentes */}
      <AbsoluteFill style={{opacity: prog(frame, l14.s, 14), alignItems: "center"}}>
        <div style={{marginTop: 210, fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 64, color: COR.texto}}>
          Entre os <Destaque cor={COR.ciano}>adolescentes</Destaque>, é pior
        </div>
        <div style={{display: "flex", gap: 22, marginTop: 50}}>
          {Array.from({length: 10}, (_, i) => {
            const aceso = i < 8 ? prog(frame, oito + i * 3, 8) : 0;
            return (
              <User key={i} size={112} strokeWidth={2.2}
                color={aceso > 0.5 ? COR.coral : "rgba(255,255,255,0.3)"} fill={aceso > 0.5 ? COR.coral : "none"}
                style={{transform: `translateY(${-14 * Math.sin(Math.PI * aceso)}px)`}} />
            );
          })}
        </div>
        <Entra em={oito + 4} style={{marginTop: 40, display: "flex", alignItems: "baseline", gap: 30}}>
          <span style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 150, color: COR.coral}}>+ de 80%</span>
          <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 40, color: COR.texto}}>não se mexem o quanto deveriam</span>
        </Entra>
        <Entra em={oito + 12} style={{marginTop: 6}}>
          <span style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 26, color: COR.apagado}}>11 a 17 anos · dados de 2016 (OMS)</span>
        </Entra>
      </AbsoluteFill>

      <Som em={quase - 2} arquivo="pop" volume={0.18} />
      <Som em={trinta - 4} arquivo="pop" volume={0.18} />
      <Som em={oito + 4} arquivo="pop" volume={0.18} />
    </AbsoluteFill>
  );
};
