import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {CircleCheck, Brain, HeartPulse, Hourglass, Smile} from "lucide-react";
import {mola, prog, some} from "../anim";
import {Entra, Pulso, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const Capsula: React.FC<{frame: number; titulo: number; inicio: number}> = ({frame, titulo, inicio}) => {
  const entra = mola(frame, 4, 12);
  const balanco = inicio > 0 ? Math.sin((frame - inicio) / 2.2) * 7 * some(frame, inicio + 18, 10) * prog(frame, inicio, 4) : 0;
  const sai = some(frame, titulo - 4, 8);
  const escala = (0.5 + 0.5 * entra) * (1 + 0.5 * (1 - sai));
  return (
    <div
      style={{
        position: "absolute",
        left: 260,
        top: 380,
        width: 560,
        height: 220,
        opacity: sai,
        transform: `translateY(${Math.sin(frame / 18) * 10}px) rotate(${-60 + 36 * entra + balanco}deg) scale(${escala})`,
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 110,
          overflow: "hidden",
          display: "flex",
          boxShadow: `0 0 90px ${COR.limao}55, 0 40px 80px rgba(0,0,0,0.45)`,
        }}
      >
        <div style={{flex: 1, background: `linear-gradient(180deg, #DDFF6E, ${COR.limao} 55%, #8FBF14)`}} />
        <div style={{flex: 1, background: "linear-gradient(180deg, #FFFFFF, #E6EAF2 55%, #AEB6C8)"}} />
      </div>
      {/* brilho */}
      <div style={{position: "absolute", left: 60, top: 34, width: 380, height: 36, borderRadius: 18, background: "rgba(255,255,255,0.55)"}} />
    </div>
  );
};

const Chip: React.FC<{icone: React.ReactNode; cor: string; texto: string}> = ({icone, cor, texto}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 26,
      padding: "16px 40px 16px 16px",
      borderRadius: 70,
      background: "rgba(18,26,49,0.85)",
      border: `1.5px solid ${COR.borda}`,
      boxShadow: "0 20px 50px rgba(0,0,0,0.35)",
    }}
  >
    <Selo cor={cor} tamanho={84}>{icone}</Selo>
    <span style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 44, color: COR.texto}}>{texto}</span>
  </div>
);

export const Gancho: React.FC = () => {
  const {frame, em, fala} = useCena("gancho");
  const l02 = fala("l02");
  const l03 = fala("l03");
  const titulo = em("l03", "Atividade");

  const beneficios = [
    {em: em("l01", "coração"), icone: <HeartPulse size={44} />, cor: COR.coral, texto: "protege o coração"},
    {em: em("l01", "humor"), icone: <Smile size={44} />, cor: COR.amarelo, texto: "melhora o humor"},
    {em: em("l01", "memória"), icone: <Brain size={44} />, cor: COR.ciano, texto: "ajuda a memória"},
    {em: em("l01", "viver"), icone: <Hourglass size={44} />, cor: COR.limao, texto: "mais anos de vida"},
  ];
  const vantagens = [
    {em: em("l02", "graça"), texto: "De graça"},
    {em: em("l02", "receita"), texto: "Sem receita"},
    {em: em("l02", "hoje"), texto: "Comece hoje"},
  ];

  const zoom = 1 + 0.035 * prog(frame, titulo, 90);
  const flash = frame < titulo ? 0 : interpolate(frame, [titulo, titulo + 9], [0.35, 0], {extrapolateRight: "clamp"});

  return (
    <AbsoluteFill>
      <Entra em={6} de="esquerda" sai={titulo - 6} style={{position: "absolute", left: 200, top: 210}}>
        <div style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 40, color: COR.apagado}}>Imagine um remédio que…</div>
      </Entra>

      <Capsula frame={frame} titulo={titulo} inicio={l03.s} />

      <div style={{position: "absolute", left: 1010, top: 200, display: "flex", flexDirection: "column", gap: 30}}>
        {beneficios.map((b) => (
          <Entra key={b.texto} em={b.em - 3} de="direita" quique dist={120} sai={l02.s - 8}>
            <Chip icone={b.icone} cor={b.cor} texto={b.texto} />
          </Entra>
        ))}
      </div>

      <div style={{position: "absolute", left: 1010, top: 270, display: "flex", flexDirection: "column", gap: 34}}>
        {vantagens.map((v) => (
          <Entra key={v.texto} em={v.em - 3} de="escala" quique sai={l03.s - 4}>
            <div style={{display: "flex", alignItems: "center", gap: 26}}>
              <CircleCheck size={86} color={COR.limao} strokeWidth={2.2} />
              <span style={{fontFamily: FONTE.titulo, fontWeight: 850, fontStretch: "112%", fontSize: 80, color: COR.texto}}>{v.texto}</span>
            </div>
          </Entra>
        ))}
      </div>

      {/* título */}
      <AbsoluteFill style={{alignItems: "center", justifyContent: "center", transform: `scale(${zoom})`}}>
        <div style={{position: "absolute", top: 655, opacity: frame >= titulo ? 1 : 0}}>
          <Pulso em={titulo + 2} largura={1560} altura={170} dur={38} batidas={4} cor={COR.limao} espessura={7} />
        </div>
        {[
          {texto: "ATIVIDADE", cor: COR.texto, atraso: 0, tam: 196},
          {texto: "FÍSICA", cor: COR.limao, atraso: 5, tam: 236},
        ].map((l, i) => {
          const p = mola(frame, titulo + l.atraso, 14);
          return (
            <div key={l.texto} style={{overflow: "hidden", marginTop: i ? -30 : -150}}>
              <div
                style={{
                  transform: `translateY(${(1 - p) * 110}%)`,
                  fontFamily: FONTE.titulo,
                  fontWeight: 900,
                  fontStretch: "125%",
                  fontSize: l.tam,
                  lineHeight: 1.05,
                  letterSpacing: "-0.01em",
                  color: l.cor,
                  textShadow: i ? `0 0 60px ${COR.limao}66` : "none",
                }}
              >
                {l.texto}
              </div>
            </div>
          );
        })}
        <Entra em={titulo + 16} style={{position: "absolute", top: 862}}>
          <div style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 32, letterSpacing: "0.32em", color: COR.apagado}}>
            IMPORTÂNCIA · DADOS · CURIOSIDADES
          </div>
        </Entra>
      </AbsoluteFill>
      <AbsoluteFill style={{background: "#FFFFFF", opacity: flash}} />

      {beneficios.map((b) => (
        <Som key={b.texto} em={b.em - 3} arquivo="pop" volume={0.22} />
      ))}
      {vantagens.map((v) => (
        <Som key={v.texto} em={v.em - 3} arquivo="pop" volume={0.22} />
      ))}
    </AbsoluteFill>
  );
};
