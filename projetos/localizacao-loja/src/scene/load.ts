import * as THREE from "three";
import {staticFile} from "remotion";

type BufferRef = {offset: number; length: number; type: string};
type MeshLayer = {count: number; position: BufferRef; normal: BufferRef; color: BufferRef};
type TreeLayer = {count: number; stride: number; data: BufferRef};

export type SceneJson = {
  origin: {lon: number; lat: number; crs: string};
  detailHalf: number;
  satellite: Record<string, {size_m: number; px: number}>;
  layers: {roads: MeshLayer; water: MeshLayer; buildings: MeshLayer; trees: TreeLayer};
  route: {points: [number, number][]; along: number[]; length: number; steps: {name: string; from: number; to: number}[]};
  pois: Record<string, [number, number]>;
  store: {number: number};
};

export type TreeChunk = {matrices: THREE.Matrix4[]; colors: THREE.Color[]};

export type SceneAssets = {
  json: SceneJson;
  roads: THREE.BufferGeometry[];
  water: THREE.BufferGeometry[];
  buildings: THREE.BufferGeometry[];
  trees: TreeChunk[];
  satRegion: THREE.Texture;
  satCity: THREE.Texture;
};

const CHUNK = 512;

// Os bytes de cor vêm em sRGB; a iluminação do three.js trabalha em espaço linear.
const SRGB_TO_LINEAR = (() => {
  const t = new Float32Array(256);
  for (let i = 0; i < 256; i++) {
    t[i] = new THREE.Color().setRGB(i / 255, 0, 0, THREE.SRGBColorSpace).r;
  }
  return t;
})();

const view = (bin: ArrayBuffer, ref: BufferRef) => {
  switch (ref.type) {
    case "float32":
      return new Float32Array(bin, ref.offset, ref.length);
    case "int8":
      return new Int8Array(bin, ref.offset, ref.length);
    case "uint8":
      return new Uint8Array(bin, ref.offset, ref.length);
    default:
      throw new Error(`Tipo de buffer desconhecido: ${ref.type}`);
  }
};

const chunkKey = (x: number, z: number) => `${Math.floor(x / CHUNK)}:${Math.floor(z / CHUNK)}`;

// Divide uma malha de triângulos soltos em blocos de 512 m (culling por bloco).
const splitIntoChunks = (bin: ArrayBuffer, layer: MeshLayer): THREE.BufferGeometry[] => {
  const pos = view(bin, layer.position) as Float32Array;
  const nrm = view(bin, layer.normal) as Int8Array;
  const col = view(bin, layer.color) as Uint8Array;
  const triCount = layer.count / 3;
  const groups = new Map<string, number[]>();
  for (let t = 0; t < triCount; t++) {
    const i = t * 9;
    const key = chunkKey(pos[i], pos[i + 2]);
    let g = groups.get(key);
    if (!g) {
      g = [];
      groups.set(key, g);
    }
    g.push(t);
  }
  const out: THREE.BufferGeometry[] = [];
  for (const tris of groups.values()) {
    const n = tris.length * 3;
    const p = new Float32Array(n * 3);
    const nn = new Int8Array(n * 3);
    const c = new Float32Array(n * 3);
    tris.forEach((t, k) => {
      for (let j = 0; j < 9; j++) {
        p[k * 9 + j] = pos[t * 9 + j];
        nn[k * 9 + j] = nrm[t * 9 + j];
        c[k * 9 + j] = SRGB_TO_LINEAR[col[t * 9 + j]];
      }
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(p, 3));
    g.setAttribute("normal", new THREE.BufferAttribute(nn, 3, true));
    g.setAttribute("color", new THREE.BufferAttribute(c, 3));
    g.computeBoundingSphere();
    out.push(g);
  }
  return out;
};

const loadTexture = (url: string) =>
  new Promise<THREE.Texture>((resolve, reject) => {
    new THREE.TextureLoader().load(
      url,
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.generateMipmaps = true;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.anisotropy = 16;
        resolve(tex);
      },
      undefined,
      reject,
    );
  });

export const loadScene = async (): Promise<SceneAssets> => {
  const [json, bin, satRegion, satCity] = await Promise.all([
    fetch(staticFile("scene/scene.json")).then((r) => r.json() as Promise<SceneJson>),
    fetch(staticFile("scene/scene.bin")).then((r) => r.arrayBuffer()),
    loadTexture(staticFile("scene/sat_region.jpg")),
    loadTexture(staticFile("scene/sat_city.jpg")),
  ]);

  // Árvores: [x, yCentro, z, sx, sy, sz, rotY, r, g, b]
  const tl = json.layers.trees;
  const td = view(bin, tl.data) as Float32Array;
  const treeGroups = new Map<string, TreeChunk>();
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < tl.count; i++) {
    const o = i * tl.stride;
    const key = chunkKey(td[o], td[o + 2]);
    let g = treeGroups.get(key);
    if (!g) {
      g = {matrices: [], colors: []};
      treeGroups.set(key, g);
    }
    q.setFromAxisAngle(up, td[o + 6]);
    m.compose(new THREE.Vector3(td[o], td[o + 1], td[o + 2]), q, new THREE.Vector3(td[o + 3], td[o + 4], td[o + 5]));
    g.matrices.push(m.clone());
    g.colors.push(new THREE.Color().setRGB(td[o + 7], td[o + 8], td[o + 9], THREE.SRGBColorSpace));
  }

  return {
    json,
    roads: splitIntoChunks(bin, json.layers.roads),
    water: splitIntoChunks(bin, json.layers.water),
    buildings: splitIntoChunks(bin, json.layers.buildings),
    trees: [...treeGroups.values()],
    satRegion,
    satCity,
  };
};
