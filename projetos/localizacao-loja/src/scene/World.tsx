import React, {useLayoutEffect, useMemo} from "react";
import * as THREE from "three";
import {useThree} from "@react-three/fiber";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {T} from "../timeline";
import {cameraAt, routeProgress} from "./camera";
import {routePoint} from "./route";
import type {SceneAssets} from "./load";

// Sol de oés-sudoeste: luz de 3/4 em relação ao voo (para nordeste), sombras visíveis à direita.
const SUN_AZ = 250;
const SUN_EL = 36;
const SUN_DIR = new THREE.Vector3(
  Math.sin((SUN_AZ * Math.PI) / 180) * Math.cos((SUN_EL * Math.PI) / 180),
  Math.sin((SUN_EL * Math.PI) / 180),
  -Math.cos((SUN_AZ * Math.PI) / 180) * Math.cos((SUN_EL * Math.PI) / 180),
);

const HAZE = new THREE.Color("#d5dde2");
const ZENITH = new THREE.Color("#6f9fd8");

export const ROUTE_COLORS = {start: "#2f7dff", end: "#19d3ff"};

// Desvanece a borda da área com geometria 3D (prédios "brotam" a partir da borda, ruas somem).
const edgeFade = (material: THREE.Material, half: number, mode: "height" | "alpha" | "instance") => {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uHalf = {value: half};
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
uniform float uHalf;
varying float vEdgeFade;`,
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
#ifdef USE_INSTANCING
vec3 edgeCenter = (instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
#else
vec3 edgeCenter = position;
#endif
float edgeR = max(abs(edgeCenter.x), abs(edgeCenter.z));
vEdgeFade = smoothstep(uHalf, uHalf - 650.0, edgeR);
${mode === "height" ? "transformed.y *= vEdgeFade;" : ""}
${mode === "instance" ? "transformed *= vEdgeFade;" : ""}`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
varying float vEdgeFade;`,
      )
      .replace(
        "#include <dithering_fragment>",
        `#include <dithering_fragment>
${mode === "alpha" ? "gl_FragColor.a *= vEdgeFade;" : ""}`,
      );
  };
  // o three.js usa o texto do onBeforeCompile como chave de cache; o modo precisa entrar na chave
  material.customProgramCacheKey = () => `edgeFade-${mode}`;
  return material;
};

// Granulado de solo/grama (ruído fractal que repete a cada 7 m) para o chão não parecer uma foto borrada de perto.
const makeGrain = () => {
  const n = 256;
  const rnd = (x: number, y: number, s: number) => {
    const v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453;
    return v - Math.floor(v);
  };
  const valueNoise = (x: number, y: number, cells: number, seed: number) => {
    const fx = (x / n) * cells;
    const fy = (y / n) * cells;
    const x0 = Math.floor(fx);
    const y0 = Math.floor(fy);
    const tx = fx - x0;
    const ty = fy - y0;
    const sx = tx * tx * (3 - 2 * tx);
    const sy = ty * ty * (3 - 2 * ty);
    const c = (i: number, j: number) => rnd(((x0 + i) % cells + cells) % cells, ((y0 + j) % cells + cells) % cells, seed);
    return (c(0, 0) * (1 - sx) + c(1, 0) * sx) * (1 - sy) + (c(0, 1) * (1 - sx) + c(1, 1) * sx) * sy;
  };
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const v = 0.5 * valueNoise(x, y, 8, 1) + 0.3 * valueNoise(x, y, 32, 2) + 0.2 * valueNoise(x, y, 128, 3);
      const g = Math.round(255 * v);
      data.set([g, g, g, 255], (y * n + x) * 4);
    }
  }
  const tex = new THREE.DataTexture(data, n, n);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.anisotropy = 8;
  tex.needsUpdate = true;
  return tex;
};

const withGrain = (material: THREE.MeshLambertMaterial, sizeM: number) => {
  const grain = makeGrain();
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uGrain = {value: grain};
    shader.uniforms.uGrainRepeat = {value: sizeM / 7};
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
uniform sampler2D uGrain;
uniform float uGrainRepeat;`,
      )
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>
float grainV = texture2D(uGrain, vMapUv * uGrainRepeat).r;
float grainLum = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
diffuseColor.rgb = mix(diffuseColor.rgb, vec3(grainLum), 0.18);
diffuseColor.rgb *= 0.8 + 0.4 * grainV;`,
      );
  };
  material.customProgramCacheKey = () => "grain";
  return material;
};

// Pin de mapa 3D: perfil de gota girado (LatheGeometry), achatado, com o "furo" branco.
export const makePinGeometry = () => {
  const R = 0.36;
  const hc = 1 - R;
  const alpha = Math.asin(R / hc);
  const tl = Math.sqrt(hc * hc - R * R);
  const pts: THREE.Vector2[] = [new THREE.Vector2(0, 0)];
  const tx = tl * Math.sin(alpha);
  const ty = tl * Math.cos(alpha);
  for (let i = 1; i <= 8; i++) pts.push(new THREE.Vector2((tx * i) / 8, (ty * i) / 8));
  const phi0 = Math.atan2(ty - hc, tx);
  for (let i = 1; i <= 24; i++) {
    const phi = phi0 + ((Math.PI / 2 - phi0) * i) / 24;
    pts.push(new THREE.Vector2(Math.max(0, R * Math.cos(phi)), hc + R * Math.sin(phi)));
  }
  const body = new THREE.LatheGeometry(pts, 48);
  body.scale(1, 1, 0.62);
  body.computeVertexNormals();
  const hole = new THREE.CylinderGeometry(0.15, 0.15, 2 * R * 0.62 + 0.02, 32);
  hole.rotateX(Math.PI / 2);
  hole.translate(0, hc, 0);
  return {body, hole};
};

// Máscara de borda suave para a textura da cidade sobre a da região.
const makeEdgeAlpha = () => {
  const n = 128;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const e = Math.min(x, y, n - 1 - x, n - 1 - y) / (n * 0.12);
      const v = Math.round(255 * Math.min(1, Math.max(0, e)) ** 1.5);
      data.set([v, v, v, 255], (y * n + x) * 4);
    }
  }
  const tex = new THREE.DataTexture(data, n, n);
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
};

const routeRibbon = (assets: SceneAssets) => {
  const {points, along} = assets.json.route;
  const n = points.length;
  const pos = new Float32Array(n * 2 * 3);
  const nrm = new Float32Array(n * 2 * 2);
  const side = new Float32Array(n * 2);
  const al = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    const a = points[Math.max(0, i - 3)];
    const b = points[Math.min(n - 1, i + 3)];
    let dx = b[0] - a[0];
    let dz = b[1] - a[1];
    const L = Math.hypot(dx, dz) || 1;
    dx /= L;
    dz /= L;
    for (let k = 0; k < 2; k++) {
      const j = i * 2 + k;
      pos.set([points[i][0], 0, points[i][1]], j * 3);
      nrm.set([-dz, dx], j * 2);
      side[j] = k === 0 ? -1 : 1;
      al[j] = along[i];
    }
  }
  const idx: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    const a = i * 2;
    // anti-horário visto de cima (face da frente para +y)
    idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aNormal2", new THREE.BufferAttribute(nrm, 2));
  g.setAttribute("aSide", new THREE.BufferAttribute(side, 1));
  g.setAttribute("aAlong", new THREE.BufferAttribute(al, 1));
  g.setIndex(idx);
  g.computeBoundingSphere();
  g.boundingSphere!.radius += 200;
  return g;
};

const ribbonMaterial = (glow: boolean, length: number) =>
  new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    depthTest: true,
    side: THREE.DoubleSide,
    blending: glow ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: {
      uProgress: {value: 0},
      uHalfWidth: {value: 5},
      uLength: {value: length},
      uColorA: {value: new THREE.Color(ROUTE_COLORS.start)},
      uColorB: {value: new THREE.Color(ROUTE_COLORS.end)},
      uOpacity: {value: 1},
    },
    vertexShader: `
attribute vec2 aNormal2;
attribute float aSide;
attribute float aAlong;
uniform float uHalfWidth;
varying float vSide;
varying float vAlong;
void main() {
  vec3 p = position + vec3(aNormal2.x, 0.0, aNormal2.y) * aSide * uHalfWidth;
  p.y = ${glow ? "0.45" : "0.7"};
  vSide = aSide;
  vAlong = aAlong;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`,
    fragmentShader: `
uniform float uProgress;
uniform float uLength;
uniform vec3 uColorA;
uniform vec3 uColorB;
uniform float uOpacity;
varying float vSide;
varying float vAlong;
void main() {
  if (vAlong > uProgress) discard;
  float s = abs(vSide);
  vec3 col = mix(uColorA, uColorB, clamp(vAlong / uLength, 0.0, 1.0));
  float head = smoothstep(uProgress - 60.0, uProgress, vAlong);
  ${
    glow
      ? "float a = pow(1.0 - s, 2.0) * 0.55; col = mix(col, vec3(1.0), 0.25);"
      : "float a = smoothstep(1.0, 0.82, s); col = mix(col, vec3(1.0), smoothstep(0.42, 0.0, s) * 0.55 + head * 0.35);"
  }
  gl_FragColor = vec4(col, a * uOpacity);
}`,
  });

const skyMaterial = () =>
  new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {uHaze: {value: HAZE}, uZenith: {value: ZENITH}},
    vertexShader: `
varying vec3 vDir;
void main() {
  vDir = normalize(position);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform vec3 uHaze;
uniform vec3 uZenith;
varying vec3 vDir;
void main() {
  float h = clamp(vDir.y, 0.0, 1.0);
  gl_FragColor = vec4(mix(uHaze, uZenith, pow(h, 0.55)), 1.0);
}`,
  });

const ringMaterial = () =>
  new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {uPhase: {value: 0}, uOpacity: {value: 0}, uColor: {value: new THREE.Color("#ff3b6b")}},
    vertexShader: `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform float uPhase;
uniform float uOpacity;
uniform vec3 uColor;
varying vec2 vUv;
void main() {
  float r = length(vUv - 0.5) * 2.0;
  float a = 0.0;
  for (int i = 0; i < 3; i++) {
    float ph = fract(uPhase + float(i) / 3.0);
    a += smoothstep(0.06, 0.0, abs(r - ph)) * (1.0 - ph);
  }
  a += smoothstep(0.22, 0.0, r) * 0.6;
  gl_FragColor = vec4(uColor, a * uOpacity);
}`,
  });

const headGlowMaterial = () =>
  new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {uOpacity: {value: 0}, uColor: {value: new THREE.Color(ROUTE_COLORS.end)}},
    vertexShader: `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform float uOpacity;
uniform vec3 uColor;
varying vec2 vUv;
void main() {
  float r = length(vUv - 0.5) * 2.0;
  float halo = pow(max(0.0, 1.0 - r), 2.2);
  float core = smoothstep(0.24, 0.12, r);
  gl_FragColor = vec4(mix(uColor, vec3(1.0), core), (halo * 0.8 + core) * uOpacity);
}`,
  });

export const World: React.FC<{assets: SceneAssets}> = ({assets}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const {camera, scene} = useThree();
  const half = assets.json.detailHalf;
  const route = assets.json.route;
  const pois = assets.json.pois;

  const mats = useMemo(() => {
    const ground = new THREE.MeshLambertMaterial({map: assets.satRegion, depthWrite: false});
    const city = withGrain(
      new THREE.MeshLambertMaterial({map: assets.satCity, alphaMap: makeEdgeAlpha(), transparent: true, depthWrite: false}),
      assets.json.satellite.sat_city.size_m,
    );
    const roads = edgeFade(new THREE.MeshLambertMaterial({vertexColors: true, transparent: true, depthWrite: false}), half, "alpha");
    const water = edgeFade(
      new THREE.MeshPhongMaterial({vertexColors: true, shininess: 90, specular: new THREE.Color("#7fa9b8"), transparent: true, depthWrite: false}),
      half,
      "alpha",
    );
    const buildings = edgeFade(new THREE.MeshLambertMaterial({vertexColors: true}), half, "height");
    const trees = edgeFade(new THREE.MeshLambertMaterial({flatShading: true}), half, "instance");
    return {ground, city, roads, water, buildings, trees};
  }, [assets, half]);

  const ribbon = useMemo(() => routeRibbon(assets), [assets]);
  const ribbonMat = useMemo(() => ribbonMaterial(false, route.length), [route.length]);
  const glowMat = useMemo(() => ribbonMaterial(true, route.length), [route.length]);
  const sky = useMemo(() => skyMaterial(), []);
  const ring = useMemo(() => ringMaterial(), []);
  const startRing = useMemo(() => {
    const m = ringMaterial();
    m.uniforms.uColor.value = new THREE.Color(ROUTE_COLORS.start);
    return m;
  }, []);
  const headGlow = useMemo(() => headGlowMaterial(), []);
  const pin = useMemo(() => {
    const {body, hole} = makePinGeometry();
    const bodyMat = new THREE.MeshPhongMaterial({color: "#ff2d55", emissive: "#4a0014", shininess: 70, specular: new THREE.Color("#ffd0da")});
    const holeMat = new THREE.MeshLambertMaterial({color: "#ffffff", emissive: "#bbbbbb"});
    return {body, hole, bodyMat, holeMat};
  }, []);
  const treeGeo = useMemo(() => new THREE.IcosahedronGeometry(1, 0), []);
  const treeMeshes = useMemo(
    () =>
      assets.trees.map((c) => {
        const mesh = new THREE.InstancedMesh(treeGeo, mats.trees, c.matrices.length);
        c.matrices.forEach((m, i) => {
          mesh.setMatrixAt(i, m);
          mesh.setColorAt(i, c.colors[i]);
        });
        mesh.instanceMatrix.needsUpdate = true;
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.computeBoundingSphere();
        return mesh;
      }),
    [assets, mats.trees, treeGeo],
  );
  const sun = useMemo(() => {
    const l = new THREE.DirectionalLight("#fff1dc", 2.9);
    l.castShadow = true;
    l.shadow.mapSize.set(4096, 4096);
    l.shadow.bias = -0.00025;
    l.shadow.normalBias = 0.6;
    return l;
  }, []);
  const fog = useMemo(() => new THREE.Fog(HAZE, 1000, 5000), []);

  // Tudo que depende do frame é aplicado em useLayoutEffect: roda antes do render manual da Remotion.
  useLayoutEffect(() => {
    const cam = cameraAt(t, route, pois);
    const pc = camera as THREE.PerspectiveCamera;
    pc.position.set(...cam.position);
    pc.rotation.set(cam.rotation[0], cam.rotation[1], cam.rotation[2], "YXZ");
    pc.fov = cam.fov;
    pc.near = cam.near;
    pc.far = cam.far;
    pc.updateProjectionMatrix();
    pc.updateMatrixWorld();

    scene.fog = fog;
    fog.near = cam.dist * 1.5;
    fog.far = cam.dist * 5.2;

    // sombra acompanha o ponto que a câmera olha
    const [tx, tz] = cam.target;
    const S = Math.min(2600, Math.max(320, cam.dist * 1.25));
    sun.target.position.set(tx, 0, tz);
    sun.position.set(tx + SUN_DIR.x * 4000, SUN_DIR.y * 4000, tz + SUN_DIR.z * 4000);
    sun.target.updateMatrixWorld();
    const sc = sun.shadow.camera;
    sc.left = -S;
    sc.right = S;
    sc.top = S;
    sc.bottom = -S;
    sc.near = 1000;
    sc.far = 7000;
    sc.updateProjectionMatrix();

    // rota
    const s = routeProgress(route, t);
    const halfWidth = Math.max(4.2, cam.dist * 0.0105);
    for (const m of [ribbonMat, glowMat]) {
      m.uniforms.uProgress.value = s;
      m.uniforms.uHalfWidth.value = m === glowMat ? halfWidth * 2.8 : halfWidth;
    }
    ring.uniforms.uOpacity.value = Math.min(1, Math.max(0, (t - (T.arrive - 1.0)) / 1.0));
    ring.uniforms.uPhase.value = (t * 0.45) % 1;
    // anel na praça enquanto a narração fala do centro
    const inStart = Math.min(1, Math.max(0, (t - (T.descentEnd - 0.6)) / 0.6));
    const outStart = Math.min(1, Math.max(0, (T.routeStart + 2.0 - t) / 1.0));
    startRing.uniforms.uOpacity.value = inStart * outStart;
    startRing.uniforms.uPhase.value = (t * 0.6) % 1;
    // brilho na ponta da rota, só enquanto ela anda
    const on = Math.min(1, Math.max(0, (t - T.routeStart) / 0.4)) * Math.min(1, Math.max(0, (T.arrive + 0.3 - t) / 0.5));
    headGlow.uniforms.uOpacity.value = on;
  }, [t, camera, scene, route, pois, sun, fog, ribbonMat, glowMat, ring, startRing, headGlow]);

  const cam = cameraAt(t, route, pois);
  const skyRadius = 0.8 * cam.far;
  const camPos = cam.position;
  // pin da loja: cai com um quique quando a rota começa, mantém tamanho legível de longe
  const store = pois.store;
  const pinH = Math.max(30, cam.dist * 0.095);
  const drop = Math.min(1, Math.max(0, (t - (T.routeStart + 0.2)) / 0.8));
  const easeOutBack = (x: number) => 1 + 2.4 * Math.pow(x - 1, 3) + 1.4 * Math.pow(x - 1, 2);
  const pop = 1 + 0.18 * Math.exp(-Math.pow((t - T.arrive) / 0.35, 2));
  const pinScale = pinH * (drop <= 0 ? 0 : easeOutBack(drop)) * pop;
  const pinY = 3 + pinH * 0.07 * Math.sin(t * 2.4) + (1 - Math.min(1, drop * 1.4)) * pinH * 2;
  const pinYaw = Math.atan2(camPos[0] - store[0], camPos[2] - store[1]);
  const head = routePoint(route, routeProgress(route, t));
  const headSize = Math.max(4.2, cam.dist * 0.0105) * 7;

  return (
    <>
      <hemisphereLight args={["#d8e8ff", "#8a7a5a", 1.35]} />
      <primitive object={sun} />
      <primitive object={sun.target} />

      <mesh material={sky} position={camPos} renderOrder={-10} frustumCulled={false}>
        <sphereGeometry args={[skyRadius, 32, 16]} />
      </mesh>

      <mesh material={mats.ground} rotation={[-Math.PI / 2, 0, 0]} renderOrder={-5} receiveShadow>
        <planeGeometry args={[assets.json.satellite.sat_region.size_m, assets.json.satellite.sat_region.size_m]} />
      </mesh>
      <mesh material={mats.city} rotation={[-Math.PI / 2, 0, 0]} renderOrder={-4} receiveShadow>
        <planeGeometry args={[assets.json.satellite.sat_city.size_m, assets.json.satellite.sat_city.size_m]} />
      </mesh>

      {assets.roads.map((g, i) => (
        <mesh key={`r${i}`} geometry={g} material={mats.roads} renderOrder={-3} receiveShadow />
      ))}
      {assets.water.map((g, i) => (
        <mesh key={`w${i}`} geometry={g} material={mats.water} renderOrder={-2} />
      ))}

      <mesh geometry={ribbon} material={glowMat} renderOrder={5} frustumCulled={false} />
      <mesh geometry={ribbon} material={ribbonMat} renderOrder={6} frustumCulled={false} />

      {assets.buildings.map((g, i) => (
        <mesh key={`b${i}`} geometry={g} material={mats.buildings} castShadow receiveShadow />
      ))}
      {treeMeshes.map((m, i) => (
        <primitive key={`t${i}`} object={m} />
      ))}

      {pinScale > 0.01 ? (
        <group position={[store[0], pinY, store[1]]} rotation={[0, pinYaw, 0]} scale={pinScale}>
          <mesh geometry={pin.body} material={pin.bodyMat} castShadow />
          <mesh geometry={pin.hole} material={pin.holeMat} />
        </group>
      ) : null}
      <mesh material={ring} position={[pois.store[0], 0.9, pois.store[1]]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={7}>
        <planeGeometry args={[70, 70]} />
      </mesh>
      <mesh material={startRing} position={[pois.praca[0], 0.9, pois.praca[1]]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={7}>
        <planeGeometry args={[150, 150]} />
      </mesh>
      <mesh material={headGlow} position={[head[0], 1.0, head[1]]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={9} scale={headSize}>
        <planeGeometry args={[1, 1]} />
      </mesh>
    </>
  );
};
