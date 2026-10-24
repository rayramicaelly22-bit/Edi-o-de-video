import type {SceneJson} from "../scene/load";
import sceneJson from "../../public/scene/scene.json";
import narrationJson from "../../public/audio/narration.json";

export type Word = {text: string; start: number; end: number};
export type Caption = {text: string; start: number; end: number; words: Word[]};
export type NarrationLine = {id: string; text: string; start: number; end: number; words: Word[]; captions: Caption[]};

export const SCENE = sceneJson as unknown as SceneJson;
export const NARRATION = narrationJson as unknown as {voice: string; lines: NarrationLine[]};

export const lineById = (id: string) => {
  const line = NARRATION.lines.find((l) => l.id === id);
  if (!line) throw new Error(`Fala não encontrada: ${id}`);
  return line;
};

// Início (s) da primeira palavra da fala `id` que começa com `prefix` (para sincronizar elementos com a voz)
export const wordTime = (id: string, prefix: string) => {
  const w = lineById(id).words.find((x) => x.text.toLowerCase().startsWith(prefix.toLowerCase()));
  if (!w) throw new Error(`Palavra "${prefix}" não encontrada na fala ${id}`);
  return w.start;
};
