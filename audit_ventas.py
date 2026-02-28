#!/usr/bin/env python3
"""Audit ventas META data from CSV"""
import csv
from collections import defaultdict

with open('ventas_2026.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [r for r in reader if len(r) >= 13 and r[0].strip()]

meta = [r for r in rows if r[7].strip() == 'META']

print('=== META: VENTAS SIN PRECIO ===')
sin_precio = 0
con_precio = 0
for r in meta:
    precio = r[12].strip()
    tiene = bool(precio and '$' in precio)
    if tiene:
        con_precio += 1
    else:
        sin_precio += 1
        print(f'  {r[0]:<10} {r[10]:<25} {r[3]:<10} Precio col: "{precio}"')

print(f'\nCon precio: {con_precio}')
print(f'Sin precio: {sin_precio}')
print(f'Total: {con_precio + sin_precio}')

print('\n=== CREATIVOS (TODOS, incluyendo sin precio) ===')
creativos = defaultdict(lambda: {'count': 0, 'revenue': 0, 'sin_precio': 0})
for r in meta:
    ad = r[10].strip() or '(sin creativo)'
    precio_str = r[12].strip().replace('$','').replace('.','').replace(',','.')
    try:
        precio = float(precio_str)
    except:
        precio = 0
    creativos[ad]['count'] += 1
    creativos[ad]['revenue'] += precio
    if precio == 0:
        creativos[ad]['sin_precio'] += 1

for ad, d in sorted(creativos.items(), key=lambda x: -x[1]['count']):
    flag = ' <-- SIN PRECIO' if d['sin_precio'] > 0 else ''
    sp = f"{d['sin_precio']}/{d['count']}" if d['sin_precio'] > 0 else ''
    print(f'  {ad:<25} {d["count"]} ventas | ${d["revenue"]:>15,.0f} COP | {sp}{flag}')
