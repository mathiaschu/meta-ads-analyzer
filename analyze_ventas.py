#!/usr/bin/env python3
"""Analizar datos de ventas del Google Sheet - Cierre campanas Meta Ads"""
import csv

def parse_cop(val):
    """Parse COP currency: $45.626.500 -> 45626500"""
    s = val.strip().replace('$', '').replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0

with open('ventas_2026.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [r for r in reader if len(r) >= 15 and r[0].strip()]

print(f'Total filas con datos: {len(rows)}')

# ── Ventas META solamente ──
meta_rows = [r for r in rows if r[7].strip() == 'META']
print(f'\n{"="*60}')
print(f'  VENTAS CERRADAS POR META ADS: {len(meta_rows)}')
print(f'{"="*60}')

total_valor = 0
campanas = {}
asesores = {}
anuncios = {}
conjuntos = {}
dias_cierre = []

for r in meta_rows:
    valor = parse_cop(r[12])  # Columna 12 = Precio lotes
    total_valor += valor

    camp = r[8].strip().lower()
    if camp:
        campanas.setdefault(camp, []).append(valor)

    asesor = r[1].strip()
    if asesor and asesor != 'INMOBILIARIA':
        asesores.setdefault(asesor, []).append(valor)

    anuncio = r[10].strip()
    if anuncio:
        anuncios.setdefault(anuncio, []).append(valor)

    conjunto = r[9].strip()
    if conjunto:
        conjuntos.setdefault(conjunto, []).append(valor)

    try:
        d = int(r[6].strip())
        dias_cierre.append(d)
    except:
        pass

print(f'\nValor total vendido (META): ${total_valor:,.0f} COP')
print(f'Ticket promedio: ${total_valor/len(meta_rows):,.0f} COP')
if dias_cierre:
    print(f'Promedio dias para cierre: {sum(dias_cierre)/len(dias_cierre):.1f} dias')
    print(f'Mediana dias para cierre: {sorted(dias_cierre)[len(dias_cierre)//2]} dias')
    print(f'Rango: {min(dias_cierre)} - {max(dias_cierre)} dias')

print(f'\n--- TOP CAMPANAS META (por # ventas) ---')
for camp, vals in sorted(campanas.items(), key=lambda x: -len(x[1]))[:10]:
    total = sum(vals)
    print(f'  {camp}')
    print(f'    {len(vals)} ventas | ${total:,.0f} COP | Ticket prom: ${total/len(vals):,.0f}')

print(f'\n--- ASESORES META ---')
for asesor, vals in sorted(asesores.items(), key=lambda x: -sum(x[1])):
    total = sum(vals)
    print(f'  {asesor}: {len(vals)} ventas | ${total:,.0f} COP')

print(f'\n--- TOP ANUNCIOS/CREATIVOS (por # ventas) ---')
for anuncio, vals in sorted(anuncios.items(), key=lambda x: -len(x[1]))[:10]:
    total = sum(vals)
    print(f'  {anuncio}: {len(vals)} ventas | ${total:,.0f} COP')

print(f'\n--- CONJUNTOS DE ANUNCIOS ---')
for conj, vals in sorted(conjuntos.items(), key=lambda x: -len(x[1]))[:10]:
    total = sum(vals)
    print(f'  {conj}: {len(vals)} ventas | ${total:,.0f} COP')

# ── Resumen por fuente ──
print(f'\n{"="*60}')
print(f'  RESUMEN POR FUENTE (TODAS)')
print(f'{"="*60}')
fuentes = {}
for r in rows:
    fuente = r[7].strip()
    valor = parse_cop(r[12])
    if fuente:
        if fuente not in fuentes:
            fuentes[fuente] = {'count': 0, 'valor': 0}
        fuentes[fuente]['count'] += 1
        fuentes[fuente]['valor'] += valor

total_all = sum(d['valor'] for d in fuentes.values())
for f, data in sorted(fuentes.items(), key=lambda x: -x[1]['valor']):
    pct = (data['valor'] / total_all * 100) if total_all else 0
    print(f'  {f}: {data["count"]} ventas | ${data["valor"]:,.0f} COP | {pct:.1f}% del revenue')

# ── Ventas META por mes ──
print(f'\n--- VENTAS META POR MES ---')
meta_por_mes = {}
for r in meta_rows:
    mes = r[0].strip()
    valor = parse_cop(r[12])
    if mes not in meta_por_mes:
        meta_por_mes[mes] = {'count': 0, 'valor': 0}
    meta_por_mes[mes]['count'] += 1
    meta_por_mes[mes]['valor'] += valor

for m, data in meta_por_mes.items():
    print(f'  {m}: {data["count"]} ventas | ${data["valor"]:,.0f} COP')

# ── Ventas TODAS por mes ──
print(f'\n--- VENTAS TOTALES POR MES ---')
all_por_mes = {}
for r in rows:
    mes = r[0].strip()
    valor = parse_cop(r[12])
    if mes not in all_por_mes:
        all_por_mes[mes] = {'count': 0, 'valor': 0}
    all_por_mes[mes]['count'] += 1
    all_por_mes[mes]['valor'] += valor

for m, data in all_por_mes.items():
    meta_c = meta_por_mes.get(m, {}).get('count', 0)
    meta_pct = (meta_c / data['count'] * 100) if data['count'] else 0
    print(f'  {m}: {data["count"]} ventas total | ${data["valor"]:,.0f} COP | META = {meta_c} ({meta_pct:.0f}%)')
