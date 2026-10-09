import React from "react";
import {Easing, Sequence, staticFile, useCurrentFrame} from "remotion";
import {Audio} from "@remotion/media";
import {mola, num, prog, some} from "../anim";
import {COR, FONTE, MARGEM} from "../tema";

type Direcao = "baixo" | "cima" | "esquerda" | "direita" | "escala";

// entrada padrão: desliza + aparece; `sai` (opcional) é o quadro em que some
export const Entra: React.FC<{
  em: number;
  de?: Direcao;
  dur?: number;
  dist?: number;
  sai?: number;
  quique?: boolean;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({em, de = "baixo", dur = 18, dist = 40, sai, quique, style, children}) => {
  const frame = useCurrentFrame();
  const p = quique ? mola(frame, em) : prog(frame, em, dur);
  const o = Math.min(prog(frame, em, Math.max(6, dur * 0.6)), sai === undefined ? 1 : some(frame, sai));
  const d = (1 - p) * dist;
  const transform =
    de === "baixo" ? `translateY(${d}px)` :
    de === "cima" ? `translateY(${-d}px)` :
    de === "esquerda" ? `translateX(${-d}px)` :
    de === "direita" ? `translateX(${d}px)` :
    `scale(${0.6 + 0.4 * p})`;
  return <div style={{opacity: o, transform, ...style}}>{children}</div>;
};

// número que conta até o valor final
export const Contador: React.FC<{
  ate: number;
  em: number;
  de?: number;
  dur?: number;
  casas?: number;
  antes?: string;
  depois?: string;
  style?: React.CSSProperties;
}> = ({ate, em, de = 0, dur = 24, casas = 0, antes = "", depois = "", style}) => {
  const frame = useCurrentFrame();
  const v = de + (ate - de) * prog(frame, em, dur, Easing.out(Easing.cubic));
  return (
    <span style={{fontVariantNumeric: "tabular-nums", ...style}}>
      {antes}
      {num(v, casas)}
      {depois}
    </span>
  );
};

// rótulo da seção (canto superior esquerdo) e fonte do dado (canto superior direito)
export const Cabecalho: React.FC<{rotulo: string; fonte?: string; em?: number}> = ({rotulo, fonte, em = 4}) => {
  const frame = useCurrentFrame();
  const p = prog(frame, em, 20);
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: MARGEM,
          top: 70,
          display: "flex",
          alignItems: "center",
          gap: 14,
          opacity: p,
          transform: `translateX(${(1 - p) * -30}px)`,
          fontFamily: FONTE.texto,
          fontWeight: 700,
          fontSize: 22,
          letterSpacing: "0.18em",
          color: COR.apagado,
          textTransform: "uppercase",
        }}
      >
        <div style={{width: 12, height: 12, borderRadius: 6, background: COR.limao, boxShadow: `0 0 16px ${COR.limao}`}} />
        {rotulo}
      </div>
      {fonte ? (
        <div
          style={{
            position: "absolute",
            right: MARGEM,
            top: 72,
            opacity: p * 0.9,
            fontFamily: FONTE.texto,
            fontWeight: 500,
            fontSize: 20,
            color: COR.apagado,
            textAlign: "right",
          }}
        >
          Fonte: {fonte}
        </div>
      ) : null}
    </>
  );
};

// selo redondo com ícone
export const Selo: React.FC<{cor: string; tamanho?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
  cor,
  tamanho = 96,
  children,
  style,
}) => (
  <div
    style={{
      width: tamanho,
      height: tamanho,
      borderRadius: tamanho / 2,
      background: `${cor}22`,
      border: `2px solid ${cor}55`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: cor,
      flexShrink: 0,
      ...style,
    }}
  >
    {children}
  </div>
);

// cartão escuro com borda sutil
export const Cartao: React.FC<{style?: React.CSSProperties; children: React.ReactNode}> = ({style, children}) => (
  <div
    style={{
      background: `linear-gradient(160deg, ${COR.painel2}, ${COR.painel})`,
      border: `1.5px solid ${COR.borda}`,
      borderRadius: 32,
      boxShadow: "0 30px 80px rgba(0,0,0,0.35)",
      ...style,
    }}
  >
    {children}
  </div>
);

// linha de batimento (ECG) que se desenha da esquerda para a direita
export const Pulso: React.FC<{
  em: number;
  largura: number;
  altura?: number;
  cor?: string;
  dur?: number;
  batidas?: number;
  espessura?: number;
  style?: React.CSSProperties;
}> = ({em, largura, altura = 160, cor = COR.limao, dur = 40, batidas = 3, espessura = 6, style}) => {
  const frame = useCurrentFrame();
  const meio = altura / 2;
  const passo = largura / batidas;
  let d = `M 0 ${meio}`;
  for (let i = 0; i < batidas; i++) {
    const x = i * passo + passo * 0.35;
    const a = altura * 0.42;
    d += ` L ${x} ${meio} L ${x + 18} ${meio - a * 0.18} L ${x + 34} ${meio} L ${x + 50} ${meio + a * 0.25}`;
    d += ` L ${x + 70} ${meio - a} L ${x + 92} ${meio + a * 0.55} L ${x + 108} ${meio}`;
    d += ` L ${x + 140} ${meio - a * 0.22} L ${x + 168} ${meio}`;
  }
  d += ` L ${largura} ${meio}`;
  const p = prog(frame, em, dur, Easing.inOut(Easing.cubic));
  const comprimento = largura * 2.2;
  return (
    <svg width={largura} height={altura} style={{overflow: "visible", ...style}}>
      <path
        d={d}
        fill="none"
        stroke={cor}
        strokeWidth={espessura}
        strokeLinejoin="round"
        strokeLinecap="round"
        strokeDasharray={comprimento}
        strokeDashoffset={comprimento * (1 - p)}
        style={{filter: `drop-shadow(0 0 10px ${cor})`}}
      />
    </svg>
  );
};

// efeito sonoro curto num quadro local da cena
export const Som: React.FC<{em: number; arquivo: "pop" | "whoosh" | "impacto"; volume?: number}> = ({em, arquivo, volume = 0.3}) => (
  <Sequence from={em} durationInFrames={75} layout="none">
    <Audio src={staticFile(`sfx/${arquivo}.wav`)} volume={volume} />
  </Sequence>
);

// texto com destaque em uma parte (cor de acento)
export const Destaque: React.FC<{cor?: string; children: React.ReactNode}> = ({cor = COR.limao, children}) => (
  <span style={{color: cor}}>{children}</span>
);

