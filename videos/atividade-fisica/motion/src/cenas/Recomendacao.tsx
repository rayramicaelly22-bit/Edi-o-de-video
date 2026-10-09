import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {Dumbbell, Flame, Footprints, Timer} from "lucide-react";
import {mola, prog} from "../anim";
import {Cabecalho, Contador, Entra, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const DIAS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"];

const Chip: React.FC<{icone: React.ReactNode; cor: string; texto: string}> = ({icone, cor, texto}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 16,
      padding: "10px 28px 10px 12px",
      borderRadius: 50,
      background: `${cor}1A`,
      border: `1.5px solid ${cor}66`,
    }}
  >
    <Selo cor={cor} tamanho={58}>{icone}</Selo>
    <span style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 34, color: COR.texto}}>{texto}</span>
  </div>
);

export const Recomendacao: React.FC = () => {
  const {frame, em, fala} = useCena("recomendacao");
  const l07 = fala("l07");
  const l08 = fala("l08");
  const metade = em("l09", "metade");
  const trinta = em("l09", "trinta");
  const forca = em("l10", "força");

  // pergunta: entra grande no centro e sobe quando a resposta começa
  const pEntra = mola(frame, l07.s - 4, 14);
  const pSobe = prog(frame, l08.s - 2, 22);
  const intensa = prog(frame, metade, 16);

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="02 · A recomendação" fonte="OMS, diretrizes de 2020" />

      <div
        style={{
          position: "absolute",
          width: "100%",
          top: interpolate(pSobe, [0, 1], [430, 150]),
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 30 - 10 * pSobe,
          opacity: pEntra,
          transform: `scale(${(0.7 + 0.3 * pEntra) * (1 - 0.48 * pSobe)})`,
        }}
      >
        <Timer size={112} color={COR.limao} strokeWidth={2} style={{transform: `rotate(${frame * 2}deg)`}} />
        <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "105%", fontSize: 112, color: COR.texto}}>
          Quanto é suficiente?
        </div>
      </div>

      {/* resposta moderada (some quando entra a intensa) */}
      <div style={{position: "absolute", top: 270, width: "100%", textAlign: "center", opacity: 1 - intensa}}>
        <Entra em={em("l08", "cento") - 2}>
          <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 180, lineHeight: 1, color: COR.limao}}>
            <Contador ate={150} em={em("l08", "cento")} dur={20} />
            <span style={{opacity: prog(frame, em("l08", "trezentos"), 10)}}>–300</span>
            <span style={{fontSize: 80, color: COR.texto}}> min</span>
          </div>
          <div style={{marginTop: 10, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 42, color: COR.texto}}>
            por semana de atividade <span style={{color: COR.limao}}>moderada</span>
          </div>
        </Entra>
        <Entra em={em("l08", "caminhada") - 3} quique style={{marginTop: 22}}>
          <Chip icone={<Footprints size={32} />} cor={COR.limao} texto="ex.: caminhada rápida" />
        </Entra>
      </div>

      {/* resposta intensa */}
      <div style={{position: "absolute", top: 270, width: "100%", textAlign: "center", opacity: intensa}}>
        <div style={{transform: `translateY(${(1 - intensa) * 30}px)`}}>
          <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 180, lineHeight: 1, color: COR.ciano}}>
            75–150<span style={{fontSize: 80, color: COR.texto}}> min</span>
          </div>
          <div style={{marginTop: 10, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 42, color: COR.texto}}>
            por semana de atividade <span style={{color: COR.ciano}}>intensa</span>
          </div>
        </div>
        <Entra em={em("l09", "corrida") - 3} quique style={{marginTop: 22}}>
          <Chip icone={<Flame size={32} />} cor={COR.ciano} texto="ex.: corrida" />
        </Entra>
      </div>

      {/* semana */}
      <Entra em={em("l09", "Uns") - 8} style={{position: "absolute", top: 682, left: 317, display: "flex", gap: 16}}>
        {DIAS.map((d, i) => {
          const util = i < 5;
          const enche = util ? prog(frame, trinta + i * 4, 10) : 0;
          const cor = intensa > 0.5 ? COR.ciano : COR.limao;
          const peso = (i === 1 || i === 3) ? mola(frame, forca + (i === 3 ? 6 : 0), 12) : 0;
          return (
            <div
              key={d}
              style={{
                width: 170,
                height: 150,
                borderRadius: 24,
                position: "relative",
                background: enche > 0 ? cor : COR.painel,
                border: `1.5px solid ${COR.borda}`,
                opacity: 0.55 + 0.45 * enche,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${0.92 + 0.08 * enche})`,
              }}
            >
              <div style={{fontFamily: FONTE.texto, fontWeight: 800, fontSize: 26, letterSpacing: "0.1em", color: enche > 0 ? COR.fundo : COR.apagado}}>{d}</div>
              <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontSize: 40, color: enche > 0 ? COR.fundo : COR.apagado, marginTop: 6}}>
                {util ? (intensa > 0.5 ? "15 min" : "30 min") : "—"}
              </div>
              {peso > 0 ? (
                <div style={{position: "absolute", top: -26, right: -18, transform: `scale(${peso})`}}>
                  <Selo cor={COR.coral} tamanho={64} style={{background: COR.coral, color: COR.fundo, border: "none"}}>
                    <Dumbbell size={36} />
                  </Selo>
                </div>
              ) : null}
            </div>
          );
        })}
      </Entra>

      <Entra em={forca - 2} quique style={{position: "absolute", top: 856, width: "100%", textAlign: "center"}}>
        <Chip icone={<Dumbbell size={32} />} cor={COR.coral} texto="+ exercícios de força: 2× por semana" />
      </Entra>

      <Som em={forca - 2} arquivo="pop" volume={0.22} />
      <Som em={em("l08", "caminhada") - 3} arquivo="pop" volume={0.18} />
    </AbsoluteFill>
  );
};
