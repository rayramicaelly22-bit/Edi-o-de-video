# Pipeline de edição

Scripts usados para editar os vídeos seguindo o [padrão de edição](../padrao-de-edicao/PADRAO.md).

## Etapas

1. **Áudio**: extrair um WAV de 16 kHz mono de cada vídeo com FFmpeg.
2. **Transcrição** (`transcribe.py`): faster-whisper em português, com timestamps por palavra. Gera um JSON por vídeo.
3. **Revisão de tempos** (`words.py`): mostra as palavras de um trecho, para achar pausas e recomeços.
4. **Montagem** (`build.py`): corta os trechos na vertical 1080x1920, concatena, aplica o overlay de motion e queima as legendas corrigidas pelo glossário.
5. **Motion** (`motion/`): projeto Remotion que gera o overlay com alfa (`npx remotion render Overlay out/overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png`).

## Antes de rodar em um vídeo novo

- Ajuste a lista `CLIPS` em `build.py` com os arquivos e os trechos (início e fim em segundos).
- Ajuste os tempos dos cartões de item e do gráfico em `motion/src/Overlay.tsx`.
- Confirme as correções do `glossario.json` (ele fica em `padrao-de-edicao/`).

## Observações

- Os caminhos de origem (`C:\Users\layla\Downloads`) estão fixos nos scripts. Troque se os vídeos estiverem em outra pasta.
- O `transcribe.py` lê o WAV com numpy, porque a versão do PyAV instalada aqui não abre o `.MOV` diretamente.
- Os vídeos brutos e os renders não são versionados.
