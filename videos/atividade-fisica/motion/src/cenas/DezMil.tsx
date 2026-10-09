import React from "react";
import {AbsoluteFill, interpolate} from "remotion";
import {Footprints, Lightbulb} from "lucide-react";
import {mola, prog, some} from "../anim";
import {Cabecalho, Contador, Entra, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

const Pedometro: React.FC<{frame: number; kanji: number; romaji: number}> = ({frame, kanji, romaji}) => (
  <div style={{position: "relative", width: 460, height: 600}}>
    {/* presilha */}
    <div style={{position: "absolute", left: 160, top: -34, width: 140, height: 60, borderRadius: 20, background: COR.painel2, border: `3px solid ${COR.borda}`}} />
    <div
      style={{
        position: "absolute",
        inset: 0,
        borderRadius: 96,
        background: `linear-gradient(160deg, #24305A, ${COR.painel})`,
        border: "4px solid rgba(255,255,255,0.14)",
        boxShadow: `0 40px 90px rgba(0,0,0,0.5), inset 0 2px 0 rgba(255,255,255,0.12)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          marginTop: 70,
          width: 350,
          height: 150,
          borderRadius: 26,
          background: "#0D1A08",
          border: `3px solid ${COR.limao}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `inset 0 0 30px ${COR.limao}22`,
        }}
      >
        <span style={{fontFamily: FONTE.titulo, fontWeight: 700, fontStretch: "62%", fontSize: 118, letterSpacing: "0.08em", color: COR.limao, textShadow: `0 0 18px ${COR.limao}AA`}}>
          {String(Math.min(10000, Math.floor(prog(frame, kanji - 30, 40) * 10000))).padStart(5, "0")}
        </span>
      </div>
      <div style={{marginTop: 46, opacity: prog(frame, kanji, 12), transform: `scale(${0.8 + 0.2 * mola(frame, kanji, 12)})`}}>
        <span style={{fontFamily: FONTE.jp, fontWeight: 900, fontSize: 128, color: COR.texto, letterSpacing: "0.04em"}}>万歩計</span>
      </div>
      <div style={{marginTop: 10, opacity: prog(frame, romaji, 12), fontFamily: FONTE.texto, fontWeight: 700, fontSize: 38, letterSpacing: "0.2em", color: COR.limao}}>
        MAN · PO · KEI
      </div>
    </div>
  </div>
);

export const DezMil: React.FC = () => {
  const {frame, em, fala} = useCena("dezmil");
  const l18 = fala("l18");
  const l19 = fala("l19");
  const l20 = fala("l20");
  const dez = em("l19", "dez");
  const marketing = em("l19", "marketing");
  const kanji = em("l20", "chamado");
  const medidor = em("l20", "medidor");

  const saiTitulo = some(frame, l19.s - 6, 10);
  const encolhe = prog(frame, l20.s - 4, 24);
  const carimbo = mola(frame, marketing - 2, 11);

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="04 · Curiosidades" />
      <Entra em={kanji - 10} style={{position: "absolute", right: 120, top: 72}}>
        <div style={{fontFamily: FONTE.texto, fontWeight: 500, fontSize: 20, color: COR.apagado}}>Fonte: Lee et al., JAMA Internal Medicine, 2019</div>
      </Entra>

      {/* abertura da seção */}
      <AbsoluteFill style={{alignItems: "center", justifyContent: "center", opacity: saiTitulo}}>
        <div style={{transform: `scale(${mola(frame, l18.s - 6, 12)}) rotate(${Math.sin(frame / 6) * 6}deg)`}}>
          <Lightbulb size={150} color={COR.amarelo} strokeWidth={1.8} style={{filter: `drop-shadow(0 0 30px ${COR.amarelo}AA)`}} />
        </div>
        <div style={{display: "flex", marginTop: 10}}>
          {"CURIOSIDADES".split("").map((letra, i) => {
            const p = mola(frame, em("l18", "curiosidades") - 6 + i * 1.5, 12);
            return (
              <span key={i} style={{display: "inline-block", transform: `translateY(${(1 - p) * 80}px)`, opacity: p,
                fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "112%", fontSize: 150, color: COR.limao, textShadow: `0 0 40px ${COR.limao}55`}}>
                {letra}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>

      {/* 10.000 passos + carimbo de marketing */}
      <div
        style={{
          position: "absolute",
          left: interpolate(encolhe, [0, 1], [0, -420]),
          top: interpolate(encolhe, [0, 1], [0, -90]),
          width: "100%",
          height: "100%",
          transform: `scale(${1 - 0.3 * encolhe})`,
          opacity: prog(frame, dez - 6, 10),
        }}
      >
        <div style={{position: "absolute", top: 300, width: "100%", textAlign: "center"}}>
          <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "118%", fontSize: 230, lineHeight: 1, color: COR.texto}}>
            <Contador ate={10000} em={dez} dur={30} />
          </div>
          <div style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 52, color: COR.apagado, marginTop: 6}}>passos por dia</div>
          <div style={{display: "flex", justifyContent: "center", gap: 26, marginTop: 34}}>
            {Array.from({length: 7}, (_, i) => (
              <Footprints key={i} size={58} color={COR.limao}
                style={{opacity: prog(frame, dez + i * 4, 6), transform: `rotate(${i % 2 ? 12 : -12}deg) translateY(${i % 2 ? 10 : -10}px)`}} />
            ))}
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            left: 1000,
            top: 140,
            opacity: frame >= marketing - 2 ? 1 : 0,
            transform: `rotate(-10deg) scale(${2.4 - 1.4 * carimbo})`,
            padding: "8px 34px",
            border: `9px solid ${COR.coral}`,
            borderRadius: 18,
            fontFamily: FONTE.titulo,
            fontWeight: 900,
            fontStretch: "110%",
            fontSize: 100,
            color: COR.coral,
            background: "rgba(10,15,31,0.75)",
          }}
        >
          MARKETING
        </div>
      </div>

      {/* pedômetro japonês */}
      <Entra em={l20.s} de="direita" dist={500} dur={26} style={{position: "absolute", left: 1210, top: 250}}>
        <Pedometro frame={frame} kanji={kanji} romaji={em("l20", "manpo")} />
      </Entra>
      <Entra em={em("l20", "japonês") - 4} style={{position: "absolute", left: 1150, top: 870, width: 580, textAlign: "center"}}>
        <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 30, color: COR.apagado}}>Japão · anos 1960</span>
      </Entra>

      {/* tradução */}
      <div style={{position: "absolute", left: 230, top: 620, display: "flex", flexDirection: "column", gap: 18}}>
        {[
          {k: "万", t: "dez mil"},
          {k: "歩", t: "passos"},
          {k: "計", t: "medidor"},
        ].map((x, i) => (
          <Entra key={x.k} em={medidor - 16 + i * 6} de="esquerda">
            <div style={{display: "flex", alignItems: "center", gap: 26}}>
              <span style={{fontFamily: FONTE.jp, fontWeight: 900, fontSize: 64, color: COR.limao, width: 70}}>{x.k}</span>
              <span style={{fontFamily: FONTE.texto, fontWeight: 600, fontSize: 30, color: COR.apagado}}>=</span>
              <span style={{fontFamily: FONTE.titulo, fontWeight: 800, fontSize: 52, color: COR.texto}}>{x.t}</span>
            </div>
          </Entra>
        ))}
      </div>

      <Som em={marketing - 2} arquivo="impacto" volume={0.35} />
      <Som em={kanji} arquivo="pop" volume={0.2} />
    </AbsoluteFill>
  );
};
