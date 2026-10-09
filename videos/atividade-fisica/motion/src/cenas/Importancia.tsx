import React from "react";
import {AbsoluteFill} from "remotion";
import {Brain, Droplet, HeartPulse, Ribbon, TriangleAlert} from "lucide-react";
import {prog} from "../anim";
import {Cabecalho, Cartao, Contador, Destaque, Entra, Selo, Som} from "../componentes/base";
import {COR, FONTE} from "../tema";
import {useCena} from "../tl";

export const Importancia: React.FC = () => {
  const {frame, em, fala} = useCena("importancia");
  const l06 = fala("l06");

  const cartoes = [
    {em: em("l04", "dezenove"), icone: <HeartPulse size={46} />, cor: COR.coral, ate: 19, prefixo: "", texto: "doenças do coração e AVC"},
    {em: em("l05", "diabetes"), icone: <Droplet size={46} />, cor: COR.ciano, ate: 17, prefixo: "", texto: "diabetes"},
    {em: em("l05", "depressão"), icone: <Brain size={46} />, cor: COR.limao, ate: 32, prefixo: "até", texto: "depressão e demência"},
    {em: em("l05", "câncer"), icone: <Ribbon size={46} />, cor: COR.amarelo, ate: 28, prefixo: "até", texto: "vários tipos de câncer"},
  ];

  const risco = em("l06", "risco");
  const barra = prog(frame, risco, 26);

  return (
    <AbsoluteFill>
      <Cabecalho rotulo="01 · Por que se mexer" fonte="OMS" />

      <Entra em={em("l04", "quem") - 4} sai={l06.s - 6} style={{position: "absolute", top: 170, width: "100%", textAlign: "center"}}>
        <div style={{fontFamily: FONTE.titulo, fontWeight: 800, fontStretch: "108%", fontSize: 56, color: COR.texto}}>
          Quem se mexe com regularidade tem <Destaque>menos risco</Destaque> de:
        </div>
      </Entra>

      <div style={{position: "absolute", top: 290, left: 161, display: "flex", gap: 26}}>
        {cartoes.map((c) => (
          <Entra key={c.texto} em={c.em - 3} quique dist={80} sai={l06.s - 6}>
            <Cartao style={{width: 380, height: 450, padding: 40, display: "flex", flexDirection: "column", position: "relative", overflow: "hidden"}}>
              <div style={{position: "absolute", left: 0, top: 0, width: "100%", height: 6, background: c.cor}} />
              <Selo cor={c.cor} tamanho={96}>{c.icone}</Selo>
              <div style={{marginTop: "auto", fontFamily: FONTE.texto, fontWeight: 700, fontSize: 30, color: COR.apagado, height: 36}}>
                {c.prefixo}
              </div>
              <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "100%", fontSize: 104, lineHeight: 1, color: c.cor}}>
                <Contador ate={c.ate} em={c.em} antes="−" depois="%" />
              </div>
              <div style={{marginTop: 18, fontFamily: FONTE.texto, fontWeight: 600, fontSize: 32, lineHeight: 1.2, color: COR.texto, minHeight: 78}}>
                {c.texto}
              </div>
            </Cartao>
          </Entra>
        ))}
      </div>

      {/* alerta: risco de quem não se mexe o suficiente */}
      <Entra em={l06.s + 2} quique dist={90} style={{position: "absolute", top: 230, left: 260, width: 1400}}>
        <Cartao style={{padding: "50px 64px", borderLeft: `10px solid ${COR.coral}`}}>
          <div style={{display: "flex", alignItems: "center", gap: 30}}>
            <Selo cor={COR.coral} tamanho={100}>
              <TriangleAlert size={52} />
            </Selo>
            <div style={{fontFamily: FONTE.texto, fontWeight: 650, fontSize: 40, color: COR.texto, lineHeight: 1.25}}>
              Quem <Destaque cor={COR.coral}>não se mexe o suficiente</Destaque> tem
              <br />
              um risco de morte maior:
            </div>
          </div>
          <div style={{marginTop: 30, display: "flex", alignItems: "flex-end", gap: 50}}>
            <div style={{fontFamily: FONTE.titulo, fontWeight: 900, fontStretch: "115%", fontSize: 150, lineHeight: 0.95, color: COR.coral}}>
              +20 a 30%
            </div>
          </div>
          <div style={{marginTop: 40, display: "flex", flexDirection: "column", gap: 18}}>
            {[
              {nome: "Ativo", largura: 760, cor: COR.limao, extra: 0},
              {nome: "Pouco ativo", largura: 760, cor: COR.apagado, extra: 1},
            ].map((b) => (
              <div key={b.nome} style={{display: "flex", alignItems: "center", gap: 24}}>
                <div style={{width: 220, fontFamily: FONTE.texto, fontWeight: 650, fontSize: 30, color: COR.texto}}>{b.nome}</div>
                <div style={{height: 34, width: b.largura * barra, borderRadius: 17, background: b.cor, opacity: 0.9}} />
                {b.extra ? (
                  <div
                    style={{
                      marginLeft: -24,
                      height: 34,
                      width: 190 * prog(frame, risco + 22, 18),
                      borderRadius: "0 17px 17px 0",
                      background: `repeating-linear-gradient(-45deg, ${COR.coral}, ${COR.coral} 10px, ${COR.coral}AA 10px, ${COR.coral}AA 20px)`,
                    }}
                  />
                ) : null}
              </div>
            ))}
          </div>
        </Cartao>
      </Entra>

      {cartoes.map((c) => (
        <Som key={c.texto} em={c.em - 3} arquivo="pop" volume={0.2} />
      ))}
    </AbsoluteFill>
  );
};
