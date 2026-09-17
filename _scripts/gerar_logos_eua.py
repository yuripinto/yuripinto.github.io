#!/usr/bin/env python3
"""Monta os logos das empresas americanas para o Freedom.

Os logos da B3 são SVGs de fundo colorido com a marca em branco por cima.
A coleção pública de logos de tickers (nvstly/icons) vem em PNG transparente,
a maioria já clareada para tema escuro — ou seja, quase no mesmo formato,
faltando o fundo.

Este script fecha essa diferença: recorta a sobra transparente, encaixa a
marca no quadrado com folga e assenta num fundo sólido. Marca clara ganha o
fundo colorido do cartão (o mesmo `cor` da base); marca escura ganha fundo
branco, senão ela some. Quem não tem logo na coleção fica de fora e o app
mostra as iniciais, como já faz com metade da B3.

Uso:
    python3 _scripts/gerar_logos_eua.py --icones /caminho/nvstly-icons

Dependências: pillow (pip install pillow).
"""

import argparse
import json
import os

from PIL import Image

LADO = 112          # 56px do cartão em telas retina
MARGEM = 0.82       # quanto do quadrado a marca ocupa
CLARO = 0.58        # acima disso a marca é clara e pede fundo colorido


def variantes(ticker):
    """BRK-B vira BRK.B e BRKB: cada coleção nomeia de um jeito."""
    return [ticker, ticker.replace('-', '.'), ticker.replace('-', ''),
            ticker.split('-')[0]]


def luminancia(img):
    """Média da luminosidade dos pixels visíveis, de 0 (preta) a 1 (branca)."""
    px = img.load()
    soma = peso = 0.0
    for y in range(0, img.height, 4):
        for x in range(0, img.width, 4):
            r, g, b, a = px[x, y]
            if a < 16:
                continue
            soma += (0.299 * r + 0.587 * g + 0.114 * b) / 255 * a
            peso += a
    return soma / peso if peso else 1.0


def cortar(img):
    """Tira a moldura transparente para a marca ocupar o quadrado inteiro."""
    caixa = img.getbbox()
    return img.crop(caixa) if caixa else img


def montar(origem, cor):
    logo = cortar(Image.open(origem).convert('RGBA'))
    fundo = cor if luminancia(logo) >= CLARO else '#ffffff'

    limite = int(LADO * MARGEM)
    escala = min(limite / logo.width, limite / logo.height)
    logo = logo.resize((max(1, round(logo.width * escala)),
                        max(1, round(logo.height * escala))),
                       Image.LANCZOS)

    tela = Image.new('RGBA', (LADO, LADO), fundo)
    tela.alpha_composite(logo, ((LADO - logo.width) // 2,
                                (LADO - logo.height) // 2))
    # paleta de 256 cores: o arquivo cai para ~2 KB sem diferença visível
    return tela.convert('RGB').quantize(colors=256, method=Image.MAXCOVERAGE)


def principal():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--icones', required=True, help='clone de nvstly/icons')
    p.add_argument('--saida', default=os.path.join(raiz, 'apps', 'freedom', 'logos'))
    p.add_argument('--bases', default=os.path.join(raiz, 'apps', 'freedom'))
    args = p.parse_args()

    pasta = os.path.join(args.icones, 'ticker_icons')
    disponiveis = {f[:-4] for f in os.listdir(pasta) if f.endswith('.png')}

    base = {}
    for arquivo in ('dados-nyse.json', 'dados-nasdaq.json'):
        with open(os.path.join(args.bases, arquivo), encoding='utf-8') as f:
            base.update(json.load(f))

    feitos = claros = faltando = 0
    for ticker in sorted(base):
        origem = next((os.path.join(pasta, v + '.png') for v in variantes(ticker)
                       if v in disponiveis), None)
        if not origem:
            faltando += 1
            continue
        imagem = montar(origem, base[ticker]['cor'])
        imagem.save(os.path.join(args.saida, ticker + '.png'), optimize=True)
        feitos += 1

    print(f'{feitos} logos gerados, {faltando} sem logo na coleção')


if __name__ == '__main__':
    principal()
