import React from "react";
import {Video} from "@remotion/media";
import {AbsoluteFill, staticFile, useVideoConfig} from "remotion";
import {SCENE, lineById, wordTime} from "./overlay/data";
import {Ball, Bike, Hospital, Paw, Pin} from "./overlay/Icons";
import {T} from "./timeline";
import {
  ArrivalBurst,
  Captions,
  EndCard,
  HOSPITAL_LABEL,
  MapLabel,
  NavBanner,
  PRACA_LABEL,
  Shades,
  StoreCard,
  StoreTag,
  Title,
} from "./overlay/Overlays";
import {COLORS, loadFonts} from "./overlay/theme";

// Passo 3 do pipeline: voo 3D já renderizado e tratado (public/render) + motion graphics + legendas.
// O áudio (narração, trilha e efeitos) é mixado à parte e unido no final (scripts/finalize.sh).
export const LocalizacaoLoja: React.FC = () => {
  loadFonts();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: "#000"}}>
      <Video src={staticFile("render/drone3d_graded.mp4")} premountFor={fps} muted />
      <Shades />
      <Title />
      <MapLabel
        anchor={SCENE.pois.praca}
        start={PRACA_LABEL.start}
        end={PRACA_LABEL.end}
        kicker="Ponto de partida"
        title="Praça Célio Miranda"
        icon={<Pin size={54} color="#fff" hole={COLORS.route} />}
        accent={COLORS.route}
      />
      <MapLabel
        anchor={SCENE.pois.arena}
        start={wordTime("virada", "avenida") - 0.05}
        end={T.turnAt + 0.2}
        kicker="No fim da avenida"
        title="Arena Verde"
        icon={<Ball size={54} />}
        accent="#1fa85b"
        stem={150}
        layout="side"
        side="left"
        rise={80}
      />
      <MapLabel
        anchor={SCENE.pois.hospital}
        start={HOSPITAL_LABEL.start}
        end={HOSPITAL_LABEL.end}
        kicker="Referência"
        title="Hospital São Paulo"
        icon={<Hospital size={60} color="#ff3b47" />}
        accent="#ff3b47"
        stem={140}
      />
      <MapLabel
        anchor={SCENE.pois.juniorBike}
        start={wordTime("endereco", "frente") - 0.1}
        end={lineById("convite").start - 0.2}
        kicker="Em frente"
        title="Júnior Bike"
        icon={<Bike size={50} />}
        accent={COLORS.route}
        stem={150}
        layout="side"
        side="right"
        rise={65}
      />
      <MapLabel
        anchor={SCENE.pois.vilaPet}
        start={wordTime("endereco", "ladinho") - 0.1}
        end={lineById("convite").start - 0.2}
        kicker="Do lado"
        title="Vila Pet"
        icon={<Paw size={46} />}
        accent="#ff9f1c"
        stem={120}
        layout="side"
        side="left"
        rise={-60}
      />
      <NavBanner />
      <Captions />
      <ArrivalBurst />
      <StoreTag />
      <StoreCard />
      <EndCard />
    </AbsoluteFill>
  );
};
