import React from "react";
import {AbsoluteFill, Sequence, staticFile} from "remotion";
import {Audio} from "@remotion/media";
import {Cortina, Fundo, Legendas} from "./componentes/global";
import {Brasil} from "./cenas/Brasil";
import {Cerebro} from "./cenas/Cerebro";
import {DezMil} from "./cenas/DezMil";
import {Fechamento} from "./cenas/Fechamento";
import {Fontes} from "./cenas/Fontes";
import {Gancho} from "./cenas/Gancho";
import {Importancia} from "./cenas/Importancia";
import {Lanchinhos} from "./cenas/Lanchinhos";
import {Mundo} from "./cenas/Mundo";
import {Recomendacao} from "./cenas/Recomendacao";
import {Sentado} from "./cenas/Sentado";
import {SeteMil} from "./cenas/SeteMil";
import {FPS} from "./tema";
import {DURACAO, TL, quadro, todasAsFalas} from "./tl";

const CENAS: Record<string, React.FC> = {
  gancho: Gancho,
  importancia: Importancia,
  recomendacao: Recomendacao,
  mundo: Mundo,
  brasil: Brasil,
  dezmil: DezMil,
  setemil: SeteMil,
  lanchinhos: Lanchinhos,
  cerebro: Cerebro,
  sentado: Sentado,
  fechamento: Fechamento,
  fontes: Fontes,
};

const CORTINA = 20; // quadros; o corte acontece no meio

// volume da trilha: mais baixo enquanto a voz fala (ducking), com rampas suaves
const MUSICA_LIVRE = 0.39;
const MUSICA_SOB_VOZ = 0.12;
const VOLUME_MUSICA = (() => {
  const n = DURACAO + FPS;
  const alvo = new Array<number>(n).fill(MUSICA_LIVRE);
  for (const f of todasAsFalas()) {
    const a = Math.max(0, Math.round((f.s - 0.25) * FPS));
    const b = Math.min(n, Math.round((f.e + 0.35) * FPS));
    for (let i = a; i < b; i++) alvo[i] = MUSICA_SOB_VOZ;
  }
  const janela = 7;
  return alvo.map((_, i) => {
    let soma = 0;
    let c = 0;
    for (let k = i - janela; k <= i + janela; k++) {
      if (k >= 0 && k < n) {
        soma += alvo[k];
        c++;
      }
    }
    return soma / c;
  });
})();

export const Video: React.FC = () => {
  return (
    <AbsoluteFill>
      <Fundo />
      {TL.cenas.map((c) => {
        const Cena = CENAS[c.id];
        const de = quadro(c.s);
        return (
          <Sequence key={c.id} name={c.id} from={de} durationInFrames={quadro(c.e) - de}>
            <Cena />
          </Sequence>
        );
      })}
      {TL.cenas.slice(1).map((c) => (
        <Sequence key={`cortina-${c.id}`} name={`cortina ${c.id}`} from={quadro(c.s) - CORTINA / 2} durationInFrames={CORTINA}>
          <Cortina dur={CORTINA} />
        </Sequence>
      ))}
      {TL.cenas.slice(1).map((c) => (
        <Sequence key={`whoosh-${c.id}`} from={quadro(c.s) - CORTINA / 2 - 2} durationInFrames={30} layout="none">
          <Audio src={staticFile("sfx/whoosh.wav")} volume={0.2} />
        </Sequence>
      ))}
      <Legendas />
      <Audio src={staticFile("narracao.wav")} />
      <Audio src={staticFile("trilha.wav")} volume={(f) => VOLUME_MUSICA[Math.min(f, VOLUME_MUSICA.length - 1)]} />
    </AbsoluteFill>
  );
};
