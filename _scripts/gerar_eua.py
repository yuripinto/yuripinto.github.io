#!/usr/bin/env python3
"""Monta as bases das bolsas americanas para o Freedom.

Lê a base pública de fundamentos dos EUA (demonstrativos trimestrais
reportados à SEC, coletados via Alpha Vantage no repositório
parta1960/market-fundamentals-db) e escreve um JSON por bolsa no mesmo
formato que o app já usa para a B3:

    apps/freedom/dados-nyse.json
    apps/freedom/dados-nasdaq.json

A leitura anual é montada aqui: os trimestres viram exercícios fiscais
(fluxos somados, saldos tirados do trimestre de fechamento) e os mesmos
critérios da B3 — lucro, crescimento, ROE, margem, dívida e dividendos —
geram os sinais, o veredito e o ranking.

Uso:
    python3 _scripts/gerar_eua.py --base /caminho/market-fundamentals-db

Dependências: duckdb (pip install duckdb).
"""

import argparse
import json
import math
import os
from collections import defaultdict

import duckdb

ANOS_MAX = 11          # mesma janela da B3 (2015-2025)
ANOS_MIN = 5           # menos que isso não dá para avaliar histórico
ANOS_RANKING = 8       # série curta não entra no ranking
LIQUIDEZ_MIN = 20e6    # US$ por dia, média de 90 pregões
PREGOES = 90

BOLSAS = ('NYSE', 'NASDAQ')

# os mesmos oito tons que a B3 usa nos cartões
CORES = ['#2b6cb0', '#b7791f', '#2f855a', '#c05621',
         '#4a5568', '#9b2c2c', '#553c9a', '#0987a0']

SETORES = {
    'TECHNOLOGY': 'Tecnologia',
    'FINANCIAL SERVICES': 'Financeiro',
    'HEALTHCARE': 'Saúde',
    'INDUSTRIALS': 'Indústria',
    'CONSUMER CYCLICAL': 'Consumo Cíclico',
    'CONSUMER DEFENSIVE': 'Consumo Não Cíclico',
    'REAL ESTATE': 'Imobiliário',
    'BASIC MATERIALS': 'Materiais Básicos',
    'ENERGY': 'Petróleo e Gás',
    'COMMUNICATION SERVICES': 'Comunicação',
    'UTILITIES': 'Utilidade Pública',
}

MESES = {1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio',
         6: 'junho', 7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro',
         11: 'novembro', 12: 'dezembro'}

MES_NUMERO = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
              'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9,
              'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12}

# fluxos somam os quatro trimestres; saldos vêm do trimestre de fechamento
FLUXOS = ['totalRevenue', 'netIncome', 'ebit', 'incomeTaxExpense',
          'incomeBeforeTax', 'dividendPayout', 'proceedsFromRepurchaseOfEquity']
SALDOS = ['totalShareholderEquity', 'totalAssets', 'cashAndShortTermInvestments',
          'shortLongTermDebtTotal', 'totalCurrentAssets', 'totalCurrentLiabilities']


# ---------------------------------------------------------------- leitura

def ler_parquet(base):
    """Devolve (empresas, trimestres, precos) já pivotados."""
    p = os.path.join(base, 'data', 'parquet')
    con = duckdb.connect()

    itens = ', '.join(f"'{i}'" for i in FLUXOS + SALDOS)
    colunas = ',\n      '.join(
        f"max(value) filter (where item = '{i}') as \"{i}\""
        for i in FLUXOS + SALDOS)

    empresas = con.sql(f"""
        select ticker,
               any_value(cik) as cik,
               any_value(name) as nome,
               any_value(exchange) as bolsa,
               any_value(sector) as setor,
               any_value(industry) as industria,
               any_value(fiscal_year_end) as fim_exercicio
        from '{p}/companies/*.parquet'
        where exchange in {BOLSAS}
        group by ticker
    """).fetchall()

    trimestres = con.sql(f"""
        select ticker, fiscal_date_ending as d,
      {colunas}
        from '{p}/fundamentals/*.parquet'
        where item in ({itens})
        group by ticker, fiscal_date_ending
        order by ticker, d
    """).fetchall()

    precos = con.sql(f"""
        with recente as (
          select ticker, date, close, volume, dividend_amount,
                 row_number() over (partition by ticker order by date desc) as rn,
                 max(date) over (partition by ticker) as ultimo
          from '{p}/prices_daily/*.parquet'
        )
        select ticker,
               max(ultimo) as ultimo_dia,
               max(close) filter (where rn = 1) as cotacao,
               avg(close * volume) filter (where rn <= {PREGOES}) as liquidez,
               sum(dividend_amount) filter (where date >= ultimo - interval 365 day)
                 as dividendos_12m
        from recente
        group by ticker
    """).fetchall()

    indicadores = con.sql(f"""
        with ranqueado as (
          select ticker, pe_ttm, pb, net_margin, eps_ttm, revenue_ttm,
                 row_number() over (partition by ticker order by date desc) as rn
          from '{p}/derived_metrics/latest_ratios.parquet'
        )
        select ticker, pe_ttm, pb, net_margin from ranqueado where rn = 1
    """).fetchall()

    con.close()
    return empresas, trimestres, precos, indicadores


# ------------------------------------------------------------ exercícios

def exercicio_de(data, mes_fim):
    """O exercício fiscal a que um trimestre pertence."""
    return data.year if data.month <= mes_fim else data.year + 1


def montar_linhas(quadros, mes_fim):
    """Agrupa trimestres em exercícios completos (quatro trimestres)."""
    por_ano = defaultdict(list)
    for q in quadros:
        por_ano[exercicio_de(q['d'], mes_fim)].append(q)

    linhas = []
    for ano in sorted(por_ano):
        tri = sorted(por_ano[ano], key=lambda q: q['d'])
        if len(tri) != 4:
            continue                      # exercício incompleto: fica de fora
        fecha = tri[-1]
        if fecha['d'].month != mes_fim:
            continue                      # fechamento fora do mês declarado

        def soma(campo):
            valores = [q[campo] for q in tri if q[campo] is not None]
            return sum(valores) if len(valores) == 4 else None

        receita, lucro = soma('totalRevenue'), soma('netIncome')
        if receita is None or lucro is None:
            continue

        patrimonio = fecha['totalShareholderEquity']
        ativo = fecha['totalAssets']
        caixa = fecha['cashAndShortTermInvestments']
        divida = fecha['shortLongTermDebtTotal']

        linhas.append({
            'ano': ano,
            'patrimonio': patrimonio,
            'receita': receita,
            'lucro': lucro,
            'margem': (lucro / receita * 100) if receita else None,
            'roe': (lucro / patrimonio * 100) if patrimonio and patrimonio > 0 else None,
            'caixa': caixa,
            'caixa_liquido': (caixa - divida) if caixa is not None and divida is not None else None,
            'divida': divida,
            'divida_pl': (divida / patrimonio) if divida is not None and patrimonio and patrimonio > 0 else None,
            'ativo': ativo,
            'alavancagem': (ativo / patrimonio) if ativo and patrimonio and patrimonio > 0 else None,
            'margem_financeira': None,
            'dividendos_pagos': abs(soma('dividendPayout')) if soma('dividendPayout') is not None else None,
            # no fluxo de caixa a recompra entra como saída (valor negativo);
            # valor positivo é emissão de ações, que não interessa aqui
            'recompras': max(-(soma('proceedsFromRepurchaseOfEquity') or 0), 0),
            'ebit': soma('ebit'),
            'imposto': soma('incomeTaxExpense'),
            'lucro_antes_imposto': soma('incomeBeforeTax'),
            'ativo_circulante': fecha['totalCurrentAssets'],
            'passivo_circulante': fecha['totalCurrentLiabilities'],
        })
    return linhas[-ANOS_MAX:]


# ---------------------------------------------------------------- sinais

def variacao(linhas, campo):
    """Crescimento do primeiro ao último ano, no estilo da B3."""
    valores = [(l['ano'], l[campo]) for l in linhas if l[campo] is not None]
    if len(valores) < 2:
        return None, None, None
    (ano_ini, ini), (ano_fim, fim) = valores[0], valores[-1]
    if ini is None or fim is None:
        return None, None, None
    if ini <= 0:
        return None, ano_ini, fim
    return (fim - ini) / abs(ini) * 100, ano_ini, fim


def sinal_crescimento(linhas, campo, nome, moeda):
    pct, ano_ini, fim = variacao(linhas, campo)
    if pct is None:
        if ano_ini is None:
            return {'situacao': 'neutro', 'titulo': f'{nome}: sem comparação',
                    'detalhe': 'Série curta demais para comparar as pontas.'}
        return {'situacao': 'neutro', 'titulo': f'{nome}: sem comparação',
                'detalhe': f'O período começa com prejuízo ({ano_ini}), então a '
                           'comparação percentual não diz nada.'}
    if fim is not None and fim <= 0:
        ini = next(l[campo] for l in linhas if l[campo] is not None)
        return {'situacao': 'ruim', 'titulo': f'{nome} virou negativo',
                'detalhe': f'Saiu de {ini / 1e6:,.0f} para {fim / 1e6:,.0f} '
                           f'({moeda} milhões).'.replace(',', '.')}
    if pct >= 100:
        return {'situacao': 'bom', 'titulo': f'{nome} crescendo',
                'detalhe': f'+{pct:.0f}% no período.'}
    if pct >= 0:
        return {'situacao': 'atencao', 'titulo': f'{nome} andando de lado',
                'detalhe': f'+{pct:.0f}% no período.'}
    return {'situacao': 'ruim', 'titulo': f'{nome} encolhendo',
            'detalhe': f'{pct:.0f}% no período.'}


def vg(valor, casas=1):
    """Número com vírgula decimal, sem estragar o ponto final da frase."""
    return f'{valor:.{casas}f}'.replace('.', ',')


def media(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def montar_sinais(linhas, perfil, moeda):
    sinais = []
    anos = len(linhas)
    prejuizos = [l['ano'] for l in linhas if l['lucro'] is not None and l['lucro'] < 0]

    if not prejuizos:
        sinais.append({'situacao': 'bom', 'titulo': 'Lucro consistente',
                       'detalhe': f'Lucro positivo nos {anos} anos da série.'})
    elif len(prejuizos) <= 2:
        sinais.append({'situacao': 'atencao', 'titulo': 'Lucro com tropeços',
                       'detalhe': 'Prejuízo em ' + ', '.join(str(a) for a in prejuizos) + '.'})
    else:
        sinais.append({'situacao': 'ruim', 'titulo': 'Lucro instável',
                       'detalhe': f'Prejuízo em {len(prejuizos)} dos {anos} anos.'})

    negativos = [l['ano'] for l in linhas
                 if l['patrimonio'] is not None and l['patrimonio'] < 0]
    if negativos:
        sinais.append({'situacao': 'ruim', 'titulo': 'Patrimônio líquido negativo',
                       'detalhe': f'A empresa deve mais do que tem ({len(negativos)} '
                                  f'dos {anos} anos). Com PL negativo o ROE não '
                                  'significa nada.'})

    sinais.append(sinal_crescimento(linhas, 'patrimonio', 'Patrimônio Líquido', moeda))
    sinais.append(sinal_crescimento(linhas, 'receita', 'Receita', moeda))
    sinais.append(sinal_crescimento(linhas, 'lucro', 'Lucro', moeda))

    roe = media([l['roe'] for l in linhas])
    if roe is None:
        sinais.append({'situacao': 'neutro', 'titulo': 'ROE sem base',
                       'detalhe': 'Só dá para calcular nos anos de patrimônio positivo.'})
    elif roe >= 15:
        sinais.append({'situacao': 'bom', 'titulo': 'ROE alto',
                       'detalhe': f'Média de {vg(roe)}% ao ano.'})
    elif roe >= 8:
        sinais.append({'situacao': 'atencao', 'titulo': 'ROE mediano',
                       'detalhe': f'Média de {vg(roe)}% ao ano.'})
    else:
        sinais.append({'situacao': 'ruim', 'titulo': 'ROE baixo',
                       'detalhe': f'Média de {vg(roe)}% ao ano.'})

    margem = media([l['margem'] for l in linhas])
    if margem is None:
        sinais.append({'situacao': 'neutro', 'titulo': 'Margem líquida',
                       'detalhe': 'Sem receita comparável.'})
    elif margem >= 15:
        sinais.append({'situacao': 'bom', 'titulo': 'Margem gorda',
                       'detalhe': f'Média de {vg(margem)}% da receita virando lucro.'})
    elif margem >= 5:
        sinais.append({'situacao': 'atencao', 'titulo': 'Margem apertada',
                       'detalhe': f'Média de {vg(margem)}%.'})
    else:
        sinais.append({'situacao': 'ruim', 'titulo': 'Margem baixa',
                       'detalhe': f'Média de {vg(margem)}%.'})

    ultimo = linhas[-1]
    if perfil == 'operacional':
        dpl = ultimo['divida_pl']
        if dpl is None:
            sinais.append({'situacao': 'neutro', 'titulo': 'Dívida / PL',
                           'detalhe': 'Sem dados de dívida.'})
        elif dpl <= 0.5:
            sinais.append({'situacao': 'bom', 'titulo': 'Dívida sob controle',
                           'detalhe': f'Dívida/PL de {vg(dpl, 2)} no último ano.'})
        elif dpl <= 1:
            sinais.append({'situacao': 'atencao', 'titulo': 'Dívida relevante',
                           'detalhe': f'Dívida/PL de {vg(dpl, 2)} no último ano.'})
        else:
            sinais.append({'situacao': 'ruim', 'titulo': 'Dívida maior que o patrimônio',
                           'detalhe': f'Dívida/PL de {vg(dpl, 2)} no último ano.'})

        devedores = [l for l in linhas if l['caixa_liquido'] is not None and l['caixa_liquido'] < 0]
        if ultimo['caixa_liquido'] is not None and ultimo['caixa_liquido'] >= 0:
            sinais.append({'situacao': 'bom', 'titulo': 'Caixa líquido positivo',
                           'detalhe': 'Tem mais caixa do que dívida.'})
        elif devedores:
            sinais.append({'situacao': 'atencao', 'titulo': 'Caixa líquido negativo',
                           'detalhe': f'Dívida supera o caixa em {len(devedores)} dos {anos} anos.'})
    else:
        alav = ultimo['alavancagem']
        if alav is None:
            sinais.append({'situacao': 'neutro', 'titulo': 'Alavancagem',
                           'detalhe': 'Sem dados de ativo.'})
        elif alav <= 12:
            sinais.append({'situacao': 'bom', 'titulo': 'Alavancagem sob controle',
                           'detalhe': f'Ativo de {vg(alav)} vezes o patrimônio no último ano.'})
        elif alav <= 16:
            sinais.append({'situacao': 'atencao', 'titulo': 'Alavancagem elevada',
                           'detalhe': f'Ativo de {vg(alav)} vezes o patrimônio no último ano.'})
        else:
            sinais.append({'situacao': 'ruim', 'titulo': 'Muito alavancado',
                           'detalhe': f'Ativo de {vg(alav)} vezes o patrimônio no último ano. '
                                      'Uma perda pequena na carteira come o capital.'})
    return sinais


def explicar_recompra(linhas, moeda):
    """Nas bolsas americanas é comum o patrimônio encolher por recompra de ações.

    A conta não muda por isso — dinheiro que sai é dinheiro que sai —, mas quem
    lê a tabela merece saber que o patrimônio caiu por devolução ao acionista, e
    não por prejuízo.
    """
    pct, _, _ = variacao(linhas, 'patrimonio')
    if pct is None or pct >= 0:
        return None
    recompras = sum(l['recompras'] or 0 for l in linhas)
    lucros = sum(l['lucro'] for l in linhas if l['lucro'] and l['lucro'] > 0)
    if not recompras or not lucros or recompras < lucros * 0.25:
        return None
    return (f'O patrimônio encolhe em parte por recompra de ações: '
            f'{bilhoes_texto(recompras, moeda)} no período, o equivalente a '
            f'{recompras / lucros * 100:.0f}% do lucro acumulado. Recompra devolve '
            'dinheiro ao acionista e reduz o patrimônio contábil.')


def julgar(sinais, perfil):
    ruins = sum(1 for s in sinais if s['situacao'] == 'ruim')
    atencoes = sum(1 for s in sinais if s['situacao'] == 'atencao')
    if ruins >= 2:
        return 'ruim', 'Histórico fraco pelos critérios básicos. Não é empresa boa.'
    if ruins == 1 or atencoes >= 3:
        return 'atencao', 'Histórico razoável, mas tem ponto para acompanhar de perto.'
    if perfil == 'operacional':
        return 'bom', 'Histórico sólido: lucra, cresce e não depende de dívida.'
    return 'bom', 'Histórico sólido: lucra e cresce de forma consistente.'


# ------------------------------------------------------------ dividendos

def montar_dividendos(linhas):
    com_dado = [l for l in linhas if l['dividendos_pagos'] is not None]
    anos = len(com_dado)
    pagando = [l for l in com_dado if l['dividendos_pagos'] > 0]
    sem = {'anos_pagando': len(pagando), 'anos': anos, 'payout': None,
           'situacao': 'sem dados', 'titulo': 'Sem histórico de dividendos',
           'detalhe': 'A empresa não detalha dividendos no fluxo de caixa em anos suficientes.'}
    if anos < ANOS_MIN or not pagando:
        return sem

    lucrativos = [l for l in pagando if l['lucro'] and l['lucro'] > 0]
    payout = media([l['dividendos_pagos'] / l['lucro'] * 100 for l in lucrativos]) if lucrativos else None
    quanto = f'Pagou em {len(pagando)} dos {anos} anos'

    if len(pagando) / anos < 0.9:
        return {'anos_pagando': len(pagando), 'anos': anos, 'payout': payout,
                'situacao': 'regular', 'titulo': 'Pagadora irregular',
                'detalhe': f'{quanto}, sem constância.'}
    if payout is None:
        return sem
    if payout > 100:
        return {'anos_pagando': len(pagando), 'anos': anos, 'payout': payout,
                'situacao': 'regular', 'titulo': 'Distribui mais do que lucra',
                'detalhe': f'{quanto}, média de {payout:.0f}% do lucro — o excedente '
                           'sai de caixa ou dívida.'}
    if payout < 25:
        return {'anos_pagando': len(pagando), 'anos': anos, 'payout': payout,
                'situacao': 'regular', 'titulo': 'Paga sempre, mas pouco',
                'detalhe': f'{quanto}, média de {payout:.0f}% do lucro.'}
    if any(l['lucro'] is not None and l['lucro'] < 0 for l in com_dado):
        return {'anos_pagando': len(pagando), 'anos': anos, 'payout': payout,
                'situacao': 'regular', 'titulo': 'Paga bem, mas o lucro oscila',
                'detalhe': f'{quanto}, média de {payout:.0f}% do lucro, com anos de '
                           'prejuízo no meio.'}
    return {'anos_pagando': len(pagando), 'anos': anos, 'payout': payout,
            'situacao': 'bom', 'titulo': 'Boa pagadora de dividendos',
            'detalhe': f'{quanto}, distribuindo em média {payout:.0f}% de um lucro '
                       'que não falha.'}


# ------------------------------------------------------------ indicadores

def montar_indicadores(linhas, cotacao, dividendos_12m, pe, pb, perfil):
    ind = {}
    ultimo = linhas[-1]
    if pe is not None and abs(pe) < 1000:
        ind['P/L'] = pe
    if pb is not None and abs(pb) < 1000:
        ind['P/VP'] = pb
    if cotacao and dividendos_12m:
        ind['Div.Yield'] = dividendos_12m / cotacao * 100
    if ultimo['roe'] is not None:
        ind['ROE'] = ultimo['roe']
    if perfil == 'operacional':
        capital = (ultimo['patrimonio'] or 0) + (ultimo['divida'] or 0)
        ebit, antes, imposto = ultimo['ebit'], ultimo['lucro_antes_imposto'], ultimo['imposto']
        if ebit and capital > 0:
            aliquota = (imposto / antes) if antes and antes > 0 and imposto is not None else 0.21
            aliquota = min(max(aliquota, 0.0), 0.5)
            ind['ROIC'] = ebit * (1 - aliquota) / capital * 100
    if ultimo['margem'] is not None:
        ind['Mrg. Líq.'] = ultimo['margem']
    ac, pc = ultimo['ativo_circulante'], ultimo['passivo_circulante']
    if ac and pc and perfil == 'operacional':
        ind['Liq. Corr.'] = ac / pc
    if perfil == 'operacional' and ultimo['patrimonio'] and ultimo['patrimonio'] > 0 \
            and ultimo['divida'] is not None and ultimo['caixa'] is not None:
        ind['Dív.Líq/ Patrim.'] = (ultimo['divida'] - ultimo['caixa']) / ultimo['patrimonio']
    if len(linhas) >= 6:
        base, fim = linhas[-6]['receita'], ultimo['receita']
        if base and base > 0 and fim and fim > 0:
            ind['Cresc. Rec.5a'] = ((fim / base) ** (1 / 5) - 1) * 100
    return {k: round(v, 2) for k, v in ind.items() if v is not None and math.isfinite(v)}


# ------------------------------------------------------------------ nota

def pontuar(linhas, dividendos):
    """Nota bruta de 0 a 100 — vira ranking depois de normalizada."""
    anos = len(linhas)
    lucrativos = sum(1 for l in linhas if l['lucro'] is not None and l['lucro'] > 0)
    nota = 25 * lucrativos / anos

    for campo, peso in (('receita', 12.5), ('lucro', 12.5)):
        pct, _, _ = variacao(linhas, campo)
        if pct is not None:
            nota += peso * min(max(pct, 0) / 200, 1)

    roe = media([l['roe'] for l in linhas])
    if roe is not None:
        nota += 20 * min(max(roe, 0) / 25, 1)

    margem = media([l['margem'] for l in linhas])
    if margem is not None:
        nota += 15 * min(max(margem, 0) / 25, 1)

    dpl = linhas[-1]['divida_pl']
    if dpl is None:
        nota += 7.5
    else:
        nota += 15 * min(max(1 - dpl, 0), 1)

    if dividendos['situacao'] == 'bom':
        nota += 12.5
    elif dividendos['situacao'] == 'regular':
        nota += 5
    return nota


# ------------------------------------------------------------------ saída

def arredondar(v, casas=1):
    return None if v is None else round(v, casas)


def milhoes(v):
    return None if v is None else round(v / 1e6, 1)


def bilhoes_texto(v, moeda):
    if v is None:
        return None
    if abs(v) >= 1e9:
        return f'{moeda} {vg(v / 1e9)} bilhões'
    return f'{moeda} {v / 1e6:.0f} milhões'


def cor_de(ticker):
    return CORES[sum(ord(c) for c in ticker) % len(CORES)]


def perfil_de(industria):
    i = (industria or '').upper()
    if 'BANK' in i:
        return 'banco'
    if 'INSURANCE' in i and 'BROKER' not in i:
        return 'seguradora'
    return 'operacional'


def titulo(texto):
    return ' '.join(p.capitalize() for p in (texto or '').split())


def principal():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True,
                   help='clone de parta1960/market-fundamentals-db')
    p.add_argument('--saida', default=os.path.join(raiz, 'apps', 'freedom'))
    p.add_argument('--liquidez-min', type=float, default=LIQUIDEZ_MIN)
    args = p.parse_args()

    empresas, trimestres, precos, indicadores = ler_parquet(args.base)
    print(f'{len(empresas)} empresas, {len(trimestres)} trimestres lidos')

    campos = ['d'] + FLUXOS + SALDOS
    por_ticker = defaultdict(list)
    for linha in trimestres:
        por_ticker[linha[0]].append(dict(zip(campos, linha[1:])))

    mercado = {t: {'ultimo_dia': u, 'cotacao': c, 'liquidez': l, 'dividendos_12m': d}
               for t, u, c, l, d in precos}
    metricas = {t: {'pe': pe, 'pb': pb, 'margem': m} for t, pe, pb, m in indicadores}

    bases = {b: {} for b in BOLSAS}
    for ticker, cik, nome, bolsa, setor, industria, fim_exercicio in empresas:
        preco = mercado.get(ticker)
        if not preco or not preco['cotacao'] or not preco['liquidez']:
            continue
        if preco['liquidez'] < args.liquidez_min:
            continue
        mes_fim = MES_NUMERO.get((fim_exercicio or '').upper())
        if not mes_fim:
            continue

        linhas = montar_linhas(por_ticker.get(ticker, []), mes_fim)
        if len(linhas) < ANOS_MIN:
            continue

        moeda = 'US$'
        perfil = perfil_de(industria)
        sinais = montar_sinais(linhas, perfil, moeda)
        veredito, resumo = julgar(sinais, perfil)
        dividendos = montar_dividendos(linhas)
        m = metricas.get(ticker, {})
        ind = montar_indicadores(linhas, preco['cotacao'], preco['dividendos_12m'],
                                 m.get('pe'), m.get('pb'), perfil)

        ultimo = linhas[-1]
        notas = []
        if mes_fim != 12:
            notas.append(f'O ano fiscal da empresa fecha em {MESES[mes_fim]}: cada linha '
                         f'é o exercício encerrado nesse mês, não o ano civil.')
        if perfil != 'operacional':
            notas.append(f'Dívida não se aplica a {perfil}: o passivo aqui é a própria '
                         'operação, não alavancagem.')
        nota_recompra = explicar_recompra(linhas, moeda)
        if nota_recompra:
            notas.append(nota_recompra)

        setor_pt = SETORES.get((setor or '').upper(), 'Outros')
        paragrafo = (
            f'{nome} é uma companhia de {setor_pt.lower()} listada na {bolsa}'
            + (f', no ramo de {titulo(industria)}' if industria else '') + '. '
            + f'No exercício de {ultimo["ano"]} teve receita de '
            + f'{bilhoes_texto(ultimo["receita"], moeda)} e '
            + ('lucro de ' + bilhoes_texto(ultimo['lucro'], moeda)
               if ultimo['lucro'] and ultimo['lucro'] > 0
               else 'prejuízo de ' + bilhoes_texto(abs(ultimo['lucro'] or 0), moeda)) + '.')

        bases[bolsa][ticker] = {
            'nome': nome,
            'setor': setor_pt,
            'cor': cor_de(ticker),
            'perfil': perfil,
            'bolsa': bolsa,
            'moeda': moeda,
            'liquidez': round(preco['liquidez']),
            'cotacao': round(preco['cotacao'], 2),
            'cik': cik,
            'coletado_em': preco['ultimo_dia'].strftime('%d/%m/%Y'),
            'indicadores': ind,
            'notas': notas,
            'veredito': veredito,
            'resumo': resumo,
            'linhas': [{
                'ano': l['ano'],
                'patrimonio': milhoes(l['patrimonio']),
                'receita': milhoes(l['receita']),
                'lucro': milhoes(l['lucro']),
                'margem': arredondar(l['margem'], 2),
                'roe': arredondar(l['roe'], 2),
                'caixa': milhoes(l['caixa']),
                'caixa_liquido': milhoes(l['caixa_liquido']),
                'divida': milhoes(l['divida']),
                'divida_pl': arredondar(l['divida_pl'], 3),
                'ativo': milhoes(l['ativo']),
                'alavancagem': arredondar(l['alavancagem'], 2),
                'margem_financeira': None,
            } for l in linhas],
            'sinais': sinais,
            'sobre': {
                'paragrafo': paragrafo,
                'pais': 'Estados Unidos',
                'industria': titulo(industria) if industria else None,
            },
            'dividendos': dividendos,
            '_nota_bruta': pontuar(linhas, dividendos),
            '_anos': len(linhas),
        }

    for bolsa, base in bases.items():
        elegiveis = [t for t, d in base.items()
                     if d['veredito'] == 'bom' and d['_anos'] >= ANOS_RANKING]
        if elegiveis:
            teto = max(base[t]['_nota_bruta'] for t in elegiveis)
            elegiveis.sort(key=lambda t: -base[t]['_nota_bruta'])
            for posicao, t in enumerate(elegiveis, 1):
                base[t]['posicao'] = posicao
                base[t]['nota'] = round(base[t]['_nota_bruta'] / teto * 100, 1)
        for d in base.values():
            d.pop('_nota_bruta', None)
            d.pop('_anos', None)

        destino = os.path.join(args.saida, f'dados-{bolsa.lower()}.json')
        with open(destino, 'w', encoding='utf-8') as f:
            json.dump(base, f, ensure_ascii=False, separators=(',', ':'))
        tamanho = os.path.getsize(destino) / 1e6
        boas = sum(1 for d in base.values() if d['veredito'] == 'bom')
        print(f'{destino}: {len(base)} empresas ({boas} boas), {tamanho:.1f} MB')


if __name__ == '__main__':
    principal()
