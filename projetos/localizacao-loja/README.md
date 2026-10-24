# Vídeo de localização da loja (Stories 9:16)

Vídeo de 36 s em 1080x1920 que mostra, como num voo de drone, o caminho do centro de Paragominas (Praça Célio
Miranda) até a loja na **Av. Barão de Araruna, 885 — Promissão**, perto do Hospital São Paulo, em frente à
Júnior Bike e ao lado da Vila Pet. Tudo é gerado por código: mapa 3D, voo, motion graphics, narração com IA,
trilha e efeitos.

## Como foi feito

| Etapa | Script | O que faz |
| --- | --- | --- |
| 1 | `scripts/fetch_overture.py` | Baixa ruas, prédios, água e pontos comerciais de Paragominas do Overture Maps (S3 público). |
| 2 | `scripts/route.py` | Rota de carro (respeita mão única, prefere avenidas) da praça até a loja. |
| 3 | `scripts/fetch_satellite.py` | Imagens Sentinel-2 sem nuvem (ago–out/2026) em duas escalas + NDVI para as árvores. |
| 4 | `scripts/build_scene.py` | Geometria 3D: ruas com calçada e faixa, 28 mil prédios (telhado de quatro águas com cor tirada do satélite), água e ~29 mil árvores onde o satélite vê vegetação. |
| 5 | `scripts/narration.py` | Narração com o Supertonic 3 (local), encaixada nos momentos do voo; tempos de cada palavra para as legendas. |
| 6 | `scripts/audio.py` | Trilha sintetizada (Mi maior, 124,7 BPM, compassos alinhados com início da rota, virada e chegada), efeitos e mixagem com ducking. |
| 7 | `npx remotion render Drone3D out/drone3d.mp4 --gl=swangle` | Renderiza o voo 3D (Three.js na Remotion). |
| 8 | `scripts/grade.sh` | Tilt-shift de drone, contraste, cor e vinheta. |
| 9 | `scripts/finalize.sh` | Motion graphics + legendas por cima do voo e áudio normalizado em -14 LUFS. |

A linha do tempo fica em `src/timeline.json` (fonte única para câmera, overlays e áudio). A câmera é uma função
pura do tempo (`src/scene/camera.ts`), usada tanto no render 3D quanto para prender as etiquetas aos pontos do mapa.

## Rodando de novo

Precisa de Node 22, Python 3 com `pyarrow shapely pyproj rasterio networkx scipy pillow sherpa-onnx soundfile`,
FFmpeg e acesso de rede ao S3 (Overture, Sentinel-2) e ao GitHub (modelos de voz). Os downloads e os assets
pesados não são versionados (ver `.gitignore`).

```bash
cd projetos/localizacao-loja && npm install
cd scripts
python fetch_overture.py && python route.py && python fetch_satellite.py && python build_scene.py
# modelo de voz: sherpa-onnx-supertonic-3-tts-int8-2026-05-11 (release "tts-models" do k2-fsa/sherpa-onnx) em .cache/tts/
python narration.py && python audio.py
cd .. && npx remotion render Drone3D out/drone3d.mp4 --gl=swangle --concurrency=2 --crf=10
scripts/grade.sh out/drone3d.mp4 public/render/drone3d_graded.mp4
scripts/finalize.sh out/localizacao-loja.mp4
```

Para trocar a voz, o texto ou o ritmo: edite `LINES`, `VOICE_SID` (0–4 femininas, 5–9 masculinas) ou `SPEED`
em `scripts/narration.py` e rode os passos 5, 6 e 9 (o voo 3D só precisa ser refeito se `src/timeline.json` mudar
antes da chegada na loja).

## Premissas sobre a localização

- A Av. Barão de Araruna tem numeração métrica (nº ≈ metros desde o início, a sudeste), confirmada pelos
  endereços de pontos comerciais próximos. O nº 885 fica a ~925 m do início da avenida, ~140 m depois do
  Hospital São Paulo (nº 737), no lado dos números ímpares (sudoeste). Margem estimada: ±30 m.
- Júnior Bike e Vila Pet não aparecem na base de dados; a etiqueta da Júnior Bike fica do outro lado da avenida,
  em frente à loja, e a Vila Pet aparece só no cartão.
- Para ajustar o ponto exato, mude `STORE_ALONG_M` / `STORE_SIDE_OFFSET_M` em `scripts/config.py`.

## Créditos dos dados e modelos

- Mapa: © colaboradores do OpenStreetMap (ODbL), Overture Maps Foundation, Google Open Buildings (CC BY 4.0).
- Imagem de satélite: contém dados modificados do Copernicus Sentinel-2 (2026), processados pela Element 84.
- Voz: Supertonic 3 (Supertone Inc., OpenRAIL-M), via sherpa-onnx. Conferência de pronúncia: Whisper turbo.
- Fonte: Montserrat (SIL OFL 1.1, via @fontsource).
- Trilha e efeitos: sintetizados em `scripts/audio.py`.
