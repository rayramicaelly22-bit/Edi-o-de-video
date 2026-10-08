import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Tempos em segundos no vídeo final (1080x1920, 30 fps).
// Ajuste aqui se o corte mudar.
const FPS = 30;
const f = (s: number) => Math.round(s * FPS);
export const OVERLAY_SECONDS = 72.4;

// Paleta da Areta: bordô e off-white
const INK = "#6D1F2F";
const ACCENT = "#F6F1E7";
const FONT = "Arial, Helvetica, sans-serif";

// Título: cada linha é uma faixa bordô que desliza e revela o texto em off-white
const TitleLine: React.FC<{text: string; delay: number}> = ({text, delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: frame - delay, fps, config: {damping: 200}});
  return (
    <div style={{overflow: "hidden"}}>
      <div
        style={{
          transform: `translateX(${(1 - p) * -105}%)`,
          background: INK,
          color: ACCENT,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 92,
          lineHeight: 1.05,
          textTransform: "uppercase",
          padding: "16px 36px",
          borderRadius: 16,
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </div>
    </div>
  );
};

const KineticTitle: React.FC = () => {
  return (
    <AbsoluteFill
      style={{alignItems: "center", justifyContent: "flex-start", paddingTop: 260, display: "flex", flexDirection: "column", gap: 18}}
    >
      <TitleLine text="Coisas que eu" delay={0} />
      <TitleLine text="parei de fazer" delay={9} />
    </AbsoluteFill>
  );
};

// Cartão do item: entra pela esquerda e some no fim
const ItemChip: React.FC<{num: string; label: string; duration: number}> = ({num, label, duration}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 14}});
  const out = interpolate(frame, [duration - 12, duration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        top: 300,
        left: 70,
        display: "flex",
        alignItems: "center",
        gap: 22,
        transform: `translateX(${(1 - p) * -540}px)`,
        opacity: out,
      }}
    >
      <div
        style={{
          background: ACCENT,
          color: INK,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 72,
          padding: "12px 26px",
          borderRadius: 18,
        }}
      >
        {num}
      </div>
      <div
        style={{
          background: INK,
          color: ACCENT,
          fontFamily: FONT,
          fontWeight: 700,
          fontSize: 60,
          padding: "12px 30px",
          borderRadius: 18,
        }}
      >
        {label}
      </div>
    </div>
  );
};

// Cartão flutuando com a assinatura, sem logo oficial
const FloatingBadge: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 12}});
  const bob = Math.sin(frame / 14) * 14;
  const tilt = Math.sin(frame / 22) * 3;
  return (
    <div
      style={{
        position: "absolute",
        top: 1230,
        left: 60,
        transform: `translateY(${bob + (1 - p) * 120}px) rotate(${tilt}deg) scale(${p})`,
        opacity: p,
        background: INK,
        color: ACCENT,
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: 58,
        padding: "22px 36px",
        borderRadius: 28,
        boxShadow: "0 20px 50px rgba(0,0,0,0.35)",
      }}
    >
      ✦ Claude Pro
    </div>
  );
};

// Gráfico que preenche enquanto você fala das planilhas (ilustrativo, sem números)
const FillingChart: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const heights = [0.45, 0.7, 0.55, 0.9, 0.75];
  return (
    <div
      style={{
        position: "absolute",
        left: 90,
        right: 90,
        top: 1080,
        height: 330,
        boxSizing: "border-box",
        background: "rgba(246,241,231,0.96)",
        borderRadius: 28,
        padding: "34px 50px",
        boxShadow: "0 20px 50px rgba(0,0,0,0.25)",
      }}
    >
      <div style={{fontFamily: FONT, fontWeight: 700, fontSize: 44, color: INK, marginBottom: 18}}>
        Controle financeiro
      </div>
      <div style={{display: "flex", alignItems: "flex-end", gap: 28, height: 200}}>
        {heights.map((h, i) => {
          const p = spring({frame: frame - 12 - i * 6, fps, config: {damping: 200}});
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: `${h * p * 100}%`,
                background: i === 3 ? INK : "rgba(109,31,47,0.45)",
                borderRadius: 12,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

// Botão de comentar no final, pulsando de leve
const CommentCta: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 12}});
  const pulse = 1 + Math.sin(frame / 5) * 0.03;
  return (
    <div
      style={{
        position: "absolute",
        top: 820,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        transform: `scale(${p * pulse})`,
        opacity: p,
      }}
    >
      <div
        style={{
          background: ACCENT,
          color: INK,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 66,
          padding: "26px 52px",
          borderRadius: 999,
          boxShadow: "0 20px 50px rgba(0,0,0,0.3)",
        }}
      >
        Comenta: PARTE 2
      </div>
    </div>
  );
};

// Tempos calculados a partir dos trechos cortados
export const Overlay: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: "transparent"}}>
      <Sequence from={0} durationInFrames={f(3.3)}>
        <KineticTitle />
      </Sequence>
      <Sequence from={f(0.6)} durationInFrames={f(2.6)}>
        <FloatingBadge />
      </Sequence>
      <Sequence from={f(3.7)} durationInFrames={f(4)}>
        <ItemChip num="01" label="Limpeza" duration={f(4)} />
      </Sequence>
      <Sequence from={f(14.9)} durationInFrames={f(4)}>
        <ItemChip num="02" label="Agenda" duration={f(4)} />
      </Sequence>
      <Sequence from={f(23.6)} durationInFrames={f(11)}>
        <ItemChip num="03" label="Planilhas" duration={f(4)} />
        <FillingChart />
      </Sequence>
      <Sequence from={f(50.9)} durationInFrames={f(4)}>
        <ItemChip num="04" label="Faculdade" duration={f(4)} />
      </Sequence>
      <Sequence from={f(68.4)} durationInFrames={f(4)}>
        <CommentCta />
      </Sequence>
    </AbsoluteFill>
  );
};
