# Atividade física: importância, dados e curiosidades

Vídeo explicativo todo em motion graphics, com narração por IA.

- **Formato:** horizontal 16:9, 1920x1080, 30 fps, H.264 + AAC
- **Duração:** 2min47s
- **Voz:** Kokoro, voz `pm_alex` (português do Brasil), gerada localmente
- **Trilha:** original, composta por código (`trilha.py`), sem direitos de terceiros
- **Identidade visual:** azul-noite `#0A0F1F` com verde-limão `#C5F536`, coral `#FF5B4A`, ciano `#38C6F0` e amarelo `#FFD23F`; títulos em Archivo e textos em Inter
- **Legendas:** queimadas no vídeo, sincronizadas com a narração

## Estrutura

| Cena | O que mostra |
| --- | --- |
| Gancho | Cápsula de "remédio" com os benefícios e título "Atividade física" |
| 01 · Por que se mexer | Cartões com a redução de risco (OMS) e o risco maior de quem não se mexe |
| 02 · A recomendação | 150–300 min/semana moderada ou 75–150 intensa, semana preenchida, força 2× |
| 03 · Os dados | 31% dos adultos do mundo (1,8 bilhão), tendência até 2030 e adolescentes |
| 03 · Brasil | 42,3% dos adultos das capitais (2024) contra 30,3% (2009) |
| 04 · Curiosidades | Os 10 mil passos e o manpo-kei, 7 mil passos, "lanchinhos" de exercício, cérebro, tempo sentado |
| 05 · Resumindo | "Cada movimento conta" e dicas para começar |
| Fontes | Lista das referências |

O texto completo da narração está em [`roteiro.json`](roteiro.json).

## Fontes dos dados

- OMS. *WHO guidelines on physical activity and sedentary behaviour* (2020). Recomendações de 150–300 min/semana de atividade moderada ou 75–150 de intensa, força 2× por semana.
- OMS. [Investing in physical activity](https://www.who.int/health-topics/physical-activity/investing-in-physical-activity): redução de risco de doenças do coração e AVC (19%), diabetes (17%), depressão e demência (28–32%) e vários tipos de câncer (8–28%).
- OMS. [Fact sheet sobre atividade física](https://www.who.int/news-room/fact-sheets/detail/physical-activity): risco de morte 20–30% maior para quem não é ativo o suficiente; mais de 80% dos adolescentes insuficientemente ativos (dados de 2016).
- Strain et al. *The Lancet Global Health* (2024), divulgado pela [OMS](https://www.who.int/news/item/26-06-2024-nearly-1.8-billion-adults-at-risk-of-disease-from-not-doing-enough-physical-activity): 31% dos adultos (1,8 bilhão) não atingiram o mínimo em 2022; projeção de 35% em 2030; série 23,4% (2000), 26,4% (2010), 31,3% (2022).
- Ministério da Saúde. *Vigitel Brasil 2006–2024*: atividade física no tempo livre (150+ min/semana) em adultos das capitais passou de 30,3% (2009) para 42,3% (2024).
- Lee et al. *Association of Step Volume and Intensity With All-Cause Mortality in Older Women*. JAMA Internal Medicine (2019): origem da meta de 10 mil passos no pedômetro japonês manpo-kei.
- Ding et al. *Daily steps and health outcomes in adults: a systematic review and dose-response meta-analysis*. The Lancet Public Health (2025): 7.000 passos/dia ligados a risco de morte 47% menor que 2.000 passos/dia.
- Stamatakis et al. *Association of wearable device-measured vigorous intermittent lifestyle physical activity with mortality*. Nature Medicine (2022): em quem não treinava, 3 explosões de 1–2 min/dia ligadas a risco de morte 38–40% menor.
- Erickson et al. *Exercise training increases size of hippocampus and improves memory*. PNAS (2011): um ano de caminhadas aumentou o hipocampo em cerca de 2% em idosos.
- Ekelund et al. *Does physical activity attenuate, or even eliminate, the detrimental association of sitting time with mortality?* The Lancet (2016): 60–75 min/dia de atividade moderada parecem anular o risco extra de ficar mais de 8 h/dia sentado.

Os estudos observacionais mostram associação, não causa. A narração usa "ligado a" e "parece" nesses casos.

## Como refazer o vídeo

Requisitos: Python 3, Node.js 18+, FFmpeg e um Chromium (o Remotion baixa um sozinho se não houver).

1. **Ambiente Python** (fora do repositório):

   ```bash
   python3 -m venv venv
   venv/bin/pip install kokoro-onnx soundfile pedalboard scipy pyloudnorm
   ```

2. **Modelo de voz** (cerca de 350 MB, fora do repositório):

   ```bash
   mkdir modelos && cd modelos
   curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
   curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
   ```

3. **Narração e linha do tempo:** `venv/bin/python narracao.py modelos`. Gera `motion/public/narracao.wav` e `motion/src/timeline.json` (tempos de cada cena, fala, palavra e legenda).
4. **Trilha e efeitos:** `venv/bin/python trilha.py`. Gera `motion/public/trilha.wav` e `motion/public/sfx/`.
5. **Animação:** dentro de `motion/`, rode `npm install` e depois `npx remotion render AtividadeFisica out/video_bruto.mp4 --crf=18 --audio-bitrate=320k`. Para ver e ajustar no navegador, use `npm run studio`.
6. **Áudio final:** `python3 finalizar.py`. Ajusta o volume para -14 LUFS e grava `motion/out/atividade-fisica.mp4`.

Para mudar o texto, edite `roteiro.json` e rode de novo os passos 3 a 6: as cenas se ajustam sozinhas aos novos tempos, porque cada animação está presa à palavra em que ela é dita (veja `useCena` em `motion/src/tl.ts`). Se uma palavra usada como gatilho sair do texto, o render para com o erro `palavra "..." não encontrada`.

Os arquivos de áudio e vídeo não são versionados (veja o `.gitignore`).
