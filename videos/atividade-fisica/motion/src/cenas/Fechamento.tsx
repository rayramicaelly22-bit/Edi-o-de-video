import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {Brain, Bus, HeartPulse, Music, Timer, TrendingUp} from "lucide-react";
import {mola, prog, some} from "../anim";
import {Cabecalho, Entra, Pulso, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

export const Fechamento: React.FC = () => {
  const {frame, em, fala} = useCena("fechamento");
  const l26 = fala("l26");
  const l27 = fala("l27");
  const l28 = fala("l28");

  const palavras = [
    {t: "CADA", em: em("l26", "Cada"), cor: COR.texto},
    {t: "MOVIMENTO", em: em("l26", "movimento"), cor: COR.texto},
    {t: "CONTA.", em: em("l26", "conta"), cor: COR.limao},
  ];
  const sobe = prog(frame, l27.s - 4, 22);
  const sai27 = some(frame, l28.s - 6);
  const dicas = [
    {em: em("l27", "dez"), icone: <Timer size={38} />, cor: COR.limao, texto: "10 minutos hoje"},
    {em: em("l27", "escada"), icone: <TrendingUp size={38} />, cor: COR.ciano, texto: "vá de escada"},
    {em: em("l27", "ponto"), icone: <Bus size={38} />, cor: COR.amarelo, texto: "desça um ponto antes"},
    {em: em("l27", "dance"), icone: <Music size={38} />, cor: COR.coral, texto: "dance na sala"},
  ];

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="05 · Resumindo" />

      <div style={{opacity: sai27}}>
        <Entra em={em("l26", "você") - 4} sai={l27.s - 8} style={{position: "absolute", top: 250, width: "100%", textAlign: "center"}}>
          <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 52, color: COR.apagado}}>Você não precisa virar atleta.</span>
        </Entra>

        <div
          style={{
            position: "absolute",
            width: "100%",
            top: interpolate(sobe, [0, 1], [380, 170]),
            textAlign: "center",
            transform: `scale(${1 - 0.42 * sobe})`,
            transformOrigin: "50% 0%",
          }}
        >
          <div style={{display: "flex", justifyContent: "center", flexWrap: "wrap", columnGap: 44, maxWidth: 1700, margin: "0 auto"}}>
            {palavras.map((p) => {
              const m = mola(frame, p.em - 2, 11);
              return (
                <span
                  key={p.t}
                  style={{
                    display: "inline-block",
                    opacity: prog(frame, p.em - 2, 4),
                    transform: `scale(${0.4 + 0.6 * m})`,
                    fontFamily: FONTE.titulo,
                    fontWeight: 900,
                    fontStretch: "112%",
                    fontSize: 140,
                    lineHeight: 1.05,
                    color: p.cor,
                    textShadow: p.cor === COR.limao ? `0 0 50px ${COR.limao}66` : "none",
                  }}
                >
                  {p.t}
                </span>
              );
            })}
          </div>
          <div style={{display: "flex", justifyContent: "center", marginTop: 10, opacity: 1 - sobe}}>
            <Pulso em={em("l26", "conta") + 4} largura={1300} altura={130} batidas={3} dur={30} />
          </div>
        </div>

        <div style={{position: "absolute", top: 540, width: "100%", display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 26, padding: "0 140px"}}>
          {dicas.map((d) => (
            <Entra key={d.texto} em={d.em - 3} de="escala" quique>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 20,
                  padding: "14px 36px 14px 14px",
                  borderRadius: 60,
                  background: "rgba(18,26,49,0.9)",
                  border: `1.5px solid ${d.cor}55`,
                }}
              >
                <Selo cor={d.cor} tamanho={78}>{d.icone}</Selo>
                <span style={{fontFamily: FONTE.texto, fontWeight: 700, fontSize: 42, color: COR.texto}}>{d.texto}</span>
              </div>
            </Entra>
          ))}
        </div>
      </div>

      {/* mensagem final */}
      <AbsoluteFill style={{alignItems: "center", justifyContent: "center", opacity: prog(frame, l28.s - 4, 14)}}>
        <div style={{display: "flex", gap: 40, marginTop: -120}}>
          <Selo cor={COR.coral} tamanho={150} style={{transform: `scale(${mola(frame, l28.s - 2, 10)})`}}>
            <HeartPulse size={80} />
          </Selo>
          <Selo cor={COR.ciano} tamanho={150} style={{transform: `scale(${mola(frame, l28.s + 4, 10)})`}}>
            <Brain size={80} />
          </Selo>
        </div>
        <div style={{marginTop: 40, fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 92, color: COR.texto, textAlign: "center"}}>
          Seu corpo e sua cabeça <span style={{color: COR.limao}}>agradecem.</span>
        </div>
        <div style={{marginTop: 20}}>
          <Pulso em={l28.s + 6} largura={1400} altura={120} batidas={4} dur={44} espessura={5} />
        </div>
      </AbsoluteFill>

      {dicas.map((d) => (
        <Som key={d.texto} em={d.em - 3} arquivo="pop" volume={0.18} />
      ))}
    </AbsoluteFill>
  );
};
