import React from "react";
import {AbsoluteFill} from "remotion";
import {Armchair, Footprints} from "lucide-react";
import {mola, prog} from "../anim";
import {Cabecalho, Cartao, Entra, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const Bloco: React.FC<{icone: React.ReactNode; cor: string; valor: string; texto: string}> = ({icone, cor, valor, texto}) => (
  <Cartao style={{width: 420, padding: "24px 30px", borderTop: `6px solid ${cor}`, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center"}}>
    <div style={{color: cor}}>{icone}</div>
    <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "105%", fontSize: 66, lineHeight: 1.05, color: cor, marginTop: 6, whiteSpace: "nowrap"}}>{valor}</div>
    <div style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 28, color: COR.texto, marginTop: 4, whiteSpace: "nowrap"}}>{texto}</div>
  </Cartao>
);

export const Sentado: React.FC = () => {
  const {frame, em, fala} = useCena("sentado");
  const l25 = fala("l25");
  const sentado = em("l25", "sentado");
  const hora = em("l25", "hora");
  const anular = em("l25", "anular");

  // gangorra: pende para o lado de quem fica sentado e se equilibra no "anular"
  const pende = mola(frame, sentado + 2, 16);
  const equilibra = mola(frame, anular - 2, 10);
  const ang = (-11 * pende) * (1 - equilibra);
  const rad = (ang * Math.PI) / 180;
  const CX = 960;
  const CY = 770;
  const R = 560;
  const esq = {x: CX - R * Math.cos(rad), y: CY - R * Math.sin(rad)};
  const dir = {x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad)};

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="04 · Curiosidades" fonte="Ekelund et al., The Lancet, 2016" />

      <Entra em={l25.s - 4} style={{position: "absolute", top: 160, width: "100%", textAlign: "center"}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 92, color: COR.texto}}>
          E quem passa o dia <span style={{color: COR.coral}}>sentado</span>?
        </div>
      </Entra>
      <Entra em={anular + 6} style={{position: "absolute", top: 290, width: "100%", textAlign: "center"}}>
        <span style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 40, color: COR.limao}}>
          parece anular o risco extra de ficar muito tempo sentado
        </span>
      </Entra>

      {/* gangorra */}
      <div style={{opacity: prog(frame, sentado - 6, 12)}}>
        <div
          style={{
            position: "absolute",
            left: CX - R - 20,
            top: CY - 10,
            width: 2 * R + 40,
            height: 20,
            borderRadius: 10,
            background: `linear-gradient(90deg, ${COR.coral}, ${COR.texto} 50%, ${COR.limao})`,
            transform: `rotate(${ang}deg)`,
          }}
        />
        <svg style={{position: "absolute", left: CX - 70, top: CY + 8}} width={140} height={110}>
          <path d="M 70 0 L 140 110 L 0 110 Z" fill={COR.painel2} stroke={COR.borda} strokeWidth={3} />
        </svg>
        <div
          style={{
            position: "absolute",
            left: CX - 34,
            top: CY - 34,
            width: 68,
            height: 68,
            borderRadius: 34,
            background: frame >= anular ? COR.limao : COR.painel2,
            border: `3px solid ${COR.borda}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: FONTE.titulo,
            fontWeight: 900,
            fontSize: 44,
            color: frame >= anular ? COR.fundo : COR.apagado,
            transform: `scale(${1 + 0.25 * Math.sin(Math.PI * prog(frame, anular, 12))})`,
          }}
        >
          =
        </div>
      </div>

      <div style={{position: "absolute", left: esq.x - 240, top: esq.y - 262, opacity: prog(frame, sentado - 4, 10), transform: `translateY(${(1 - mola(frame, sentado - 4, 12)) * -80}px)`}}>
        <Bloco icone={<Armchair size={62} strokeWidth={2} />} cor={COR.coral} valor="8h+" texto="sentado por dia" />
      </div>
      <div style={{position: "absolute", left: dir.x - 240, top: dir.y - 262, opacity: prog(frame, hora - 4, 10), transform: `translateY(${(1 - mola(frame, hora - 4, 12)) * -80}px)`}}>
        <Bloco icone={<Footprints size={62} strokeWidth={2} />} cor={COR.limao} valor="60–75 min" texto="de atividade moderada" />
      </div>

      <Som em={sentado - 4} arquivo="pop" volume={0.2} />
      <Som em={hora - 4} arquivo="pop" volume={0.2} />
      <Som em={anular - 2} arquivo="pop" volume={0.22} />
    </AbsoluteFill>
  );
};
