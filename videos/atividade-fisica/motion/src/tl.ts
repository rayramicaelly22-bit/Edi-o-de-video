import {useCurrentFrame} from "remotion";
import timeline from "./timeline.json";
import {FPS} from "./tema";

// timeline.json é gerado pelo narracao.py (tempos em segundos)
export type Palavra = {w: string; s: number; e: number};
export type Fala = {id: string; texto: string; s: number; e: number; palavras: Palavra[]};
export type Cena = {id: string; s: number; e: number; falas: Fala[]};
export type Legenda = {texto: string; s: number; e: number};

export const TL = timeline as {duracao: number; cenas: Cena[]; legendas: Legenda[]};
export const quadro = (seg: number) => Math.round(seg * FPS);
export const DURACAO = quadro(TL.duracao);

export const cena = (id: string): Cena => {
  const c = TL.cenas.find((x) => x.id === id);
  if (!c) throw new Error(`cena não encontrada: ${id}`);
  return c;
};

export const todasAsFalas = (): Fala[] => TL.cenas.flatMap((c) => c.falas);

const normal = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}-]/gu, "");

// início (em segundos) da n-ésima palavra da fala que começa com o prefixo
export const palavra = (falaId: string, prefixo: string, n = 1): number => {
  const f = todasAsFalas().find((x) => x.id === falaId);
  if (!f) throw new Error(`fala não encontrada: ${falaId}`);
  const achadas = f.palavras.filter((p) => normal(p.w).startsWith(normal(prefixo)));
  if (achadas.length < n) throw new Error(`palavra "${prefixo}" não encontrada em ${falaId}`);
  return achadas[n - 1].s;
};

// dentro de uma cena: quadro local atual e conversores de tempo absoluto -> quadro local
export const useCena = (id: string) => {
  const c = cena(id);
  const frame = useCurrentFrame();
  const local = (seg: number) => quadro(seg - c.s);
  return {
    frame,
    dur: quadro(c.e - c.s),
    // quadro local em que a palavra é dita
    em: (falaId: string, prefixo: string, n = 1) => local(palavra(falaId, prefixo, n)),
    // quadros locais de início e fim de uma fala
    fala: (falaId: string) => {
      const f = c.falas.find((x) => x.id === falaId);
      if (!f) throw new Error(`fala ${falaId} não está na cena ${id}`);
      return {s: local(f.s), e: local(f.e)};
    },
  };
};
