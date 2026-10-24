import React from "react";
import {Video} from "@remotion/media";
import {AbsoluteFill, staticFile, useVideoConfig} from "remotion";
import {SCENE, lineById, wordTime} from "./overlay/data";
import {Bike, Hospital, Pin} from "./overlay/Icons";
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
        stem={170}
        layout="side"
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
