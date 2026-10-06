# Padrão de edição

Padrão para os vídeos de fala direta (talking head) em formato Reels/TikTok. O objetivo é que os vídeos fiquem com a sua voz e o seu jeito de falar, com um acabamento consistente e sem exagero.

## Princípios de autenticidade

- **A fala é a estrela.** Motion graphics só destacam o que você já disse; nunca substituem a fala nem inventam informação.
- **Não crie números, depoimentos ou resultados.** Gráficos e barras são ilustrativos, sem valores reais, a menos que você informe os dados.
- **Mantenha os seus bordões e repetições** ("Hoje, o Claude ... pra mim", "Tudo bonitinho!", "Tchau, tchau"). São parte da sua identidade.
- **Corrija a fala, não a personalidade.** Tire tropeços, recomeços e pausas longas. Mantenha gírias e expressões que você usa de propósito.
- **Efeito com moderação.** No máximo um motion ao mesmo tempo, sempre ligado a um item ou a uma palavra-chave.

## Estrutura

1. **Gancho / título** (0–4 s): palavras entrando em grande e translúcido, com o assunto do vídeo.
2. **Itens numerados** (cada um com um cartão `01`, `02`...): o cartão aparece quando você começa o item e some antes do próximo.
3. **Apoio visual** (opcional): um gráfico ilustrativo ou um cartão flutuando com o nome da ferramenta, só quando combinar com a fala.
4. **Chamada para comentar** (último trecho): botão "Comenta: PARTE 2" ou equivalente.

## Cortes

- Remova pausas maiores que **0,5 s**; deixe **0,2 s** de respiro em cada lado.
- Remova recomeços: quando você começa uma frase de novo, mantenha só a última versão.
- Não corte palavras no meio. Confira a transcrição palavra por palavra antes de cortar.
- Trechos de gravação repetidos (mesmo título gravado duas vezes): fique com a melhor tomada.

## Legendas

- Fonte: **Arial, negrito**. Tamanho **58** (em 1080x1920).
- Cor branca, com contorno preto de 4 px. Destaque amarelo `#FFD400` só se for usar.
- Até **4 palavras por linha**, na parte inferior, com margem de **360 px** (fica fora da área dos ícones do Reels).
- Ortografia: passe pelo glossário (`glossario.json`) e revise as palavras que a transcrição erra. Nomes de marcas e da comunidade devem ser confirmados por você.

## Motion graphics (paleta e estilo)

- Cores: preto `#111111`, amarelo `#FFD400`, branco `#FFFFFF`. Não use logos oficiais de marcas de terceiros.
- Cartões: retângulos arredondados (raio 18 px), entrada com mola (`spring`), saída em fade.
- Animações de texto: palavras entrando uma a uma com atraso de 4 frames.
- Gráficos: barras preenchendo em sequência, sem números.
- Ferramenta: Remotion (skill em `skills/remotion-best-practices`). O código do overlay está em `pipeline/motion/`.

## Formato de exportação

- 1080x1920, 30 fps, H.264 (CRF 20), áudio AAC 192 kbps.
- Overlay de motion em ProRes 4444 com canal alfa, composto antes das legendas.
- Um vídeo de cerca de 70 s fica em torno de 80 MB.

## Checklist antes de publicar

- [ ] Pausas longas e recomeços removidos
- [ ] Ortografia conferida (glossário)
- [ ] Nomes de marcas e da comunidade confirmados
- [ ] Bordões e repetições mantidos
- [ ] Motion sem números inventados
- [ ] Legendas legíveis e fora dos ícones do Reels
- [ ] Exportado em 1080x1920
