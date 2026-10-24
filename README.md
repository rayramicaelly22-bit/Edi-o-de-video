# Edição de vídeo

Repositório para edição de vídeos, com skills do Claude Code para edição e motion graphics.

## Skills incluídas

Pasta `skills/remotion-best-practices/`: skill oficial da Remotion (React para vídeo), que cobre:

- **motion graphics e animações** (`remotion-markup`): títulos, transições, layout, tipografia, timing
- **legendas** (`remotion-captions`): transcrição e exibição de legendas SRT
- **áudio e mídia** (`remotion-multimedia`): vídeos, áudio e imagens
- **criação de projeto** (`remotion-create`) e **preview** (`remotion-studio`)
- **renderização** (`remotion-render`): exporta o vídeo final
- **mapas** (`remotion-maps`): rotas animadas, marcadores, MapLibre/Mapbox/MapTiler e voos 3D (Cesium)
- **interatividade** (`remotion-interactivity`) e **apps/SaaS** (`remotion-saas`)

Origem: https://github.com/remotion-dev/skills (copiada da branch `main`, versão 4.0.538, commit `6c67adc`).

## Projetos

- [`projetos/localizacao-loja/`](projetos/localizacao-loja): vídeo de Stories (9:16) mostrando, como um voo de
  drone, o caminho do centro de Paragominas até a loja, com mapa 3D gerado de dados abertos, narração com IA,
  trilha e motion graphics.

## Como usar

Copie a pasta para a skills do Claude Code:

```bash
cp -r skills/remotion-best-practices ~/.claude/skills/
```

Ou instale direto pelo repositório oficial:

```bash
npx skills add remotion-dev/skills
```

Depois, no Claude Code, use `/remotion-best-practices` ou um dos subcomandos acima.

## Observações

- A Remotion precisa de Node.js instalado para renderizar (`npx create-video`).
- O repositório original não declara licença; confira os termos antes de redistribuir.
