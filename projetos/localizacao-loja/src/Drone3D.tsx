import React, {useEffect, useState} from "react";
import * as THREE from "three";
import {ThreeCanvas} from "@remotion/three";
import {AbsoluteFill, useDelayRender, useVideoConfig} from "remotion";
import {loadScene, type SceneAssets} from "./scene/load";
import {World} from "./scene/World";

// Passo 1 do pipeline: só a cena 3D (o motion graphics entra depois, por cima do vídeo renderizado).
export const Drone3D: React.FC = () => {
  const {width, height} = useVideoConfig();
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const [handle] = useState(() => delayRender("Carregando a cena 3D de Paragominas", {timeoutInMilliseconds: 120000}));
  const [assets, setAssets] = useState<SceneAssets | null>(null);

  useEffect(() => {
    loadScene()
      .then((a) => {
        setAssets(a);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, [handle, continueRender, cancelRender]);

  return (
    <AbsoluteFill style={{backgroundColor: "#d5dde2"}}>
      {assets ? (
        <ThreeCanvas
          width={width}
          height={height}
          flat
          shadows={{type: THREE.PCFShadowMap}}
          gl={{antialias: true, preserveDrawingBuffer: true, powerPreference: "high-performance"}}
          camera={{fov: 58, near: 2, far: 60000, position: [0, 3000, 0]}}
        >
          <World assets={assets} />
        </ThreeCanvas>
      ) : null}
    </AbsoluteFill>
  );
};
