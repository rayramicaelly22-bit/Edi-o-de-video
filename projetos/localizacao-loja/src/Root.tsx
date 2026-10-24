import React from "react";
import {Composition} from "remotion";
import {Drone3D} from "./Drone3D";
import {LocalizacaoLoja} from "./LocalizacaoLoja";
import {FPS, T} from "./timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="LocalizacaoLoja" component={LocalizacaoLoja} durationInFrames={Math.round(T.end * FPS)} fps={FPS} width={1080} height={1920} />
      <Composition id="Drone3D" component={Drone3D} durationInFrames={Math.round(T.end * FPS)} fps={FPS} width={1080} height={1920} />
    </>
  );
};
