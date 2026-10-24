import {continueRender, delayRender, staticFile} from "remotion";

export const COLORS = {
  ink: "#0b1f3a",
  inkSoft: "rgba(11, 31, 58, 0.86)",
  white: "#ffffff",
  route: "#2f7dff",
  routeLight: "#19d3ff",
  pin: "#ff2d55",
  highlight: "#ffd60a",
  muted: "#9fb3c8",
};

export const FONT = "Montserrat";

// Montserrat (OFL-1.1, via @fontsource) carregada dos arquivos locais em public/fonts.
let fontsRequested = false;
export const loadFonts = () => {
  if (fontsRequested || typeof document === "undefined") return;
  fontsRequested = true;
  const handle = delayRender("Carregando Montserrat");
  const faces: FontFace[] = [];
  for (const weight of [600, 700, 800, 900]) {
    for (const subset of ["latin", "latin-ext"]) {
      faces.push(
        new FontFace(FONT, `url(${staticFile(`fonts/montserrat-${subset}-${weight}-normal.woff2`)}) format("woff2")`, {
          weight: String(weight),
          unicodeRange: subset === "latin" ? "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD" : "U+0100-02AF, U+0304, U+0308, U+0329, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
        }),
      );
    }
  }
  Promise.all(faces.map((f) => f.load().then((loaded) => (document.fonts as unknown as Set<FontFace>).add(loaded))))
    .then(() => continueRender(handle))
    .catch(() => continueRender(handle));
};
