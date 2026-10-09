import React from "react";
import {Composition} from "remotion";
import {FPS, H, W} from "./tema";
import {DURACAO} from "./tl";
import {Video} from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition id="AtividadeFisica" component={Video} durationInFrames={DURACAO} fps={FPS} width={W} height={H} />
);
