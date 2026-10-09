import {loadFont} from "@remotion/fonts";
import archivo from "@fontsource-variable/archivo/files/archivo-latin-standard-normal.woff2";
import inter from "@fontsource-variable/inter/files/inter-latin-standard-normal.woff2";
import jp109 from "@fontsource/noto-sans-jp/files/noto-sans-jp-109-900-normal.woff2";
import jp111 from "@fontsource/noto-sans-jp/files/noto-sans-jp-111-900-normal.woff2";
import jp112 from "@fontsource/noto-sans-jp/files/noto-sans-jp-112-900-normal.woff2";

// Identidade visual: azul-noite, verde-limão (energia), coral (alerta) e ciano (dados)
export const COR = {
  fundo: "#0A0F1F",
  painel: "#121A31",
  painel2: "#18223F",
  borda: "rgba(255,255,255,0.09)",
  texto: "#F3F5FA",
  apagado: "#8F98B8",
  limao: "#C5F536",
  coral: "#FF5B4A",
  ciano: "#38C6F0",
  amarelo: "#FFD23F",
};

export const FONTE = {
  titulo: "Archivo",
  texto: "Inter",
  jp: "Noto Sans JP",
};

// fontes variáveis: peso 100–900 e largura 62–125% (Archivo)
loadFont({family: FONTE.titulo, url: archivo, weight: "100 900", stretch: "62% 125%"});
loadFont({family: FONTE.texto, url: inter, weight: "100 900"});
loadFont({family: FONTE.jp, url: jp109, weight: "900", unicodeRange: "U+6B69"});
loadFont({family: FONTE.jp, url: jp111, weight: "900", unicodeRange: "U+4E07"});
loadFont({family: FONTE.jp, url: jp112, weight: "900", unicodeRange: "U+8A08"});

export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const MARGEM = 120;
