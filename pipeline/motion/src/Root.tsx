import React from "react";
import {Composition} from "remotion";
import {Overlay, OVERLAY_SECONDS} from "./Overlay";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Overlay"
      component={Overlay}
      durationInFrames={Math.round(OVERLAY_SECONDS * 30)}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
