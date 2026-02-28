#!/usr/bin/env python3
"""
Meta Ads Dashboard Builder for Los Lagos Condominio
Reads JSON data files and generates a self-contained HTML dashboard.
"""

import json
import os
import csv
import subprocess
import sys
import base64
import hashlib
import socket
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

# ── File paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN_FILE = os.path.join(SCRIPT_DIR, "ad_insights.json")
DAILY_FILE = os.path.join(SCRIPT_DIR, "daily_insights.json")
ADSET_FILE = os.path.join(SCRIPT_DIR, "adset_insights.json")
DAILY_ADSET_FILE = os.path.join(SCRIPT_DIR, "daily_adset_insights.json")
VENTAS_FILE = os.path.join(SCRIPT_DIR, "ventas_2026.csv")
RESUMEN_FILE = os.path.join(SCRIPT_DIR, "resumen_gsheet.csv")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "dashboard.html")
ENC_KEY_FILE = os.path.join(SCRIPT_DIR, ".openai_key.enc")
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")
_ENC_SALT = "meta-ads-los-lagos-2026"

# ── OpenAI Integration ──────────────────────────────────────────────────────

def _derive_key(salt):
    return hashlib.sha256(salt.encode()).digest()

def _decrypt_api_key(encrypted_b64):
    key = _derive_key(_ENC_SALT)
    encrypted = base64.b64decode(encrypted_b64)
    decrypted = bytes(a ^ b for a, b in zip(encrypted, (key * ((len(encrypted) // len(key)) + 1))[:len(encrypted)]))
    return decrypted.decode()

def load_openai_key():
    """Load OpenAI API key from env var, .env file, or encrypted file."""
    # 1. Environment variable
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    # 2. .env file
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    # 3. Encrypted file
    if os.path.exists(ENC_KEY_FILE):
        with open(ENC_KEY_FILE, "r") as f:
            return _decrypt_api_key(f.read().strip())
    return None

def call_openai(api_key, system_prompt, user_prompt, model="gpt-4o-mini"):
    """Call OpenAI Chat Completions API using stdlib only."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2500,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]

# ── Helpers ─────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_action_value(actions, action_type):
    """Extract a numeric value from the actions list."""
    if not actions:
        return 0
    for a in actions:
        if a["action_type"] == action_type:
            return float(a["value"])
    return 0


def get_cost_per_action(cost_list, action_type):
    if not cost_list:
        return 0
    for a in cost_list:
        if a["action_type"] == action_type:
            return float(a["value"])
    return 0


def fmt_cop(val):
    """Format as COP currency string with compact notation."""
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:,.1f}B".replace(",", ".")
    if val >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M".replace(",", ".")
    return f"${val:,.0f}".replace(",", ".")


def fmt_num(val):
    """Format a number with compact notation."""
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M".replace(",", ".")
    if val >= 1_000:
        return f"{val / 1_000:,.1f}K".replace(",", ".")
    return f"{val:,.0f}".replace(",", ".")


def infer_objective(campaign_name):
    """Infer campaign objective from naming convention."""
    name_upper = campaign_name.upper()
    if "TRAF" in name_upper:
        return "TRAFFIC"
    if "RECON" in name_upper or "MENSAJES" in name_upper:
        return "AWARENESS"
    if "FORM" in name_upper or "LEAD" in name_upper:
        return "LEADS"
    return "OTHER"


# ── Auto-sync ventas from Google Sheet ──────────────────────────────────────
print("Syncing ventas from Google Sheet...")
try:
    subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "sync_ventas.py")],
                   check=True, cwd=SCRIPT_DIR)
except Exception as e:
    print(f"Warning: Could not sync ventas: {e}")


def parse_cop_value(val):
    """Parse COP from Sheet format: $45.626.500 -> 45626500"""
    s = val.strip().replace('$', '').replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0


def load_ventas(path):
    """Load and process ventas CSV from Google Sheet."""
    if not os.path.exists(path):
        print(f"Warning: {path} not found. Run sync_ventas.py first.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = []
        for r in reader:
            if len(r) < 13 or not r[0].strip():
                continue
            rows.append({
                'mes': r[0].strip(),
                'nombre': r[1].strip(),
                'asesor': r[2].strip(),
                'lote': r[3].strip(),
                'dia_contacto': r[4].strip(),
                'dia_cierre': r[5].strip(),
                'dias_cierre': int(r[6].strip()) if r[6].strip().isdigit() else None,
                'fuente': r[7].strip(),
                'campana': r[8].strip(),
                'conjunto': r[9].strip(),
                'anuncio': r[10].strip(),
                'tipo_campana': r[11].strip(),
                'precio': parse_cop_value(r[12]),
            })
    return rows


def load_resumen(path):
    """Load and parse the resumen general CSV (gid=0) from Google Sheet."""
    result = {
        'campaigns_meta': [], 'campaigns_tiktok': [],
        'inversion_mensual': {},  # {fuente: {mes: valor}}
        'info_comercial': {},     # {fuente: {mes: count}}
        'asesores': {},           # {name: {mes: count}}
        'leads_summary': {},      # {item: {mes: valor}}
        'funnel': {},             # {item: {mes: valor}}
        'tiempo_cierre': {},      # {fuente: avg_days}
        'cpa': {},                # {fuente: {mes: valor}}
    }
    if not os.path.exists(path):
        print(f"Warning: {path} not found.")
        return result
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Parse campaign sections (META and TIKTOK)
    section = None
    for i, r in enumerate(rows):
        if len(r) < 1:
            continue
        cell0 = r[0].strip()

        # Detect section markers
        if cell0 == 'FUENTE' and len(r) > 1 and 'INVERSIÓN' in r[1]:
            section = 'inversion'
            continue
        if cell0 == 'CPA' and len(r) > 1 and 'ENERO' in r[1]:
            section = 'cpa'
            continue
        if 'INFORMACION COMERCIAL' in cell0 or (len(r) > 1 and 'INFORMACION COMERCIAL' in r[1]):
            section = 'info_comercial'
            continue
        if 'ASESORES' in cell0 or (len(r) > 1 and 'ASESORES' in r[1]):
            section = 'asesores'
            continue
        if cell0 == 'ITEM' or (len(r) > 1 and cell0 == '' and 'LEADS' in str(r)):
            section = 'leads'
            continue
        if cell0 == 'FUNNEL':
            section = 'funnel'
            continue
        if 'TIEMPO PARA CERRAR' in cell0 or (len(r) > 1 and 'TIEMPO PARA CERRAR' in r[1]):
            section = 'tiempo_cierre'
            continue

        # Parse campaign rows (top section)
        if cell0 and not cell0.startswith('CAMPAÑA') and section is None:
            ubic = r[3].strip() if len(r) > 3 else ''
            if ubic == 'META' and cell0 != 'META':
                inv = parse_cop_value(r[4]) if len(r) > 4 else 0
                ventas = int(r[5]) if len(r) > 5 and r[5].strip().isdigit() else 0
                feb = int(r[7]) if len(r) > 7 and r[7].strip().isdigit() else 0
                result['campaigns_meta'].append({
                    'name': cell0, 'inv': inv, 'ventas': ventas, 'feb': feb
                })
            elif ubic == 'TIKTOK' and cell0 != 'TIKTOK':
                inv = parse_cop_value(r[4]) if len(r) > 4 else 0
                ventas = int(r[5]) if len(r) > 5 and r[5].strip().isdigit() else 0
                feb = int(r[7]) if len(r) > 7 and r[7].strip().isdigit() else 0
                result['campaigns_tiktok'].append({
                    'name': cell0, 'inv': inv, 'ventas': ventas, 'feb': feb
                })

        # Parse inversion mensual
        if section == 'inversion' and cell0 in ('META', 'GOOGLE ADS', 'TIKTOK'):
            result['inversion_mensual'][cell0] = parse_cop_value(r[1]) if len(r) > 1 else 0

        # Parse CPA
        if section == 'cpa' and cell0 in ('META', 'GOOGLE', 'TIKTOK', 'TOTAL CPA'):
            result['cpa'][cell0] = parse_cop_value(r[1]) if len(r) > 1 else 0

        # Parse info comercial
        if section == 'info_comercial' and cell0 and cell0 not in ('TOTAL', '') and 'INFORMACION' not in cell0:
            if len(r) > 2:
                ene = int(r[1]) if r[1].strip().isdigit() else 0
                feb = int(r[2]) if r[2].strip().isdigit() else 0
                result['info_comercial'][cell0] = {'ENERO': ene, 'FEBRERO': feb}

        # Parse leads summary
        if section == 'leads' and cell0.startswith('LEADS') or (section == 'leads' and cell0.startswith('COSTO')):
            result['leads_summary'][cell0] = parse_cop_value(r[1]) if len(r) > 1 else 0

        # Parse funnel
        if section == 'funnel' and cell0 and cell0 != 'FUNNEL':
            val = r[1].strip() if len(r) > 1 else '0'
            if val.replace('.', '').replace(',', '').isdigit():
                result['funnel'][cell0] = parse_cop_value(val)
            else:
                result['funnel'][cell0] = val

        # Parse tiempo cierre
        if section == 'tiempo_cierre' and cell0 in ('META', 'GOOGLE ADS', 'TIKTOK'):
            val = r[1].strip() if len(r) > 1 else '0'
            try:
                result['tiempo_cierre'][cell0] = float(val.replace(',', '.'))
            except:
                result['tiempo_cierre'][cell0] = 0

    return result


# ── Load data ───────────────────────────────────────────────────────────────
print("Loading data files...")
campaign_raw = load_json(CAMPAIGN_FILE)
daily_raw = load_json(DAILY_FILE)
adset_raw = load_json(ADSET_FILE)
daily_adset_raw = load_json(DAILY_ADSET_FILE) if os.path.exists(DAILY_ADSET_FILE) else {"data": []}
ventas_raw = load_ventas(VENTAS_FILE)
resumen_raw = load_resumen(RESUMEN_FILE)

# ── Process campaign-level (30-day aggregate) ───────────────────────────────
campaigns = []
for c in campaign_raw["data"]:
    # The campaign file has one entry per campaign for the 30-day window
    impressions = int(c.get("impressions", 0))
    clicks = int(c.get("clicks", 0))
    spend = float(c.get("spend", 0))
    cpc = float(c.get("cpc", 0))
    cpm = float(c.get("cpm", 0))
    ctr = float(c.get("ctr", 0))
    reach = int(c.get("reach", 0))
    frequency = float(c.get("frequency", 0))

    actions = c.get("actions", [])
    cost_actions = c.get("cost_per_action_type", [])

    leads = get_action_value(actions, "lead")
    link_clicks = get_action_value(actions, "link_click")
    landing_page_views = get_action_value(actions, "landing_page_view")
    video_views = get_action_value(actions, "video_view")
    post_engagement = get_action_value(actions, "post_engagement")
    messaging = get_action_value(actions, "onsite_conversion.total_messaging_connection")

    cpl = get_cost_per_action(cost_actions, "lead")
    if cpl == 0 and leads > 0:
        cpl = spend / leads

    objective = infer_objective(c["campaign_name"])

    campaigns.append({
        "name": c["campaign_name"],
        "id": c["campaign_id"],
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "cpc": cpc,
        "cpm": cpm,
        "ctr": ctr,
        "reach": reach,
        "frequency": frequency,
        "leads": int(leads),
        "link_clicks": int(link_clicks),
        "landing_page_views": int(landing_page_views),
        "video_views": int(video_views),
        "post_engagement": int(post_engagement),
        "messaging": int(messaging),
        "cpl": cpl,
        "objective": objective,
    })

# ── Detect ON/OFF status using recent daily data ───────────────────────────
all_daily_dates = sorted(set(r['date_start'] for r in daily_raw['data']))
last_3_dates = set(all_daily_dates[-3:]) if len(all_daily_dates) >= 3 else set(all_daily_dates)
recent_spend_by_camp = defaultdict(float)
for r in daily_raw['data']:
    if r['date_start'] in last_3_dates:
        recent_spend_by_camp[r['campaign_name']] += float(r.get('spend', 0))

for c in campaigns:
    c['is_active'] = recent_spend_by_camp.get(c['name'], 0) > 0

active_count = sum(1 for c in campaigns if c['is_active'])
paused_count = sum(1 for c in campaigns if not c['is_active'])
print(f"  Campaigns: {len(campaigns)} total ({active_count} ON, {paused_count} OFF)")

# Sort by spend desc
campaigns.sort(key=lambda x: x["spend"], reverse=True)

# ── Compute account-level KPIs ──────────────────────────────────────────────
total_spend = sum(c["spend"] for c in campaigns)
total_impressions = sum(c["impressions"] for c in campaigns)
total_clicks = sum(c["clicks"] for c in campaigns)
total_reach = sum(c["reach"] for c in campaigns)
total_leads = sum(c["leads"] for c in campaigns)
total_link_clicks = sum(c["link_clicks"] for c in campaigns)
total_landing_views = sum(c["landing_page_views"] for c in campaigns)
total_video_views = sum(c["video_views"] for c in campaigns)
total_engagement = sum(c["post_engagement"] for c in campaigns)
total_messaging = sum(c["messaging"] for c in campaigns)

avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
avg_cpm = (total_spend / total_impressions * 1000) if total_impressions else 0
avg_cpl = (total_spend / total_leads) if total_leads else 0

# ── Process daily insights ──────────────────────────────────────────────────
# Daily data has one entry per campaign per day
daily_agg = defaultdict(lambda: {
    "spend": 0, "impressions": 0, "clicks": 0, "leads": 0,
    "link_clicks": 0, "video_views": 0, "reach": 0
})

for row in daily_raw["data"]:
    date = row["date_start"]
    daily_agg[date]["spend"] += float(row.get("spend", 0))
    daily_agg[date]["impressions"] += int(row.get("impressions", 0))
    daily_agg[date]["clicks"] += int(row.get("clicks", 0))
    daily_agg[date]["reach"] += int(row.get("reach", 0))

    actions = row.get("actions", [])
    daily_agg[date]["leads"] += int(get_action_value(actions, "lead"))
    daily_agg[date]["link_clicks"] += int(get_action_value(actions, "link_click"))
    daily_agg[date]["video_views"] += int(get_action_value(actions, "video_view"))

# Sort by date
daily_dates = sorted(daily_agg.keys())
daily_spend = [daily_agg[d]["spend"] for d in daily_dates]
daily_leads = [daily_agg[d]["leads"] for d in daily_dates]
daily_impressions = [daily_agg[d]["impressions"] for d in daily_dates]
daily_clicks = [daily_agg[d]["clicks"] for d in daily_dates]
daily_cpl = []
daily_ctr = []
daily_cpm = []
for d in daily_dates:
    imp = daily_agg[d]["impressions"]
    cl = daily_agg[d]["clicks"]
    sp = daily_agg[d]["spend"]
    ld = daily_agg[d]["leads"]
    daily_cpl.append(round(sp / ld, 0) if ld > 0 else 0)
    daily_ctr.append(round(cl / imp * 100, 2) if imp > 0 else 0)
    daily_cpm.append(round(sp / imp * 1000, 0) if imp > 0 else 0)

# Format dates for display (DD/MM)
daily_labels = []
for d in daily_dates:
    parts = d.split("-")
    daily_labels.append(f"{parts[2]}/{parts[1]}")

# Full ISO dates for JS filtering
daily_iso_dates = daily_dates  # ['2026-01-28', '2026-01-29', ...]

# Prepare ventas as JSON for JS filtering
ventas_json_list = []
for v in ventas_raw:
    ventas_json_list.append({
        'mes': v['mes'],
        'nombre': v['nombre'],
        'asesor': v['asesor'],
        'lote': v['lote'],
        'fuente': v['fuente'],
        'campana': v['campana'],
        'conjunto': v['conjunto'],
        'anuncio': v['anuncio'],
        'precio': v['precio'],
        'dia_cierre': v['dia_cierre'],
        'dias_cierre': v['dias_cierre'],
    })

# ── Process ad set data ─────────────────────────────────────────────────────
adsets = []
for a in adset_raw["data"]:
    impressions = int(a.get("impressions", 0))
    clicks = int(a.get("clicks", 0))
    spend = float(a.get("spend", 0))
    cpc = float(a.get("cpc", 0))
    cpm = float(a.get("cpm", 0))
    ctr = float(a.get("ctr", 0))
    reach = int(a.get("reach", 0))
    frequency = float(a.get("frequency", 0))

    actions = a.get("actions", [])
    cost_actions = a.get("cost_per_action_type", [])

    leads = get_action_value(actions, "lead")
    link_clicks = get_action_value(actions, "link_click")
    video_views = get_action_value(actions, "video_view")
    post_engagement = get_action_value(actions, "post_engagement")

    cpl = get_cost_per_action(cost_actions, "lead")
    if cpl == 0 and leads > 0:
        cpl = spend / leads

    adsets.append({
        "campaign_name": a.get("campaign_name", ""),
        "name": a.get("adset_name", ""),
        "id": a.get("adset_id", ""),
        "impressions": impressions,
        "clicks": clicks,
        "spend": spend,
        "cpc": cpc,
        "cpm": cpm,
        "ctr": ctr,
        "reach": reach,
        "frequency": frequency,
        "leads": int(leads),
        "link_clicks": int(link_clicks),
        "video_views": int(video_views),
        "post_engagement": int(post_engagement),
        "cpl": cpl,
    })

# Detect ON/OFF for adsets based on their parent campaign status
_active_camp_names = set(c['name'] for c in campaigns if c.get('is_active', False))
for a in adsets:
    a['is_active'] = a['campaign_name'] in _active_camp_names

adset_active_count = sum(1 for a in adsets if a['is_active'])
adset_paused_count = sum(1 for a in adsets if not a['is_active'])
print(f"  Ad Sets: {len(adsets)} total ({adset_active_count} ON, {adset_paused_count} OFF)")

# Sort: ON first, then by spend desc
adsets.sort(key=lambda x: (0 if x['is_active'] else 1, -x['spend']))

# ── Process Ventas Data ─────────────────────────────────────────────────────
print("Processing ventas data...")

# All ventas
ventas_total_count = len(ventas_raw)
ventas_total_revenue = sum(v['precio'] for v in ventas_raw)

# By source
ventas_by_source = defaultdict(lambda: {'count': 0, 'revenue': 0})
for v in ventas_raw:
    src = v['fuente']
    if src:
        ventas_by_source[src]['count'] += 1
        ventas_by_source[src]['revenue'] += v['precio']

# META ventas only
meta_ventas = [v for v in ventas_raw if v['fuente'] == 'META']
meta_ventas_count = len(meta_ventas)
meta_ventas_revenue = sum(v['precio'] for v in meta_ventas)
meta_avg_ticket = meta_ventas_revenue / meta_ventas_count if meta_ventas_count else 0

# Days to close (META only)
meta_dias = [v['dias_cierre'] for v in meta_ventas if v['dias_cierre'] is not None]
meta_avg_dias = sum(meta_dias) / len(meta_dias) if meta_dias else 0
meta_median_dias = sorted(meta_dias)[len(meta_dias)//2] if meta_dias else 0

# ROAS calculation: META revenue / META Ads spend
roas = meta_ventas_revenue / total_spend if total_spend > 0 else 0

# By month
ventas_by_month = defaultdict(lambda: {'total': 0, 'revenue': 0, 'meta': 0, 'meta_revenue': 0})
for v in ventas_raw:
    m = v['mes']
    ventas_by_month[m]['total'] += 1
    ventas_by_month[m]['revenue'] += v['precio']
    if v['fuente'] == 'META':
        ventas_by_month[m]['meta'] += 1
        ventas_by_month[m]['meta_revenue'] += v['precio']

# Top campaigns by sales (normalize name for matching)
def normalize_camp_name(name):
    return name.strip().lower().replace('  ', ' ')

meta_ventas_by_campaign = defaultdict(lambda: {'count': 0, 'revenue': 0})
for v in meta_ventas:
    cn = normalize_camp_name(v['campana'])
    if cn:
        meta_ventas_by_campaign[cn]['count'] += 1
        meta_ventas_by_campaign[cn]['revenue'] += v['precio']

# Top asesores
meta_ventas_by_asesor = defaultdict(lambda: {'count': 0, 'revenue': 0})
for v in meta_ventas:
    name = v['nombre']
    if name and name != 'INMOBILIARIA':
        meta_ventas_by_asesor[name]['count'] += 1
        meta_ventas_by_asesor[name]['revenue'] += v['precio']

# Top creativos (anuncios)
meta_ventas_by_creative = defaultdict(lambda: {'count': 0, 'revenue': 0})
for v in meta_ventas:
    ad = v['anuncio']
    if ad:
        meta_ventas_by_creative[ad]['count'] += 1
        meta_ventas_by_creative[ad]['revenue'] += v['precio']

# Cross-reference: campaign spend vs revenue (ROAS per campaign)
campaign_roas = []
for c in campaigns:
    cn = normalize_camp_name(c['name'])
    vdata = meta_ventas_by_campaign.get(cn, {'count': 0, 'revenue': 0})
    camp_roas = vdata['revenue'] / c['spend'] if c['spend'] > 0 else 0
    campaign_roas.append({
        'name': c['name'],
        'spend': c['spend'],
        'leads': c['leads'],
        'ventas': vdata['count'],
        'revenue': vdata['revenue'],
        'roas': camp_roas,
        'conversion_rate': (vdata['count'] / c['leads'] * 100) if c['leads'] > 0 else 0,
        'cost_per_sale': c['spend'] / vdata['count'] if vdata['count'] > 0 else 0,
    })

campaign_roas.sort(key=lambda x: x['revenue'], reverse=True)

# Source chart data
source_labels = []
source_counts = []
source_revenues = []
for src, data in sorted(ventas_by_source.items(), key=lambda x: -x[1]['revenue']):
    source_labels.append(src)
    source_counts.append(data['count'])
    source_revenues.append(data['revenue'])

print(f"  Ventas totales: {ventas_total_count}")
print(f"  Ventas META: {meta_ventas_count}")
print(f"  Revenue META: ${meta_ventas_revenue:,.0f} COP")
print(f"  ROAS META: {roas:.1f}x")

# ── Objective distribution (spend) ──────────────────────────────────────────
obj_spend = defaultdict(float)
for c in campaigns:
    obj_spend[c["objective"]] += c["spend"]

obj_labels = list(obj_spend.keys())
obj_values = [obj_spend[k] for k in obj_labels]

# Spanish labels for objectives
obj_labels_es = []
for o in obj_labels:
    if o == "LEADS":
        obj_labels_es.append("Leads / Formularios")
    elif o == "TRAFFIC":
        obj_labels_es.append("Trafico")
    elif o == "AWARENESS":
        obj_labels_es.append("Reconocimiento")
    else:
        obj_labels_es.append("Otro")

# ── Top & Bottom performers by CPL (only active campaigns with leads) ───────
lead_campaigns = [c for c in campaigns if c["leads"] > 0 and c["cpl"] > 0 and c.get('is_active', True)]
lead_campaigns_sorted = sorted(lead_campaigns, key=lambda x: x["cpl"])
top_performers = lead_campaigns_sorted[:3]
bottom_performers = lead_campaigns_sorted[-3:]
bottom_performers.reverse()

# ── Build campaign table rows ───────────────────────────────────────────────
def build_campaign_rows():
    rows = []
    # Sort: ON campaigns first, then OFF
    sorted_camps = sorted(campaigns, key=lambda c: (0 if c.get('is_active', True) else 1, -c['spend']))
    cpls = [c["cpl"] for c in sorted_camps if c["cpl"] > 0]
    min_cpl = min(cpls) if cpls else 0
    max_cpl = max(cpls) if cpls else 1

    for c in sorted_camps:
        cpl_class = ""
        if c["cpl"] > 0:
            ratio = (c["cpl"] - min_cpl) / (max_cpl - min_cpl) if max_cpl != min_cpl else 0.5
            if ratio < 0.33:
                cpl_class = "cpl-low"
            elif ratio < 0.66:
                cpl_class = "cpl-mid"
            else:
                cpl_class = "cpl-high"

        obj_badge = ""
        if c["objective"] == "LEADS":
            obj_badge = '<span class="badge badge-leads">Leads</span>'
        elif c["objective"] == "TRAFFIC":
            obj_badge = '<span class="badge badge-traffic">Trafico</span>'
        elif c["objective"] == "AWARENESS":
            obj_badge = '<span class="badge badge-awareness">Awareness</span>'
        else:
            obj_badge = '<span class="badge badge-other">Otro</span>'

        is_on = c.get('is_active', True)
        status_badge = '<span class="badge badge-leads" style="margin-left:6px">ON</span>' if is_on else '<span class="badge" style="background:rgba(255,75,75,0.15);color:#ff4b4b;margin-left:6px;font-weight:700">OFF</span>'
        row_style = '' if is_on else ' style="opacity:0.45"'

        cpl_display = f'${c["cpl"]:,.0f}'.replace(",", ".") if c["cpl"] > 0 else "-"
        spend_display = f'${c["spend"]:,.0f}'.replace(",", ".")

        rows.append(f"""<tr{row_style}>
            <td class="campaign-name">{c['name']} {obj_badge} {status_badge}</td>
            <td class="num">{spend_display}</td>
            <td class="num">{c['impressions']:,}</td>
            <td class="num">{c['clicks']:,}</td>
            <td class="num">{c['ctr']:.2f}%</td>
            <td class="num">{c['leads']}</td>
            <td class="num {cpl_class}">{cpl_display}</td>
            <td class="num">{c['link_clicks']:,}</td>
            <td class="num">{c['video_views']:,}</td>
        </tr>""")
    return "\n".join(rows)


def build_adset_rows():
    rows = []
    cpls = [a["cpl"] for a in adsets if a["cpl"] > 0]
    min_cpl = min(cpls) if cpls else 0
    max_cpl = max(cpls) if cpls else 1

    for a in adsets:
        cpl_class = ""
        if a["cpl"] > 0:
            ratio = (a["cpl"] - min_cpl) / (max_cpl - min_cpl) if max_cpl != min_cpl else 0.5
            if ratio < 0.33:
                cpl_class = "cpl-low"
            elif ratio < 0.66:
                cpl_class = "cpl-mid"
            else:
                cpl_class = "cpl-high"

        is_on = a.get('is_active', True)
        status_badge = '<span class="badge badge-leads" style="margin-left:6px">ON</span>' if is_on else '<span class="badge" style="background:rgba(255,75,75,0.15);color:#ff4b4b;margin-left:6px;font-weight:700">OFF</span>'
        row_style = '' if is_on else ' style="opacity:0.45"'

        cpl_display = f'${a["cpl"]:,.0f}'.replace(",", ".") if a["cpl"] > 0 else "-"
        spend_display = f'${a["spend"]:,.0f}'.replace(",", ".")

        rows.append(f"""<tr{row_style}>
            <td class="campaign-name">{a['campaign_name']}</td>
            <td class="adset-name">{a['name']} {status_badge}</td>
            <td class="num">{spend_display}</td>
            <td class="num">{a['impressions']:,}</td>
            <td class="num">{a['clicks']:,}</td>
            <td class="num">{a['ctr']:.2f}%</td>
            <td class="num">{a['leads']}</td>
            <td class="num {cpl_class}">{cpl_display}</td>
            <td class="num">{a['link_clicks']:,}</td>
            <td class="num">{a['video_views']:,}</td>
        </tr>""")
    return "\n".join(rows)


def build_ventas_source_rows():
    """Build rows for the source attribution table."""
    rows = []
    for src, data in sorted(ventas_by_source.items(), key=lambda x: -x[1]['revenue']):
        pct_count = (data['count'] / ventas_total_count * 100) if ventas_total_count else 0
        pct_rev = (data['revenue'] / ventas_total_revenue * 100) if ventas_total_revenue else 0
        if data['revenue'] > 0:
            rev_display = f"${data['revenue']:,.0f}".replace(",", ".")
        else:
            rev_display = '<span style="color:var(--text-muted);font-size:11px">Sin dato</span>'
        color = '#4361ee' if src == 'META' else '#8892b0'
        rows.append(f"""<tr>
            <td style="font-weight:600; color:{color}">{src}</td>
            <td class="num">{data['count']}</td>
            <td class="num">{pct_count:.1f}%</td>
            <td class="num">{rev_display}</td>
            <td class="num">{pct_rev:.1f}%</td>
        </tr>""")
    return "\n".join(rows)


def build_campaign_roas_rows():
    """Build rows for the campaign ROAS cross-reference table."""
    rows = []
    for cr in campaign_roas:
        if cr['spend'] == 0:
            continue
        spend_d = f"${cr['spend']:,.0f}".replace(",", ".")
        if cr['revenue'] > 0:
            rev_d = f"${cr['revenue']:,.0f}".replace(",", ".")
        elif cr['ventas'] > 0:
            rev_d = '<span style="color:var(--accent-orange);font-size:11px">Pendiente</span>'
        else:
            rev_d = "-"
        roas_d = f"{cr['roas']:.1f}x" if cr['roas'] > 0 else "-"
        conv_d = f"{cr['conversion_rate']:.1f}%" if cr['conversion_rate'] > 0 else "-"
        cps_d = f"${cr['cost_per_sale']:,.0f}".replace(",", ".") if cr['cost_per_sale'] > 0 else "-"
        
        roas_class = ""
        if cr['roas'] >= 5:
            roas_class = "cpl-low"
        elif cr['roas'] >= 2:
            roas_class = "cpl-mid"
        elif cr['roas'] > 0:
            roas_class = "cpl-high"
        
        rows.append(f"""<tr>
            <td class="campaign-name">{cr['name']}</td>
            <td class="num">{spend_d}</td>
            <td class="num">{cr['leads']}</td>
            <td class="num" style="font-weight:700">{cr['ventas']}</td>
            <td class="num">{conv_d}</td>
            <td class="num">{rev_d}</td>
            <td class="num {roas_class}" style="font-weight:700">{roas_d}</td>
            <td class="num">{cps_d}</td>
        </tr>""")
    return "\n".join(rows)


def build_asesor_rows():
    """Build rows for asesores table."""
    rows = []
    for name, data in sorted(meta_ventas_by_asesor.items(), key=lambda x: -x[1]['revenue']):
        rev_d = f"${data['revenue']:,.0f}".replace(",", ".")
        avg_d = f"${data['revenue']/data['count']:,.0f}".replace(",", ".") if data['count'] else "-"
        rows.append(f"""<tr>
            <td style="font-weight:600">{name}</td>
            <td class="num">{data['count']}</td>
            <td class="num">{rev_d}</td>
            <td class="num">{avg_d}</td>
        </tr>""")
    return "\n".join(rows)


def build_creative_ventas_rows():
    """Build rows for creative performance by actual sales."""
    rows = []
    for ad, data in sorted(meta_ventas_by_creative.items(), key=lambda x: -x[1]['count'])[:12]:
        if data['revenue'] > 0:
            rev_d = f"${data['revenue']:,.0f}".replace(",", ".")
        elif data['count'] > 0:
            rev_d = '<span style="color:var(--accent-orange);font-size:11px">Precio pendiente</span>'
        else:
            continue
        rows.append(f"""<tr>
            <td style="font-weight:600">{ad}</td>
            <td class="num">{data['count']}</td>
            <td class="num">{rev_d}</td>
        </tr>""")
    return "\n".join(rows)


def build_performer_cards(performers, is_top=True):
    cards = []
    for i, c in enumerate(performers):
        rank = i + 1
        icon = "&#9650;" if is_top else "&#9660;"
        color = "#00d4aa" if is_top else "#ff6b6b"
        cpl_display = f'${c["cpl"]:,.0f}'.replace(",", ".")
        spend_display = f'${c["spend"]:,.0f}'.replace(",", ".")

        cards.append(f"""
        <div class="performer-card" style="border-left: 4px solid {color}">
            <div class="performer-rank" style="color: {color}">{icon} #{rank}</div>
            <div class="performer-name">{c['name']}</div>
            <div class="performer-stats">
                <div class="performer-stat">
                    <span class="stat-label">CPL</span>
                    <span class="stat-value" style="color: {color}">{cpl_display}</span>
                </div>
                <div class="performer-stat">
                    <span class="stat-label">Leads</span>
                    <span class="stat-value">{c['leads']}</span>
                </div>
                <div class="performer-stat">
                    <span class="stat-label">Inversion</span>
                    <span class="stat-value">{spend_display}</span>
                </div>
            </div>
        </div>
        """)
    return "\n".join(cards)


# ── Build Google Sheet comparison data ──────────────────────────────────────
def build_sheet_comparison_section():
    """Build HTML for multi-channel comparison from Google Sheet data."""
    inv = resumen_raw.get('inversion_mensual', {})
    cpa_data = resumen_raw.get('cpa', {})
    info = resumen_raw.get('info_comercial', {})
    funnel_data = resumen_raw.get('funnel', {})
    tiempo = resumen_raw.get('tiempo_cierre', {})

    # Inversion comparison cards
    meta_inv = inv.get('META', 0)
    tiktok_inv = inv.get('TIKTOK', 0)
    google_inv = inv.get('GOOGLE ADS', 0)
    total_inv = meta_inv + tiktok_inv + google_inv

    # CPA by channel
    meta_cpa = cpa_data.get('META', 0)
    google_cpa = cpa_data.get('GOOGLE', 0)
    tiktok_cpa = cpa_data.get('TIKTOK', 0)

    # Ventas by source (from info comercial)
    ventas_info = {}
    for src, months in info.items():
        total = sum(months.values())
        ventas_info[src] = {'total': total, **months}

    # Funnel data
    leads_total = funnel_data.get('LEADS TOTALES', 0)
    leads_cp = funnel_data.get('LEADS CP', 0)
    contactos = funnel_data.get('CONTACTOS UNICOS', 0)
    llamadas = funnel_data.get('LLAMADAS HECHAS', 0)
    contestadas = funnel_data.get('LLAMADAS CONTESTADAS', 0)
    visita_agendada = funnel_data.get('VISITA AGENDADA', 0)
    visita_cumplida = funnel_data.get('VISITA CUMPLIDA', 0)
    cierre_campana = funnel_data.get('CIERRE X CAMPA\u00d1A', 0)

    # TikTok campaigns
    tiktok_camps = resumen_raw.get('campaigns_tiktok', [])

    # Pre-compute ventas counts per platform
    meta_ventas_sheet = info.get("META", {}).get("ENERO", 0) + info.get("META", {}).get("FEBRERO", 0)
    tiktok_ventas_sheet = info.get("TIKTOK", {}).get("ENERO", 0) + info.get("TIKTOK", {}).get("FEBRERO", 0)
    google_ventas_sheet = info.get("GOOGLE ADS", {}).get("ENERO", 0) + info.get("GOOGLE ADS", {}).get("FEBRERO", 0)

    html_parts = []

    # Multi-channel investment KPIs
    html_parts.append(f'''
    <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));">
        <div class="kpi-card animate-in" style="border:1px solid rgba(67,97,238,0.3)">
            <span class="kpi-icon">&#128312;</span>
            <div class="kpi-label">Meta Ads</div>
            <div class="kpi-value" style="color:var(--accent-blue)">{fmt_cop(meta_inv)}</div>
            <div class="kpi-sub">CPA: {fmt_cop(meta_cpa) if meta_cpa else "N/A"} | {meta_ventas_sheet} ventas</div>
        </div>
        <div class="kpi-card animate-in" style="border:1px solid rgba(255,0,80,0.3)">
            <span class="kpi-icon">&#127916;</span>
            <div class="kpi-label">TikTok Ads</div>
            <div class="kpi-value" style="color:#ff0050">{fmt_cop(tiktok_inv)}</div>
            <div class="kpi-sub">CPA: {fmt_cop(tiktok_cpa) if tiktok_cpa else "N/A"} | {tiktok_ventas_sheet} ventas</div>
        </div>
        <div class="kpi-card animate-in" style="border:1px solid rgba(66,133,244,0.3)">
            <span class="kpi-icon">&#128270;</span>
            <div class="kpi-label">Google Ads</div>
            <div class="kpi-value" style="color:#4285f4">{fmt_cop(google_inv)}</div>
            <div class="kpi-sub">CPA: {fmt_cop(google_cpa) if google_cpa else "N/A"} | {google_ventas_sheet} ventas</div>
        </div>
        <div class="kpi-card animate-in" style="border:1px solid rgba(255,159,67,0.3)">
            <span class="kpi-icon">&#128176;</span>
            <div class="kpi-label">Total Multicanal</div>
            <div class="kpi-value" style="color:var(--accent-orange)">{fmt_cop(total_inv)}</div>
            <div class="kpi-sub">Todas las plataformas Enero 2026</div>
        </div>
    </div>''')

    # Funnel section
    if leads_total or contactos or llamadas:
        funnel_items = [
            ("Leads Totales", leads_total, "#4361ee"),
            ("Contactos Unicos", contactos, "#7b2ff7"),
            ("Llamadas Hechas", llamadas, "#ff9f43"),
            ("Llamadas Contestadas", contestadas, "#00d4aa"),
            ("Visitas Agendadas", visita_agendada, "#ff6b9d"),
            ("Visitas Cumplidas", visita_cumplida, "#ff6b6b"),
            ("Cierres", cierre_campana, "#00d4aa"),
        ]
        max_val = max(v for _, v, _ in funnel_items if isinstance(v, (int, float))) if funnel_items else 1

        funnel_html = ""
        for label, val, color in funnel_items:
            if not isinstance(val, (int, float)) or val == 0:
                continue
            pct = val / max_val * 100 if max_val > 0 else 0
            val_display = f"{int(val):,}" if isinstance(val, (int, float)) else str(val)
            funnel_html += f'''
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <div style="width:160px;font-size:12px;color:var(--text-secondary);text-align:right">{label}</div>
                <div style="flex:1;background:var(--bg-card-alt);border-radius:6px;height:28px;overflow:hidden;position:relative">
                    <div style="background:{color};height:100%;width:{pct}%;border-radius:6px;transition:width 0.6s ease"></div>
                    <span style="position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:12px;font-weight:600;color:var(--text-primary)">{val_display}</span>
                </div>
            </div>'''

        html_parts.append(f'''
    <div class="chart-grid" style="margin-top:20px">
        <div class="section" style="margin-bottom:0">
            <div class="section-title"><span class="icon">&#128200;</span> Funnel Comercial (Enero)</div>
            <div style="padding:16px">{funnel_html}</div>
        </div>
        <div class="section" style="margin-bottom:0">
            <div class="section-title"><span class="icon">&#9201;</span> Tiempo Promedio de Cierre (dias)</div>
            <div class="table-wrapper"><table>
                <thead><tr><th>Fuente</th><th>Dias Promedio</th></tr></thead>
                <tbody>''')
        for src in ['META', 'GOOGLE ADS', 'TIKTOK']:
            days = tiempo.get(src, 0)
            color = 'var(--accent-cyan)' if days and days <= 10 else 'var(--accent-orange)' if days and days <= 20 else 'var(--accent-red)'
            html_parts.append(f'''
                    <tr><td style="font-weight:600">{src}</td><td class="num" style="color:{color};font-weight:700">{days:.0f} dias</td></tr>''')
        html_parts.append('''
                </tbody>
            </table></div>
        </div>
    </div>''')

    # TikTok campaigns table
    if tiktok_camps:
        tk_rows = ""
        for tk in tiktok_camps:
            inv_d = fmt_cop(tk['inv']) if tk['inv'] > 0 else "-"
            cpa_d = fmt_cop(tk['inv'] / tk['ventas']) if tk['ventas'] > 0 else "-"
            tk_rows += f"""<tr>
                <td class="campaign-name">{tk['name']}</td>
                <td class="num">{inv_d}</td>
                <td class="num" style="font-weight:700">{tk['ventas']}</td>
                <td class="num">{cpa_d}</td>
                <td class="num">{tk['feb']}</td>
            </tr>"""
        html_parts.append(f'''
    <div class="section" style="margin-top:20px">
        <div class="section-title"><span class="icon">&#127916;</span> Campanas TikTok (Google Sheet)</div>
        <div class="table-wrapper"><div class="table-scroll"><table>
            <thead><tr>
                <th>Campana</th><th>Inversion Total</th><th>Ventas</th><th>CPA</th><th>Feb</th>
            </tr></thead>
            <tbody>{tk_rows}</tbody>
        </table></div></div>
    </div>''')

    return "\n".join(html_parts)

sheet_comparison_html = build_sheet_comparison_section()
print(f"  Sheet comparison section built.")


# ── Generate HTML ───────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

# Dynamic date range from daily data
def format_date_es(date_str):
    """Convert YYYY-MM-DD to 'DD Mon YYYY' in Spanish."""
    meses = {'01':'Ene','02':'Feb','03':'Mar','04':'Abr','05':'May','06':'Jun',
             '07':'Jul','08':'Ago','09':'Sep','10':'Oct','11':'Nov','12':'Dic'}
    parts = date_str.split('-')
    return f"{int(parts[2])} {meses[parts[1]]} {parts[0]}"

date_start_str = format_date_es(daily_dates[0]) if daily_dates else "?"
date_end_str = format_date_es(daily_dates[-1]) if daily_dates else "?"
total_data_days = len(daily_dates)

# ── Build dynamic filter buttons ────────────────────────────────────────────
# Calculate which months we have data for
data_months = set()
if daily_dates:
    for d in daily_dates:
        m = d.split('-')[1]
        data_months.add(m)

# Filter buttons for Ads: show real data range options
filter_buttons_ads = []
if total_data_days >= 7:
    filter_buttons_ads.append(('7', '7 dias'))
if total_data_days >= 14:
    filter_buttons_ads.append(('14', '14 dias'))
if total_data_days >= 21:
    filter_buttons_ads.append(('21', '21 dias'))
filter_buttons_ads.append((str(total_data_days), f'Todo ({total_data_days}d)'))

# Filter buttons for Ventas: dynamic from available months
ventas_months_available = sorted(ventas_by_month.keys())
filter_buttons_ventas = [('ALL', 'Todos')]
for m in ventas_months_available:
    filter_buttons_ventas.append((m, m.capitalize()))

# ── Build dynamic AI analysis ───────────────────────────────────────────────
# Analysis is now generated client-side in JavaScript for dynamic updates
# We just need to prepare the data payload

import json as _json

# ── OpenAI-Powered Analysis ─────────────────────────────────────────────────
print("Generating AI Analysis via OpenAI...")

_openai_key = load_openai_key()
_ai_analysis = None

if _openai_key:
    # Build comprehensive data summary for OpenAI
    _active_camps = [c for c in campaigns if c.get('is_active', False)]
    _paused_camps = [c for c in campaigns if not c.get('is_active', False)]
    _active_adset_list = [a for a in adsets if a.get('is_active', False)]
    _paused_adset_list = [a for a in adsets if not a.get('is_active', False)]

    # Daily trends for last 7 days
    _sorted_daily = sorted(daily_raw['data'], key=lambda d: d['date_start'])
    _last7_daily = _sorted_daily[-7:] if len(_sorted_daily) >= 7 else _sorted_daily
    _prev7_daily = _sorted_daily[-14:-7] if len(_sorted_daily) >= 14 else []

    # Aggregate weekly data
    def _week_agg(daily_list):
        s = sum(float(d.get('spend', 0)) for d in daily_list)
        l_vals = []
        for d in daily_list:
            for act in d.get('actions', []):
                if act['action_type'] == 'lead':
                    l_vals.append(int(act['value']))
        leads = sum(l_vals)
        return s, leads, (s / leads if leads > 0 else 0)

    _w2_spend, _w2_leads, _w2_cpl = _week_agg(_last7_daily)
    _w1_spend, _w1_leads, _w1_cpl = _week_agg(_prev7_daily) if _prev7_daily else (0, 0, 0)

    _camp_lines = []
    for c in sorted(_active_camps, key=lambda x: -x['spend']):
        _camp_lines.append(
            f"  - {c['name']} | Spend: ${c['spend']:,.0f} | Leads: {c['leads']} | "
            f"CPL: ${c['cpl']:,.0f} | CTR: {c['ctr']:.2f}% | Freq: {c.get('frequency',0):.2f} | "
            f"Reach: {c.get('reach',0):,} | Impr: {c.get('impressions',0):,}"
        )

    _adset_lines = []
    for a in sorted(_active_adset_list, key=lambda x: -x['spend']):
        _adset_lines.append(
            f"  - {a['campaign_name']} → {a['name']} | Spend: ${a['spend']:,.0f} | "
            f"Leads: {a['leads']} | CPL: ${a['cpl']:,.0f} | CTR: {a['ctr']:.2f}% | "
            f"Freq: {a['frequency']:.2f} | Reach: {a['reach']:,}"
        )

    _paused_lines = []
    for c in sorted(_paused_camps, key=lambda x: -x['spend']):
        _paused_lines.append(f"  - {c['name']} | Spend: ${c['spend']:,.0f} | Leads: {c['leads']} | CPL: ${c['cpl']:,.0f}")

    _daily_lines = []
    for d in _last7_daily:
        d_leads = sum(int(act['value']) for act in d.get('actions', []) if act['action_type'] == 'lead')
        d_spend = float(d.get('spend', 0))
        _daily_lines.append(
            f"  - {d['date_start']} | Spend: ${d_spend:,.0f} | Leads: {d_leads} | "
            f"CPM: ${float(d.get('cpm',0)):,.0f} | CTR: {float(d.get('ctr',0)):.2f}%"
        )

    _avg_cpm = total_impressions > 0 and (total_spend / total_impressions * 1000) or 0
    _avg_cpc = total_clicks > 0 and (total_spend / total_clicks) or 0
    _cpl_usd = avg_cpl / 4400 if avg_cpl > 0 else 0
    _date_range = f"{daily_dates[0]} a {daily_dates[-1]}" if daily_dates else "N/A"

    _system_prompt = (
        "Eres un analista senior de performance marketing especializado en Meta Ads "
        "(Facebook e Instagram) para el sector inmobiliario en Colombia. Tu cliente es "
        "'Los Lagos Condominio', un proyecto de vivienda nueva. "
        "Genera insights accionables, especificos y basados en datos numericos. "
        "Cada insight debe ser 1-2 oraciones concisas con cifras concretas. "
        "NO uses emojis. NO uses markdown. Usa texto plano con numeros. "
        "NO menciones Google Sheets, ni datos de ventas, ni ROAS de ventas. "
        "100% enfocado en metricas de Meta Ads: CPL, CTR, CPM, frecuencia, reach, "
        "impresiones, engagement, overlap, learning phase, fatiga de creativos, "
        "segmentacion, bid strategies, pacing."
    )

    _user_prompt = f"""Analiza estos datos de Meta Ads para Los Lagos Condominio y genera recomendaciones:

RESUMEN GENERAL (periodo: {_date_range}, {len(daily_dates)} dias):
- Inversion total: ${total_spend:,.0f} COP
- Leads totales: {total_leads:,}
- CPL promedio: ${avg_cpl:,.0f} COP (~${_cpl_usd:.2f} USD)
- CTR: {avg_ctr:.2f}%
- CPM: ${_avg_cpm:,.0f} COP
- CPC: ${_avg_cpc:,.0f} COP
- Impresiones: {total_impressions:,}
- Alcance: {total_reach:,}
- Video Views: {total_video_views:,}
- Engagement: {total_engagement:,}
- Mensajeria: {total_messaging:,}

ESTADO DE CUENTA:
- Campanas activas (ON): {active_count} de {len(campaigns)}
- Conjuntos activos: {len(_active_adset_list)} de {len(adsets)}
- Campanas pausadas: {paused_count}

CAMPANAS ACTIVAS (ordenadas por inversion):
{chr(10).join(_camp_lines)}

CAMPANAS PAUSADAS:
{chr(10).join(_paused_lines) if _paused_lines else '  Ninguna'}

CONJUNTOS DE ANUNCIOS ACTIVOS (ordenados por inversion):
{chr(10).join(_adset_lines)}

TENDENCIA DIARIA (ultimos 7 dias):
{chr(10).join(_daily_lines)}

TENDENCIA SEMANAL:
- Semana anterior: Spend ${_w1_spend:,.0f} | Leads: {_w1_leads} | CPL: ${_w1_cpl:,.0f}
- Ultima semana: Spend ${_w2_spend:,.0f} | Leads: {_w2_leads} | CPL: ${_w2_cpl:,.0f}

BENCHMARKS SECTOR INMOBILIARIO COLOMBIA:
- CTR promedio: 0.9% - 1.5%
- CPM promedio: $5,000 - $12,000 COP
- Frecuencia ideal: < 2.5
- CPL competitivo real estate: $8,000 - $25,000 COP

Responde ESTRICTAMENTE en JSON valido con esta estructura (sin markdown, sin ```json, solo el JSON puro):
{{
  "positivo": ["item1", "item2", ...maximo 6 items],
  "vigilar": ["item1", "item2", ...maximo 6 items],
  "recomendaciones": ["item1", "item2", ...maximo 6 items]
}}

REGLAS:
1. Cada item: 1-2 oraciones con datos numericos especificos
2. "positivo": Metricas que funcionan bien vs benchmarks inmobiliarios
3. "vigilar": Senales de alerta, tendencias negativas, riesgos de Auction Overlap, fatiga, learning phase
4. "recomendaciones": Acciones concretas y especificas para optimizar Meta Ads
5. Mencionar nombres de campanas y conjuntos especificos cuando sea relevante
6. NO mencionar Google Sheets, ventas reales, ROAS de ventas ni datos externos
7. Solo metricas de Meta Ads API"""

    try:
        print("  Calling OpenAI API (gpt-4o-mini)...")
        _ai_response = call_openai(_openai_key, _system_prompt, _user_prompt)
        # Clean response - strip markdown code blocks if present
        _ai_clean = _ai_response.strip()
        if _ai_clean.startswith("```"):
            _ai_clean = _ai_clean.split("\n", 1)[1] if "\n" in _ai_clean else _ai_clean[3:]
        if _ai_clean.endswith("```"):
            _ai_clean = _ai_clean[:-3]
        _ai_clean = _ai_clean.strip()
        _ai_analysis = json.loads(_ai_clean)
        print(f"  ✅ OpenAI analysis received: {len(_ai_analysis.get('positivo',[]))} positivo, "
              f"{len(_ai_analysis.get('vigilar',[]))} vigilar, {len(_ai_analysis.get('recomendaciones',[]))} recomendaciones")
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
        print(f"  ⚠️  OpenAI API/Network error: {e}")
        print("  → Using fallback (client-side refresh available)")
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Failed to parse OpenAI response as JSON: {e}")
        print(f"     Raw response: {_ai_response[:300] if '_ai_response' in dir() else 'N/A'}")
    except Exception as e:
        print(f"  ⚠️  Unexpected error: {e}")
else:
    print("  ⚠️  No OpenAI API key found. Set OPENAI_API_KEY env var or add .openai_key.enc")

# Build analysis HTML
_now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

def _build_analysis_items(items):
    """Build HTML for analysis items list."""
    html = ""
    for item in items[:8]:
        # Highlight numbers and key phrases
        import re
        highlighted = re.sub(
            r'(\$[\d,.]+|\d+[.,]?\d*%|\d+[.,]\d+x|CPL de \$[\d,.]+|CTR del? [\d,.]+%)',
            r'<span class="analysis-highlight">\1</span>',
            item
        )
        html += f'<div class="analysis-item"><span class="analysis-bullet"></span><span>{highlighted}</span></div>\n'
    return html

if _ai_analysis:
    _pos_html = _build_analysis_items(_ai_analysis.get('positivo', []))
    _warn_html = _build_analysis_items(_ai_analysis.get('vigilar', []))
    _rec_html = _build_analysis_items(_ai_analysis.get('recomendaciones', []))
    _source_label = f"Generado por OpenAI (gpt-4o-mini) | Datos: Meta Ads API | {_now_str}"
else:
    _pos_html = '<div class="analysis-item"><span class="analysis-bullet"></span><span>No se pudo conectar con OpenAI. Ejecuta <b>python3 build_dashboard.py</b> para reintentar.</span></div>'
    _warn_html = _pos_html
    _rec_html = _pos_html
    _source_label = f"Error al generar analisis | {_now_str}"

# Serialize prompts for JS embedding
import json as _json2
_system_prompt_js = _json2.dumps(_system_prompt, ensure_ascii=False) if _openai_key else '""'
_user_prompt_js = _json2.dumps(_user_prompt, ensure_ascii=False) if _openai_key else '""'

# Read encrypted key for client-side refresh
_enc_key_b64 = ""
if os.path.exists(ENC_KEY_FILE):
    with open(ENC_KEY_FILE, "r") as f:
        _enc_key_b64 = f.read().strip()

analysis_section_html = f'''<!-- AI-POWERED ANALYSIS (OpenAI) -->
<div class="analysis-section" id="analysisSection">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
        <div class="section-title" style="margin-bottom:0"><span class="icon">&#129504;</span> Analisis IA &mdash; Insights Automaticos</div>
        <div style="display:flex;gap:8px;align-items:center;">
            <button onclick="togglePrompt()" class="filter-btn" style="font-size:11px;padding:6px 14px;opacity:0.7;" title="Ver prompt enviado a OpenAI">
                &#128065; Ver Prompt
            </button>
            <button onclick="refreshAnalysis()" id="btnRefreshAI" class="filter-btn source-btn" style="background:var(--gradient-1);color:#fff;border:none;font-size:12px;padding:8px 18px;cursor:pointer;" title="Regenerar analisis con OpenAI">
                &#9889; Actualizar Analisis
            </button>
        </div>
    </div>
    <div style="font-size:11px;color:var(--text-muted);margin:4px 0 16px 0;" id="analysisTimestamp">
        {_source_label}
    </div>
    <!-- Prompt viewer (hidden by default) -->
    <div id="promptViewer" style="display:none;margin-bottom:20px;background:var(--bg-card-alt);border:1px solid var(--border-color);border-radius:12px;padding:16px;max-height:400px;overflow-y:auto;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h4 style="color:var(--accent-cyan);margin:0;">&#128221; Prompt enviado a OpenAI</h4>
            <button onclick="togglePrompt()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;">&#10005;</button>
        </div>
        <div style="margin-bottom:12px;">
            <div style="color:var(--accent-purple);font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:4px;">System Prompt</div>
            <pre id="systemPromptText" style="white-space:pre-wrap;font-size:11px;color:var(--text-secondary);line-height:1.5;margin:0;font-family:inherit;"></pre>
        </div>
        <div>
            <div style="color:var(--accent-blue);font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:4px;">User Prompt (datos enviados)</div>
            <pre id="userPromptText" style="white-space:pre-wrap;font-size:11px;color:var(--text-secondary);line-height:1.5;margin:0;font-family:inherit;"></pre>
        </div>
    </div>
    <div class="analysis-grid" id="analysisGrid">
        <div class="analysis-card positive">
            <div class="analysis-card-header"><span class="analysis-icon">&#9989;</span><h3>Lo Positivo</h3></div>
            {_pos_html}
        </div>
        <div class="analysis-card warning">
            <div class="analysis-card-header"><span class="analysis-icon">&#9888;&#65039;</span><h3>A Vigilar</h3></div>
            {_warn_html}
        </div>
        <div class="analysis-card recommend">
            <div class="analysis-card-header"><span class="analysis-icon">&#128161;</span><h3>Recomendaciones</h3></div>
            {_rec_html}
        </div>
    </div>
</div>'''
print("AI Analysis section generated.")

# Pre-compute JSON for campaign/adset/daily data embedding in JS
_campaigns_js = json.dumps([{
    'name': c['name'], 'id': c['id'], 'spend': c['spend'], 'leads': c['leads'],
    'cpl': round(c['cpl']), 'ctr': round(c['ctr'], 2), 'cpm': round(c['cpm']),
    'reach': c['reach'], 'impressions': c['impressions'],
    'clicks': c['clicks'], 'link_clicks': c['link_clicks'],
    'frequency': round(c.get('frequency', 0), 2),
    'video_views': c['video_views'], 'engagement': c['post_engagement'],
    'messaging': c['messaging'], 'is_active': c.get('is_active', False),
    'objective': c['objective']
} for c in campaigns], ensure_ascii=False)

_adsets_js = json.dumps([{
    'campaign_name': a['campaign_name'], 'name': a['name'],
    'spend': a['spend'], 'leads': a['leads'], 'cpl': round(a['cpl']),
    'ctr': round(a['ctr'], 2), 'reach': a['reach'],
    'impressions': a['impressions'],
    'clicks': a['clicks'], 'link_clicks': a['link_clicks'],
    'video_views': a['video_views'],
    'frequency': round(a.get('frequency', 0), 2),
    'is_active': a.get('is_active', False)
} for a in adsets], ensure_ascii=False)

_daily_raw_js = json.dumps([
    [
        r['date_start'], r['campaign_name'],
        round(float(r.get('spend', 0))),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'lead')),
        int(r.get('impressions', 0)), int(r.get('clicks', 0)),
        int(r.get('reach', 0)), round(float(r.get('ctr', 0)), 2),
        round(float(r.get('cpm', 0))),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'link_click')),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'video_view'))
    ]
    for r in sorted(daily_raw['data'], key=lambda x: x['date_start'])
])

# Per-adset daily data (compact: [date, campaign_name, adset_name, spend, leads, impressions, clicks, reach, link_clicks, video_views])
_daily_adset_raw_js = json.dumps([
    [
        r['date_start'], r.get('campaign_name', ''), r.get('adset_name', ''),
        round(float(r.get('spend', 0))),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'lead')),
        int(r.get('impressions', 0)), int(r.get('clicks', 0)),
        int(r.get('reach', 0)),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'link_click')),
        int(sum(int(a['value']) for a in r.get('actions', []) if a['action_type'] == 'video_view'))
    ]
    for r in sorted(daily_adset_raw['data'], key=lambda x: x['date_start'])
])

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Los Lagos Condominio - Dashboard Meta Ads</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
/* ── RESET & BASE ─────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
    --bg-dark: #0f0f1a;
    --bg-card: #16213e;
    --bg-card-alt: #1a1a2e;
    --bg-table-header: #0e1628;
    --bg-table-row-hover: #1e2d4f;
    --accent-blue: #4361ee;
    --accent-purple: #7b2ff7;
    --accent-cyan: #00d4aa;
    --accent-pink: #ff6b9d;
    --accent-orange: #ff9f43;
    --accent-red: #ff6b6b;
    --text-primary: #e8e8f0;
    --text-secondary: #8892b0;
    --text-muted: #5a6380;
    --border-color: #2a2a4a;
    --gradient-1: linear-gradient(135deg, #4361ee 0%, #7b2ff7 100%);
    --gradient-2: linear-gradient(135deg, #00d4aa 0%, #4361ee 100%);
    --gradient-3: linear-gradient(135deg, #ff6b9d 0%, #ff9f43 100%);
    --gradient-4: linear-gradient(135deg, #7b2ff7 0%, #ff6b9d 100%);
    --shadow: 0 4px 24px rgba(0,0,0,0.3);
    --shadow-lg: 0 8px 40px rgba(0,0,0,0.4);
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--bg-dark);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}}

/* ── ANIMATIONS ───────────────────────────────────────── */
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(30px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
}}
@keyframes slideInLeft {{
    from {{ opacity: 0; transform: translateX(-30px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}
@keyframes pulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.05); }}
}}
@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}

.animate-in {{
    animation: fadeInUp 0.6s ease forwards;
    opacity: 0;
}}
.animate-in:nth-child(1) {{ animation-delay: 0.05s; }}
.animate-in:nth-child(2) {{ animation-delay: 0.1s; }}
.animate-in:nth-child(3) {{ animation-delay: 0.15s; }}
.animate-in:nth-child(4) {{ animation-delay: 0.2s; }}
.animate-in:nth-child(5) {{ animation-delay: 0.25s; }}
.animate-in:nth-child(6) {{ animation-delay: 0.3s; }}
.animate-in:nth-child(7) {{ animation-delay: 0.35s; }}
.animate-in:nth-child(8) {{ animation-delay: 0.4s; }}

/* ── LAYOUT ───────────────────────────────────────────── */
.container {{
    max-width: 1600px;
    margin: 0 auto;
    padding: 20px 24px 60px;
}}

/* ── HEADER ───────────────────────────────────────────── */
.header {{
    background: linear-gradient(135deg, #16213e 0%, #1a1a2e 50%, #0f0f1a 100%);
    border-bottom: 1px solid var(--border-color);
    padding: 28px 0;
    margin-bottom: 32px;
    animation: fadeIn 0.8s ease;
    position: relative;
    overflow: hidden;
}}
.header::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--gradient-1);
}}
.header-content {{
    max-width: 1600px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
}}
.header-left h1 {{
    font-size: 28px;
    font-weight: 700;
    background: var(--gradient-1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}}
.header-left .subtitle {{
    color: var(--text-secondary);
    font-size: 14px;
    margin-top: 4px;
}}
.header-right {{
    text-align: right;
}}
.header-right .date-range {{
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 600;
}}
.header-right .updated {{
    color: var(--text-muted);
    font-size: 12px;
    margin-top: 2px;
}}
.btn-refresh-data {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    padding: 8px 20px;
    background: var(--gradient-2);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 2px 12px rgba(0,212,170,0.25);
}}
.btn-refresh-data:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(0,212,170,0.4);
}}
.btn-refresh-data:disabled {{
    opacity: 0.6;
    cursor: wait;
    transform: none;
}}
.btn-refresh-data .spinner {{
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.refresh-log {{
    margin-top: 12px;
    padding: 12px 16px;
    background: rgba(0,0,0,0.4);
    border-radius: 8px;
    font-family: monospace;
    font-size: 11px;
    color: var(--text-secondary);
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    display: none;
    border: 1px solid var(--border-color);
}}
.account-id {{
    display: inline-block;
    background: rgba(67, 97, 238, 0.15);
    color: var(--accent-blue);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-family: monospace;
    margin-top: 6px;
}}

/* ── KPI CARDS ────────────────────────────────────────── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}}
.kpi-card {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 24px 20px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid var(--border-color);
}}
.kpi-card:hover {{
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}}
.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}}
.kpi-card:nth-child(1)::before {{ background: var(--gradient-1); }}
.kpi-card:nth-child(2)::before {{ background: var(--gradient-2); }}
.kpi-card:nth-child(3)::before {{ background: var(--gradient-3); }}
.kpi-card:nth-child(4)::before {{ background: linear-gradient(135deg, #4361ee, #00d4aa); }}
.kpi-card:nth-child(5)::before {{ background: linear-gradient(135deg, #ff9f43, #ff6b9d); }}
.kpi-card:nth-child(6)::before {{ background: var(--gradient-4); }}
.kpi-card:nth-child(7)::before {{ background: linear-gradient(135deg, #00d4aa, #7b2ff7); }}
.kpi-card:nth-child(8)::before {{ background: linear-gradient(135deg, #ff6b6b, #ff9f43); }}
.kpi-icon {{
    font-size: 28px;
    margin-bottom: 8px;
    display: block;
}}
.kpi-label {{
    color: var(--text-secondary);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}}
.kpi-value {{
    font-size: clamp(20px, 3.5vw, 26px);
    font-weight: 800;
    margin-top: 6px;
    color: var(--text-primary);
    letter-spacing: -0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.kpi-sub {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
}}

/* ── SECTION ──────────────────────────────────────────── */
.section {{
    margin-bottom: 36px;
    animation: fadeInUp 0.6s ease forwards;
}}
.section-title {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 18px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
}}
.section-title .icon {{
    font-size: 22px;
}}

/* ── CHART CONTAINERS ─────────────────────────────────── */
.chart-container {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}}
.chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
}}
.chart-grid-3 {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
}}
.chart-full {{
    margin-bottom: 32px;
}}

/* ── TABLES ───────────────────────────────────────────── */
.table-wrapper {{
    background: var(--bg-card);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
    margin-bottom: 32px;
}}
.table-scroll {{
    overflow-x: auto;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
thead th {{
    background: var(--bg-table-header);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 11px;
    padding: 14px 16px;
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    border-bottom: 2px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 1;
    transition: background 0.2s;
}}
thead th:hover {{
    background: #141d35;
    color: var(--accent-blue);
}}
thead th .sort-icon {{
    margin-left: 4px;
    opacity: 0.4;
    font-size: 10px;
}}
thead th.sorted .sort-icon {{
    opacity: 1;
    color: var(--accent-blue);
}}
tbody td {{
    padding: 12px 16px;
    border-bottom: 1px solid rgba(42, 42, 74, 0.4);
    white-space: nowrap;
}}
tbody tr {{
    transition: background 0.2s ease;
}}
tbody tr:hover {{
    background: var(--bg-table-row-hover);
}}
.num {{
    text-align: right;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 12px;
}}
.campaign-name {{
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 500;
}}
.adset-name {{
    max-width: 200px;
    font-weight: 500;
    color: var(--accent-cyan);
}}

/* CPL color coding */
.cpl-low {{
    color: var(--accent-cyan) !important;
    font-weight: 700;
}}
.cpl-mid {{
    color: var(--accent-orange) !important;
    font-weight: 700;
}}
.cpl-high {{
    color: var(--accent-red) !important;
    font-weight: 700;
}}

/* ── BADGES ───────────────────────────────────────────── */
.badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    vertical-align: middle;
    margin-left: 6px;
}}
.badge-leads {{
    background: rgba(0, 212, 170, 0.15);
    color: var(--accent-cyan);
}}
.badge-traffic {{
    background: rgba(67, 97, 238, 0.15);
    color: var(--accent-blue);
}}
.badge-awareness {{
    background: rgba(123, 47, 247, 0.15);
    color: var(--accent-purple);
}}
.badge-other {{
    background: rgba(255, 159, 67, 0.15);
    color: var(--accent-orange);
}}

/* ── PERFORMER CARDS ──────────────────────────────────── */
.performers-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 32px;
}}
.performers-section {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}}
.performers-section h3 {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.performer-card {{
    background: var(--bg-card-alt);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    transition: transform 0.2s ease;
}}
.performer-card:hover {{
    transform: translateX(4px);
}}
.performer-rank {{
    font-size: 14px;
    font-weight: 800;
    margin-bottom: 4px;
}}
.performer-name {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 10px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.performer-stats {{
    display: flex;
    gap: 20px;
}}
.performer-stat {{
    display: flex;
    flex-direction: column;
}}
.stat-label {{
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.stat-value {{
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    font-family: 'SF Mono', monospace;
}}

/* ── RESPONSIVE ───────────────────────────────────────── */
@media (max-width: 1200px) {{
    .chart-grid-3 {{ grid-template-columns: 1fr 1fr; }}
}}
@media (max-width: 900px) {{
    .chart-grid, .performers-grid {{ grid-template-columns: 1fr; }}
    .chart-grid-3 {{ grid-template-columns: 1fr; }}
    .kpi-grid {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
    .header-content {{ flex-direction: column; text-align: center; }}
    .header-right {{ text-align: center; }}
}}
@media (max-width: 600px) {{
    .kpi-value {{ font-size: 20px; }}
    .container {{ padding: 12px; }}
}}

/* ── ANALYSIS SECTION ──────────────────────────────────── */
.analysis-section {{
    margin-bottom: 36px;
    animation: fadeInUp 0.6s ease forwards;
}}
.analysis-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
}}
.analysis-card {{
    background: var(--bg-card);
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
    position: relative;
    overflow: hidden;
}}
.analysis-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}}
.analysis-card.positive::before {{ background: linear-gradient(90deg, #00d4aa, #4361ee); }}
.analysis-card.warning::before {{ background: linear-gradient(90deg, #ff9f43, #ff6b9d); }}
.analysis-card.recommend::before {{ background: linear-gradient(90deg, #4361ee, #7b2ff7); }}
.analysis-card-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
}}
.analysis-card-header .analysis-icon {{
    font-size: 24px;
}}
.analysis-card-header h3 {{
    font-size: 16px;
    font-weight: 700;
}}
.analysis-card.positive h3 {{ color: var(--accent-cyan); }}
.analysis-card.warning h3 {{ color: var(--accent-orange); }}
.analysis-card.recommend h3 {{ color: var(--accent-blue); }}
.analysis-item {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-secondary);
}}
.analysis-item:last-child {{ margin-bottom: 0; }}
.analysis-bullet {{
    flex-shrink: 0;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-top: 7px;
}}
.analysis-card.positive .analysis-bullet {{ background: var(--accent-cyan); }}
.analysis-card.warning .analysis-bullet {{ background: var(--accent-orange); }}
.analysis-card.recommend .analysis-bullet {{ background: var(--accent-blue); }}
.analysis-highlight {{
    color: var(--text-primary);
    font-weight: 600;
}}
@media (max-width: 1000px) {{
    .analysis-grid {{ grid-template-columns: 1fr; }}
}}

/* ── FILTER BAR ───────────────────────────────────────── */
.filter-bar {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 16px 24px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    box-shadow: var(--shadow);
}}
.filter-bar .filter-label {{
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}}
.filter-group {{
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}}
.filter-btn {{
    background: var(--bg-card-alt);
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s ease;
    white-space: nowrap;
    font-family: inherit;
}}
.filter-btn:hover {{
    background: rgba(67, 97, 238, 0.15);
    border-color: var(--accent-blue);
    color: var(--text-primary);
}}
.filter-btn.active {{
    background: var(--accent-blue);
    border-color: var(--accent-blue);
    color: #fff;
    font-weight: 600;
    box-shadow: 0 2px 12px rgba(67, 97, 238, 0.4);
}}
.filter-separator {{
    width: 1px;
    height: 28px;
    background: var(--border-color);
    margin: 0 4px;
}}
.filter-bar .date-display {{
    margin-left: auto;
    color: var(--accent-cyan);
    font-size: 13px;
    font-weight: 600;
    font-family: 'SF Mono', monospace;
}}
@media (max-width: 900px) {{
    .filter-bar {{ padding: 12px 16px; gap: 10px; }}
    .filter-bar .date-display {{ margin-left: 0; width: 100%; text-align: center; }}
}}

/* ── SOURCE TOGGLE + DATE PICKER ──────────────────────── */
.filter-btn.source-btn.active {{
    box-shadow: 0 2px 12px rgba(67, 97, 238, 0.4);
}}
.filter-btn.source-btn[data-source="meta"].active {{
    background: #4361ee; border-color: #4361ee; color: #fff;
}}
.filter-btn.source-btn[data-source="sheet"].active {{
    background: #00d4aa; border-color: #00d4aa; color: #fff;
}}
.filter-btn.source-btn[data-source="ambos"].active {{
    background: linear-gradient(135deg, #4361ee, #00d4aa); border-color: #4361ee; color: #fff;
}}
.date-range-picker {{
    display: flex; align-items: center; gap: 8px;
}}
.date-range-picker input[type="date"] {{
    background: var(--bg-card-alt);
    color: var(--text-primary);
    color-scheme: dark;
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.25s ease;
    min-width: 150px;
    position: relative;
}}
.date-range-picker input[type="date"]:hover {{
    border-color: var(--accent-blue);
    background: rgba(67, 97, 238, 0.1);
}}
.date-range-picker input[type="date"]:focus {{
    border-color: var(--accent-blue);
    outline: none;
    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.2);
}}
.date-range-picker input[type="date"]::-webkit-calendar-picker-indicator {{
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    background: transparent;
}}
.date-range-picker label {{
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}}
.date-range-picker .date-sep {{
    color: var(--text-muted); font-size: 16px;
}}
.section-source-meta, .section-source-sheet, .section-source-ventas {{
    transition: opacity 0.3s ease, max-height 0.4s ease;
}}
.section-hidden {{
    display: none !important;
}}

/* ── MULTICANAL SECTION ───────────────────────────────── */
.multicanal-header {{
    display: flex; align-items: center; gap: 12px;
    padding: 20px 24px;
    background: linear-gradient(135deg, rgba(67,97,238,0.08), rgba(0,212,170,0.08));
    border: 1px solid rgba(67,97,238,0.2);
    border-radius: 16px;
    margin-bottom: 20px;
}}
.multicanal-header .icon {{ font-size: 28px; }}
.multicanal-header h2 {{
    margin: 0; font-size: 20px; font-weight: 700;
    background: linear-gradient(135deg, #4361ee, #00d4aa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.multicanal-header .sub {{ color: var(--text-secondary); font-size: 13px; margin-top: 2px; }}

/* ── FOOTER ───────────────────────────────────────────── */
.footer {{
    text-align: center;
    padding: 30px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border-color);
    margin-top: 40px;
}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
    <div class="header-content">
        <div class="header-left">
            <h1>Los Lagos Condominio</h1>
            <div class="subtitle">Dashboard Multicanal &mdash; Meta Ads &bull; TikTok &bull; Google Ads</div>
            <div class="account-id">act_1089998585939349</div>
        </div>
        <div class="header-right">
            <div class="date-range">{date_start_str} &mdash; {date_end_str}</div>
            <div class="updated" id="lastUpdated">Ultima actualizacion: {now_str}</div>
            <button id="btnRefreshData" class="btn-refresh-data" onclick="refreshData()" title="Descargar datos frescos de Meta Ads y Google Sheets, luego reconstruir el dashboard">
                &#128259; Refrescar Datos
            </button>
        </div>
    </div>
</div>

<div class="container">

<!-- FILTER BAR -->
<div class="filter-bar">
    <span class="filter-label">&#128640; Fuente:</span>
    <div class="filter-group">
        <button class="filter-btn source-btn active" data-source="ambos" onclick="filterSource('ambos')">&#127760; Ambos</button>
        <button class="filter-btn source-btn" data-source="meta" onclick="filterSource('meta')">&#128312; Meta Ads</button>
        <button class="filter-btn source-btn" data-source="sheet" onclick="filterSource('sheet')">&#128202; Google Sheet</button>
    </div>
    <div class="filter-separator"></div>
    <span class="filter-label">&#128197; Rango Ads:</span>
    <div class="date-range-picker">
        <label>Desde</label>
        <input type="date" id="dateFrom" value="{daily_dates[0] if daily_dates else ''}" min="{daily_dates[0] if daily_dates else ''}" max="{daily_dates[-1] if daily_dates else ''}" title="Fecha inicio">
        <span class="date-sep">&rarr;</span>
        <label>Hasta</label>
        <input type="date" id="dateTo" value="{daily_dates[-1] if daily_dates else ''}" min="{daily_dates[0] if daily_dates else ''}" max="{daily_dates[-1] if daily_dates else ''}" title="Fecha fin">
    </div>
    <div class="filter-separator"></div>
    <span class="filter-label">&#127968; Ventas:</span>
    <div class="filter-group">
        {''.join(f'<button class="filter-btn filter-ventas{" active" if m == "ALL" else ""}" data-mes="{m}" onclick="filterVentas(\'{m}\')">{label}</button>' for m, label in filter_buttons_ventas)}
    </div>
    <span class="date-display" id="dateRangeDisplay">{date_start_str} &mdash; {date_end_str}</span>
</div>

<!-- KPI CARDS (Meta Ads) -->
<div class="section-source-meta">
<div class="kpi-grid">
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#128176;</span>
        <div class="kpi-label">Inversion Total</div>
        <div class="kpi-value" id="kpi-spend">{fmt_cop(total_spend)}</div>
        <div class="kpi-sub" id="kpi-spend-sub">COP ({total_data_days} dias)</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#128203;</span>
        <div class="kpi-label">Leads Totales</div>
        <div class="kpi-value" id="kpi-leads">{fmt_num(total_leads)}</div>
        <div class="kpi-sub">Formularios enviados</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#128178;</span>
        <div class="kpi-label">Costo por Lead</div>
        <div class="kpi-value" id="kpi-cpl">{fmt_cop(avg_cpl)}</div>
        <div class="kpi-sub">COP promedio</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#128065;</span>
        <div class="kpi-label">Impresiones</div>
        <div class="kpi-value" id="kpi-impressions">{fmt_num(total_impressions)}</div>
        <div class="kpi-sub" id="kpi-cpm-sub">CPM: {fmt_cop(avg_cpm)}</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#128073;</span>
        <div class="kpi-label">CTR (Total)</div>
        <div class="kpi-value" id="kpi-ctr">{avg_ctr:.2f}%</div>
        <div class="kpi-sub" id="kpi-clicks-sub">{fmt_num(total_clicks)} clics totales</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#127758;</span>
        <div class="kpi-label">Alcance</div>
        <div class="kpi-value" id="kpi-reach">{fmt_num(total_reach)}</div>
        <div class="kpi-sub">Cuentas unicas</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#127910;</span>
        <div class="kpi-label">Reproducciones Video</div>
        <div class="kpi-value">{fmt_num(total_video_views)}</div>
        <div class="kpi-sub">Vistas totales</div>
    </div>
    <div class="kpi-card animate-in">
        <span class="kpi-icon">&#10084;</span>
        <div class="kpi-label">Engagement</div>
        <div class="kpi-value">{total_engagement:,}</div>
        <div class="kpi-sub">{total_messaging:,} conexiones msg</div>
    </div>
</div>

{analysis_section_html}

</div><!-- /section-source-meta (KPI + analysis) -->

<!-- ══════════════════════════════════════════════════════ -->
<!-- VENTAS REALES & ROAS SECTION (cruce Meta + Sheet)     -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="section-source-ventas">

<!-- VENTAS KPI CARDS -->
<div class="section">
    <div class="section-title"><span class="icon">&#128176;</span> Ventas Reales &mdash; Cierre de Campanas (Google Sheet)</div>
    <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        <div class="kpi-card animate-in" style="border: 1px solid rgba(0,212,170,0.3);">
            <span class="kpi-icon">&#127942;</span>
            <div class="kpi-label">ROAS META</div>
            <div class="kpi-value" id="kpi-roas" style="color: {'var(--accent-cyan)' if roas >= 3 else 'var(--accent-orange)' if roas >= 1 else 'var(--accent-red)'};">{roas:.1f}x</div>
            <div class="kpi-sub">Revenue / Inversion Ads</div>
        </div>
        <div class="kpi-card animate-in">
            <span class="kpi-icon">&#128181;</span>
            <div class="kpi-label">Revenue META</div>
            <div class="kpi-value" id="kpi-meta-revenue">{fmt_cop(meta_ventas_revenue)}</div>
            <div class="kpi-sub" id="kpi-meta-revenue-sub">{meta_ventas_count} lotes vendidos via Meta</div>
        </div>
        <div class="kpi-card animate-in">
            <span class="kpi-icon">&#128200;</span>
            <div class="kpi-label">Revenue Total</div>
            <div class="kpi-value" id="kpi-total-revenue">{fmt_cop(ventas_total_revenue)}</div>
            <div class="kpi-sub" id="kpi-total-revenue-sub">{ventas_total_count} ventas todas las fuentes</div>
        </div>
        <div class="kpi-card animate-in">
            <span class="kpi-icon">&#127968;</span>
            <div class="kpi-label">Ticket Promedio</div>
            <div class="kpi-value" id="kpi-ticket">{fmt_cop(meta_avg_ticket)}</div>
            <div class="kpi-sub">Precio prom. lote (META)</div>
        </div>
        <div class="kpi-card animate-in">
            <span class="kpi-icon">&#9201;</span>
            <div class="kpi-label">Dias para Cierre</div>
            <div class="kpi-value" id="kpi-dias">{meta_median_dias} dias</div>
            <div class="kpi-sub" id="kpi-dias-sub">Mediana ({meta_avg_dias:.1f} promedio)</div>
        </div>
        <div class="kpi-card animate-in">
            <span class="kpi-icon">&#128178;</span>
            <div class="kpi-label">Costo por Venta</div>
            <div class="kpi-value" id="kpi-cpv">{fmt_cop(total_spend / meta_ventas_count) if meta_ventas_count else '$0'}</div>
            <div class="kpi-sub">Inversion Ads / Ventas META</div>
        </div>
    </div>
</div>

<!-- VENTAS BY SOURCE CHART + TABLE -->
<div class="chart-grid">
    <div class="section">
        <div class="section-title"><span class="icon">&#128202;</span> Ventas por Fuente</div>
        <div class="chart-container">
            <canvas id="sourceChart" height="280"></canvas>
        </div>
    </div>
    <div class="section">
        <div class="section-title"><span class="icon">&#128203;</span> Atribucion de Ventas</div>
        <div class="table-wrapper" style="margin-bottom: 0;">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Fuente</th>
                            <th>Ventas</th>
                            <th>% Ventas</th>
                            <th>Revenue</th>
                            <th>% Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        {build_ventas_source_rows()}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- CAMPAIGN ROAS TABLE -->
<div class="section">
    <div class="section-title"><span class="icon">&#128176;</span> ROAS por Campana &mdash; Cruce Spend vs Ventas Reales</div>
    <div class="table-wrapper">
        <div class="table-scroll">
            <table id="roasTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('roasTable', 0, 'str')">Campana <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 1, 'num')">Inversion <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 2, 'num')">Leads <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 3, 'num')">Ventas <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 4, 'num')">Conv. Rate <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 5, 'num')">Revenue <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 6, 'num')">ROAS <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('roasTable', 7, 'num')">Costo/Venta <span class="sort-icon">&#8645;</span></th>
                    </tr>
                </thead>
                <tbody>
                    {build_campaign_roas_rows()}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- ASESORES + CREATIVOS -->
<div class="chart-grid">
    <div class="section">
        <div class="section-title"><span class="icon">&#128100;</span> Asesores &mdash; Ventas META</div>
        <div class="table-wrapper" style="margin-bottom: 0;">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Asesor</th>
                            <th>Ventas</th>
                            <th>Revenue</th>
                            <th>Ticket Prom.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {build_asesor_rows()}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="section">
        <div class="section-title"><span class="icon">&#127912;</span> Creativos que Venden &mdash; META</div>
        <div class="table-wrapper" style="margin-bottom: 0;">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Anuncio/Creativo</th>
                            <th>Ventas</th>
                            <th>Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        {build_creative_ventas_rows()}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
</div><!-- /section-source-ventas (cruce) -->

<!-- ══════════════════════════════════════════════════════ -->
<!-- COMPARATIVO MULTICANAL (Google Sheet)                 -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="section-source-sheet">
<div class="multicanal-header">
    <span class="icon">&#128202;</span>
    <div>
        <h2>Comparativo Multicanal &mdash; Google Sheet</h2>
        <div class="sub">Meta Ads vs TikTok vs Google Ads &mdash; Datos del resumen general (Enero 2026)</div>
    </div>
</div>
{sheet_comparison_html}
</div><!-- /section-source-sheet -->

<!-- ══════════════════════════════════════════════════════ -->
<!-- META ADS PERFORMANCE (Original Sections)              -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="section-source-meta">

<!-- DAILY SPEND & LEADS CHART -->
<div class="section">
    <div class="section-title"><span class="icon">&#128200;</span> Inversion Diaria y Leads</div>
    <div class="chart-container chart-full">
        <canvas id="dailyChart" height="100"></canvas>
    </div>
</div>

<!-- OBJECTIVE DISTRIBUTION + TRENDS -->
<div class="chart-grid">
    <div class="section">
        <div class="section-title"><span class="icon">&#127919;</span> Distribucion por Objetivo</div>
        <div class="chart-container">
            <canvas id="objectiveChart" height="260"></canvas>
        </div>
    </div>
    <div class="section">
        <div class="section-title"><span class="icon">&#128202;</span> Tendencia CPL Diario</div>
        <div class="chart-container">
            <canvas id="cplTrendChart" height="260"></canvas>
        </div>
    </div>
</div>

<!-- METRIC TRENDS -->
<div class="section">
    <div class="section-title"><span class="icon">&#128208;</span> Tendencias de Metricas Clave</div>
    <div class="chart-grid">
        <div class="chart-container">
            <canvas id="ctrTrendChart" height="220"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="cpmTrendChart" height="220"></canvas>
        </div>
    </div>
</div>

<!-- TOP / BOTTOM PERFORMERS (dynamic) -->
<div class="section">
    <div class="section-title"><span class="icon">&#127942;</span> Mejores y Peores Campanas por CPL <span style="font-size:0.55em;color:var(--accent-cyan);margin-left:8px">&#9679; Solo campanas activas</span></div>
    <div class="performers-grid">
        <div class="performers-section">
            <h3><span style="color: var(--accent-cyan)">&#9650;</span> Mejor CPL (Mas Eficientes)</h3>
            <div id="topPerformersContainer">{build_performer_cards(top_performers, is_top=True)}</div>
        </div>
        <div class="performers-section">
            <h3><span style="color: var(--accent-red)">&#9660;</span> Mayor CPL (Menos Eficientes)</h3>
            <div id="bottomPerformersContainer">{build_performer_cards(bottom_performers, is_top=False)}</div>
        </div>
    </div>
</div>

<!-- CAMPAIGN PERFORMANCE TABLE -->
<div class="section">
    <div class="section-title"><span class="icon">&#128640;</span> Rendimiento por Campana</div>
    <div class="table-wrapper">
        <div class="table-scroll">
            <table id="campaignTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('campaignTable', 0, 'str')">Campana <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 1, 'num')">Inversion <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 2, 'num')">Impresiones <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 3, 'num')">Clics <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 4, 'num')">CTR <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 5, 'num')">Leads <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 6, 'num')">CPL <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 7, 'num')">Link Clicks <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('campaignTable', 8, 'num')">Video Views <span class="sort-icon">&#8645;</span></th>
                    </tr>
                </thead>
                <tbody id="campaignTableBody">
                    {build_campaign_rows()}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- AD SET PERFORMANCE TABLE -->
<div class="section">
    <div class="section-title"><span class="icon">&#128218;</span> Rendimiento por Conjunto de Anuncios</div>
    <div class="table-wrapper">
        <div class="table-scroll">
            <table id="adsetTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('adsetTable', 0, 'str')">Campana <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 1, 'str')">Conjunto <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 2, 'num')">Inversion <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 3, 'num')">Impresiones <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 4, 'num')">Clics <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 5, 'num')">CTR <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 6, 'num')">Leads <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 7, 'num')">CPL <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 8, 'num')">Link Clicks <span class="sort-icon">&#8645;</span></th>
                        <th onclick="sortTable('adsetTable', 9, 'num')">Video Views <span class="sort-icon">&#8645;</span></th>
                    </tr>
                </thead>
                <tbody id="adsetTableBody">
                    {build_adset_rows()}
                </tbody>
            </table>
        </div>
    </div>
</div>
</div><!-- /section-source-meta (performance) -->

<!-- FOOTER -->
<div class="footer">
    Los Lagos Condominio &mdash; Dashboard Meta Ads + Ventas Reales &mdash; Generado automaticamente el {now_str}<br>
    Datos de Meta Ads API &bull; Ventas: Google Sheet (Cierre Campanas) &bull; Cuenta: act_1089998585939349 &bull; COP
</div>

</div><!-- /container -->

<script>
// ── Chart.js Global Config ─────────────────────────────
Chart.defaults.color = '#8892b0';
Chart.defaults.borderColor = 'rgba(42, 42, 74, 0.5)';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

// ── VENTAS POR FUENTE CHART ────────────────────────────
const sourceLabels = {json.dumps(source_labels)};
const sourceCounts = {json.dumps(source_counts)};
const sourceRevenues = {json.dumps(source_revenues)};

new Chart(document.getElementById('sourceChart'), {{
    type: 'bar',
    data: {{
        labels: sourceLabels,
        datasets: [
            {{
                label: 'Ventas (#)',
                data: sourceCounts,
                backgroundColor: [
                    'rgba(67, 97, 238, 0.7)',
                    'rgba(0, 212, 170, 0.7)',
                    'rgba(123, 47, 247, 0.7)',
                    'rgba(255, 159, 67, 0.7)',
                    'rgba(255, 107, 157, 0.7)',
                    'rgba(255, 107, 107, 0.7)',
                    'rgba(100, 100, 150, 0.7)'
                ],
                borderColor: [
                    '#4361ee', '#00d4aa', '#7b2ff7', '#ff9f43', '#ff6b9d', '#ff6b6b', '#6464a0'
                ],
                borderWidth: 2,
                borderRadius: 6,
                yAxisID: 'y'
            }},
            {{
                label: 'Revenue (COP)',
                data: sourceRevenues,
                type: 'line',
                borderColor: '#00d4aa',
                backgroundColor: 'rgba(0, 212, 170, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: '#00d4aa',
                pointRadius: 5,
                pointHoverRadius: 8,
                tension: 0.3,
                yAxisID: 'y1'
            }}
        ]
    }},
    options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ labels: {{ usePointStyle: true, padding: 16 }} }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                borderColor: 'rgba(67, 97, 238, 0.3)',
                borderWidth: 1,
                padding: 12,
                callbacks: {{
                    label: function(ctx) {{
                        if (ctx.dataset.yAxisID === 'y1') {{
                            return 'Revenue: $' + (ctx.parsed.y / 1000000).toFixed(0) + 'M';
                        }}
                        return ctx.dataset.label + ': ' + ctx.parsed.y;
                    }}
                }}
            }}
        }},
        scales: {{
            y: {{
                position: 'left',
                title: {{ display: true, text: '# Ventas', font: {{ weight: '600' }} }},
                grid: {{ color: 'rgba(42, 42, 74, 0.3)' }}
            }},
            y1: {{
                position: 'right',
                title: {{ display: true, text: 'Revenue (COP)', font: {{ weight: '600' }} }},
                ticks: {{ callback: v => '$' + (v/1000000).toFixed(0) + 'M' }},
                grid: {{ drawOnChartArea: false }}
            }},
            x: {{ grid: {{ color: 'rgba(42, 42, 74, 0.2)' }} }}
        }}
    }}
}});

// ── FULL DATA ARRAYS (for filtering) ───────────────────
const ALL_DATES = {json.dumps(daily_iso_dates)};
const ALL_LABELS = {json.dumps(daily_labels)};
const ALL_SPEND = {json.dumps(daily_spend)};
const ALL_LEADS = {json.dumps(daily_leads)};
const ALL_CPL = {json.dumps(daily_cpl)};
const ALL_CTR = {json.dumps(daily_ctr)};
const ALL_CPM = {json.dumps(daily_cpm)};
const ALL_IMPRESSIONS = {json.dumps([daily_agg[d]['impressions'] for d in daily_dates])};
const ALL_CLICKS = {json.dumps([daily_agg[d]['clicks'] for d in daily_dates])};
const ALL_REACH = {json.dumps([daily_agg[d]['reach'] for d in daily_dates])};
const ALL_VENTAS = {json.dumps(ventas_json_list)};

// ── CAMPAIGN & ADSET DATA (for dynamic prompt) ─────────
const ALL_CAMPAIGNS = {_campaigns_js};

const ALL_ADSETS = {_adsets_js};

// Per-campaign daily data (compact: [date, campaign_name, spend, leads, impressions, clicks, reach, ctr, cpm, link_clicks, video_views])
const ALL_DAILY_RAW = {_daily_raw_js};

// Per-adset daily data (compact: [date, campaign_name, adset_name, spend, leads, impressions, clicks, reach, link_clicks, video_views])
const ALL_ADSET_DAILY_RAW = {_daily_adset_raw_js};

// Mutable working arrays
let dailyLabels = [...ALL_LABELS];
let dailySpend = [...ALL_SPEND];
let dailyLeads = [...ALL_LEADS];
let dailyCPL = [...ALL_CPL];
let dailyCTR = [...ALL_CTR];
let dailyCPM = [...ALL_CPM];

// Track current filters
let currentMes = 'ALL';

// ── DAILY SPEND & LEADS CHART ──────────────────────────
const dailyChart = new Chart(document.getElementById('dailyChart'), {{
    type: 'bar',
    data: {{
        labels: dailyLabels,
        datasets: [
            {{
                label: 'Inversion Diaria (COP)',
                data: dailySpend,
                type: 'bar',
                backgroundColor: 'rgba(67, 97, 238, 0.35)',
                borderColor: 'rgba(67, 97, 238, 0.8)',
                borderWidth: 1,
                borderRadius: 4,
                order: 2,
                yAxisID: 'y'
            }},
            {{
                label: 'Leads Diarios',
                data: dailyLeads,
                type: 'line',
                borderColor: '#00d4aa',
                backgroundColor: 'rgba(0, 212, 170, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: '#00d4aa',
                pointBorderColor: '#00d4aa',
                pointRadius: 4,
                pointHoverRadius: 7,
                tension: 0.3,
                fill: true,
                order: 1,
                yAxisID: 'y1'
            }}
        ]
    }},
    options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{
                labels: {{ usePointStyle: true, padding: 20 }}
            }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                borderColor: 'rgba(67, 97, 238, 0.3)',
                borderWidth: 1,
                padding: 12,
                titleFont: {{ weight: '600' }},
                callbacks: {{
                    label: function(ctx) {{
                        if (ctx.dataset.yAxisID === 'y') {{
                            return 'Inversion: $' + ctx.parsed.y.toLocaleString('es-CO');
                        }}
                        return 'Leads: ' + ctx.parsed.y;
                    }}
                }}
            }}
        }},
        scales: {{
            y: {{
                position: 'left',
                title: {{ display: true, text: 'Inversion (COP)', font: {{ weight: '600' }} }},
                ticks: {{
                    callback: v => '$' + (v/1000).toFixed(0) + 'K'
                }},
                grid: {{ color: 'rgba(42, 42, 74, 0.3)' }}
            }},
            y1: {{
                position: 'right',
                title: {{ display: true, text: 'Leads', font: {{ weight: '600' }} }},
                grid: {{ drawOnChartArea: false }}
            }},
            x: {{
                grid: {{ color: 'rgba(42, 42, 74, 0.2)' }}
            }}
        }}
    }}
}});

// ── OBJECTIVE DONUT CHART ──────────────────────────────
new Chart(document.getElementById('objectiveChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(obj_labels_es)},
        datasets: [{{
            data: {json.dumps(obj_values)},
            backgroundColor: [
                'rgba(0, 212, 170, 0.8)',
                'rgba(67, 97, 238, 0.8)',
                'rgba(123, 47, 247, 0.8)',
                'rgba(255, 159, 67, 0.8)'
            ],
            borderColor: [
                '#00d4aa',
                '#4361ee',
                '#7b2ff7',
                '#ff9f43'
            ],
            borderWidth: 2,
            hoverOffset: 12
        }}]
    }},
    options: {{
        responsive: true,
        cutout: '65%',
        plugins: {{
            legend: {{
                position: 'bottom',
                labels: {{ usePointStyle: true, padding: 16, font: {{ size: 12 }} }}
            }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                borderColor: 'rgba(67, 97, 238, 0.3)',
                borderWidth: 1,
                padding: 12,
                callbacks: {{
                    label: function(ctx) {{
                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                        const pct = ((ctx.parsed / total) * 100).toFixed(1);
                        return ctx.label + ': $' + ctx.parsed.toLocaleString('es-CO') + ' (' + pct + '%)';
                    }}
                }}
            }}
        }}
    }}
}});

// ── CPL TREND CHART ────────────────────────────────────
const cplChart = new Chart(document.getElementById('cplTrendChart'), {{
    type: 'line',
    data: {{
        labels: dailyLabels,
        datasets: [{{
            label: 'CPL Diario (COP)',
            data: dailyCPL,
            borderColor: '#ff6b9d',
            backgroundColor: 'rgba(255, 107, 157, 0.1)',
            borderWidth: 2.5,
            pointBackgroundColor: '#ff6b9d',
            pointRadius: 3,
            pointHoverRadius: 6,
            tension: 0.3,
            fill: true
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ labels: {{ usePointStyle: true }} }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                callbacks: {{
                    label: ctx => 'CPL: $' + ctx.parsed.y.toLocaleString('es-CO')
                }}
            }}
        }},
        scales: {{
            y: {{
                title: {{ display: true, text: 'CPL (COP)' }},
                ticks: {{ callback: v => '$' + v.toLocaleString('es-CO') }},
                grid: {{ color: 'rgba(42, 42, 74, 0.3)' }}
            }},
            x: {{ grid: {{ color: 'rgba(42, 42, 74, 0.2)' }} }}
        }}
    }}
}});

// ── CTR TREND CHART ────────────────────────────────────
const ctrChart = new Chart(document.getElementById('ctrTrendChart'), {{
    type: 'line',
    data: {{
        labels: dailyLabels,
        datasets: [{{
            label: 'CTR Diario (%)',
            data: dailyCTR,
            borderColor: '#4361ee',
            backgroundColor: 'rgba(67, 97, 238, 0.1)',
            borderWidth: 2.5,
            pointBackgroundColor: '#4361ee',
            pointRadius: 3,
            pointHoverRadius: 6,
            tension: 0.3,
            fill: true
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ labels: {{ usePointStyle: true }} }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                callbacks: {{ label: ctx => 'CTR: ' + ctx.parsed.y.toFixed(2) + '%' }}
            }}
        }},
        scales: {{
            y: {{
                title: {{ display: true, text: 'CTR (%)' }},
                ticks: {{ callback: v => v.toFixed(1) + '%' }},
                grid: {{ color: 'rgba(42, 42, 74, 0.3)' }}
            }},
            x: {{ grid: {{ color: 'rgba(42, 42, 74, 0.2)' }} }}
        }}
    }}
}});

// ── CPM TREND CHART ────────────────────────────────────
const cpmChart = new Chart(document.getElementById('cpmTrendChart'), {{
    type: 'line',
    data: {{
        labels: dailyLabels,
        datasets: [{{
            label: 'CPM Diario (COP)',
            data: dailyCPM,
            borderColor: '#ff9f43',
            backgroundColor: 'rgba(255, 159, 67, 0.1)',
            borderWidth: 2.5,
            pointBackgroundColor: '#ff9f43',
            pointRadius: 3,
            pointHoverRadius: 6,
            tension: 0.3,
            fill: true
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ labels: {{ usePointStyle: true }} }},
            tooltip: {{
                backgroundColor: 'rgba(15, 15, 26, 0.95)',
                callbacks: {{ label: ctx => 'CPM: $' + ctx.parsed.y.toLocaleString('es-CO') }}
            }}
        }},
        scales: {{
            y: {{
                title: {{ display: true, text: 'CPM (COP)' }},
                ticks: {{ callback: v => '$' + v.toLocaleString('es-CO') }},
                grid: {{ color: 'rgba(42, 42, 74, 0.3)' }}
            }},
            x: {{ grid: {{ color: 'rgba(42, 42, 74, 0.2)' }} }}
        }}
    }}
}});

// ── TABLE SORTING ──────────────────────────────────────
function sortTable(tableId, colIdx, type) {{
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const ths = table.querySelectorAll('thead th');

    // Toggle direction
    const th = ths[colIdx];
    const currentDir = th.dataset.sortDir || 'desc';
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';

    // Reset all
    ths.forEach(h => {{ h.classList.remove('sorted'); h.dataset.sortDir = ''; }});
    th.classList.add('sorted');
    th.dataset.sortDir = newDir;

    rows.sort((a, b) => {{
        let aVal = a.cells[colIdx].textContent.trim();
        let bVal = b.cells[colIdx].textContent.trim();

        if (type === 'num') {{
            // Parse numeric: remove $, dots, commas, %, -
            aVal = aVal.replace(/[$%.]/g, '').replace(/,/g, '').replace('-', '0');
            bVal = bVal.replace(/[$%.]/g, '').replace(/,/g, '').replace('-', '0');
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }} else {{
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }}

        if (aVal < bVal) return newDir === 'asc' ? -1 : 1;
        if (aVal > bVal) return newDir === 'asc' ? 1 : -1;
        return 0;
    }});

    rows.forEach(row => tbody.appendChild(row));
}}

// ── Animate elements on scroll ─────────────────────────
const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
        if (entry.isIntersecting) {{
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }}
    }});
}}, {{ threshold: 0.1 }});

document.querySelectorAll('.section').forEach(el => {{
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
}});

// ══════════════════════════════════════════════════════════
// FILTER LOGIC
// ══════════════════════════════════════════════════════════

const MESES_ES = {{'01':'Ene','02':'Feb','03':'Mar','04':'Abr','05':'May','06':'Jun',
                   '07':'Jul','08':'Ago','09':'Sep','10':'Oct','11':'Nov','12':'Dic'}};

function fmtCOP(val) {{
    if (val >= 1e9) return '$' + (val/1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val/1e6).toFixed(1) + 'M';
    if (val >= 1e3) return '$' + Math.round(val).toLocaleString('es-CO');
    return '$' + Math.round(val);
}}
function fmtCOPFull(val) {{
    if (val >= 1e9) return '$' + (val/1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val/1e6).toFixed(1) + 'M';
    return '$' + Math.round(val).toLocaleString('es-CO');
}}
function fmtNum(val) {{
    if (val >= 1e6) return (val/1e6).toFixed(1) + 'M';
    if (val >= 1e3) return (val/1e3).toFixed(1) + 'K';
    return Math.round(val).toLocaleString('es-CO');
}}
function fmtDateES(iso) {{
    const p = iso.split('-');
    return parseInt(p[2]) + ' ' + MESES_ES[p[1]] + ' ' + p[0];
}}

function updatePerformers(fromDate, toDate) {{
    // Aggregate daily data by campaign in the selected date range
    const campMap = {{}};
    ALL_DAILY_RAW.forEach(r => {{
        const [date, campName, spend, leads] = r;
        if (date < fromDate || date > toDate) return;
        if (!campMap[campName]) campMap[campName] = {{name: campName, spend: 0, leads: 0}};
        campMap[campName].spend += spend;
        campMap[campName].leads += leads;
    }});

    // Get active campaign names (those with spend in last 3 days of range)
    const allDatesInRange = [...new Set(ALL_DAILY_RAW.filter(r => r[0] >= fromDate && r[0] <= toDate).map(r => r[0]))].sort();
    const last3 = new Set(allDatesInRange.slice(-3));
    const recentSpend = {{}};
    ALL_DAILY_RAW.forEach(r => {{
        if (last3.has(r[0])) {{
            recentSpend[r[1]] = (recentSpend[r[1]] || 0) + r[2];
        }}
    }});

    // Filter: only active campaigns with leads > 0
    const withLeads = Object.values(campMap).filter(c => c.leads > 0 && (recentSpend[c.name] || 0) > 0);
    withLeads.forEach(c => {{ c.cpl = c.spend / c.leads; }});
    withLeads.sort((a, b) => a.cpl - b.cpl);

    const top3 = withLeads.slice(0, 3);
    const bottom3 = withLeads.slice(-3).reverse();

    function buildCards(list, isTop) {{
        if (list.length === 0) return '<div style="color:#8892b0;padding:20px;text-align:center">Sin datos en este rango</div>';
        const icon = isTop ? '&#9650;' : '&#9660;';
        const color = isTop ? '#00d4aa' : '#ff6b6b';
        return list.map((c, i) => {{
            const cplDisp = fmtCOPFull(c.cpl);
            const spendDisp = fmtCOPFull(c.spend);
            return `<div class="performer-card" style="border-left:4px solid ${{color}}">`
                + `<div class="performer-rank" style="color:${{color}}">${{icon}} #${{i+1}}</div>`
                + `<div class="performer-name">${{c.name}}</div>`
                + `<div class="performer-stats">`
                + `<div class="performer-stat"><span class="stat-label">CPL</span><span class="stat-value" style="color:${{color}}">${{cplDisp}}</span></div>`
                + `<div class="performer-stat"><span class="stat-label">Leads</span><span class="stat-value">${{c.leads}}</span></div>`
                + `<div class="performer-stat"><span class="stat-label">Inversion</span><span class="stat-value">${{spendDisp}}</span></div>`
                + `</div></div>`;
        }}).join('');
    }}

    document.getElementById('topPerformersContainer').innerHTML = buildCards(top3, true);
    document.getElementById('bottomPerformersContainer').innerHTML = buildCards(bottom3, false);
}}

function _fmtCOPTable(val) {{
    return '$' + Math.round(val).toLocaleString('es-CO');
}}

function _objBadge(name) {{
    const u = name.toUpperCase();
    if (u.includes('TRAF')) return '<span class="badge badge-traffic">Trafico</span>';
    if (u.includes('RECON') || u.includes('MENSAJES')) return '<span class="badge badge-awareness">Awareness</span>';
    if (u.includes('FORM') || u.includes('LEAD')) return '<span class="badge badge-leads">Leads</span>';
    return '<span class="badge badge-other">Otro</span>';
}}

function _statusBadge(isOn) {{
    return isOn
        ? '<span class="badge badge-leads" style="margin-left:6px">ON</span>'
        : '<span class="badge" style="background:rgba(255,75,75,0.15);color:#ff4b4b;margin-left:6px;font-weight:700">OFF</span>';
}}

function _cplClass(cpl, minCpl, maxCpl) {{
    if (cpl <= 0) return '';
    const ratio = maxCpl !== minCpl ? (cpl - minCpl) / (maxCpl - minCpl) : 0.5;
    if (ratio < 0.33) return 'cpl-low';
    if (ratio < 0.66) return 'cpl-mid';
    return 'cpl-high';
}}

function updateCampaignTable(fromDate, toDate) {{
    // Aggregate daily data by campaign in range (ALL_DAILY_RAW: [date, name, spend, leads, impr, clicks, reach, ctr, cpm, link_clicks, video_views])
    const campMap = {{}};
    ALL_DAILY_RAW.forEach(r => {{
        const [date, name, spend, leads, impr, clicks, reach, ctr, cpm, link_clicks, video_views] = r;
        if (date < fromDate || date > toDate) return;
        if (!campMap[name]) campMap[name] = {{name, spend:0, leads:0, impressions:0, clicks:0, reach:0, link_clicks:0, video_views:0}};
        const c = campMap[name];
        c.spend += spend; c.leads += leads; c.impressions += impr;
        c.clicks += clicks; c.reach += reach;
        c.link_clicks += (link_clicks || 0);
        c.video_views += (video_views || 0);
    }});

    // Get active status (spend in last 3 days of range)
    const datesInRange = [...new Set(ALL_DAILY_RAW.filter(r => r[0] >= fromDate && r[0] <= toDate).map(r => r[0]))].sort();
    const last3Set = new Set(datesInRange.slice(-3));
    const recentSpend = {{}};
    ALL_DAILY_RAW.forEach(r => {{
        if (last3Set.has(r[0])) recentSpend[r[1]] = (recentSpend[r[1]] || 0) + r[2];
    }});

    // Get objective from ALL_CAMPAIGNS
    const campLookup = {{}};
    ALL_CAMPAIGNS.forEach(c => {{ campLookup[c.name] = c; }});

    let rows = Object.values(campMap).filter(c => c.spend > 0);
    rows.forEach(c => {{
        const ref = campLookup[c.name] || {{}};
        c.cpl = c.leads > 0 ? c.spend / c.leads : 0;
        c.ctr = c.impressions > 0 ? (c.clicks / c.impressions * 100) : 0;
        c.is_active = (recentSpend[c.name] || 0) > 0;
        c.objective = ref.objective || 'OTHER';
    }});

    // Sort: ON first, then by spend desc
    rows.sort((a, b) => (a.is_active === b.is_active ? b.spend - a.spend : (a.is_active ? -1 : 1)));

    const cpls = rows.filter(c => c.cpl > 0).map(c => c.cpl);
    const minCpl = cpls.length ? Math.min(...cpls) : 0;
    const maxCpl = cpls.length ? Math.max(...cpls) : 1;

    const tbody = document.getElementById('campaignTableBody');
    tbody.innerHTML = rows.map(c => {{
        const rowStyle = c.is_active ? '' : ' style="opacity:0.45"';
        const cplDisp = c.cpl > 0 ? _fmtCOPTable(c.cpl) : '-';
        const spendDisp = _fmtCOPTable(c.spend);
        return `<tr${{rowStyle}}>`
            + `<td class="campaign-name">${{c.name}} ${{_objBadge(c.name)}} ${{_statusBadge(c.is_active)}}</td>`
            + `<td class="num">${{spendDisp}}</td>`
            + `<td class="num">${{c.impressions.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{c.clicks.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{c.ctr.toFixed(2)}}%</td>`
            + `<td class="num">${{c.leads}}</td>`
            + `<td class="num ${{_cplClass(c.cpl, minCpl, maxCpl)}}">${{cplDisp}}</td>`
            + `<td class="num">${{c.link_clicks.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{c.video_views.toLocaleString('es-CO')}}</td>`
            + `</tr>`;
    }}).join('');
}}

function updateAdsetTable(fromDate, toDate) {{
    // Aggregate daily adset data in range (ALL_ADSET_DAILY_RAW: [date, campaign_name, adset_name, spend, leads, impr, clicks, reach, link_clicks, video_views])
    const adsetMap = {{}};
    ALL_ADSET_DAILY_RAW.forEach(r => {{
        const [date, campName, adsetName, spend, leads, impr, clicks, reach, link_clicks, video_views] = r;
        if (date < fromDate || date > toDate) return;
        const key = campName + '|' + adsetName;
        if (!adsetMap[key]) adsetMap[key] = {{campaign_name: campName, name: adsetName, spend:0, leads:0, impressions:0, clicks:0, reach:0, link_clicks:0, video_views:0}};
        const a = adsetMap[key];
        a.spend += spend; a.leads += leads; a.impressions += impr;
        a.clicks += clicks; a.reach += reach;
        a.link_clicks += (link_clicks || 0);
        a.video_views += (video_views || 0);
    }});

    // Get active status (campaign spend in last 3 days of range)
    const datesInRange = [...new Set(ALL_ADSET_DAILY_RAW.filter(r => r[0] >= fromDate && r[0] <= toDate).map(r => r[0]))].sort();
    const last3Set = new Set(datesInRange.slice(-3));
    const recentSpend = {{}};
    ALL_ADSET_DAILY_RAW.forEach(r => {{
        if (last3Set.has(r[0])) {{
            const key = r[1] + '|' + r[2];
            recentSpend[key] = (recentSpend[key] || 0) + r[3];
        }}
    }});

    let rows = Object.values(adsetMap).filter(a => a.spend > 0);
    rows.forEach(a => {{
        a.cpl = a.leads > 0 ? a.spend / a.leads : 0;
        a.ctr = a.impressions > 0 ? (a.clicks / a.impressions * 100) : 0;
        const key = a.campaign_name + '|' + a.name;
        a.is_active = (recentSpend[key] || 0) > 0;
    }});

    // Sort: ON first, then by spend desc
    rows.sort((a, b) => (a.is_active === b.is_active ? b.spend - a.spend : (a.is_active ? -1 : 1)));

    const cpls = rows.filter(a => a.cpl > 0).map(a => a.cpl);
    const minCpl = cpls.length ? Math.min(...cpls) : 0;
    const maxCpl = cpls.length ? Math.max(...cpls) : 1;

    const tbody = document.getElementById('adsetTableBody');
    tbody.innerHTML = rows.map(a => {{
        const isOn = a.is_active;
        const rowStyle = isOn ? '' : ' style="opacity:0.45"';
        const cplDisp = a.cpl > 0 ? _fmtCOPTable(a.cpl) : '-';
        const spendDisp = _fmtCOPTable(a.spend);
        return `<tr${{rowStyle}}>`
            + `<td class="campaign-name">${{a.campaign_name}}</td>`
            + `<td class="adset-name">${{a.name}} ${{_statusBadge(isOn)}}</td>`
            + `<td class="num">${{spendDisp}}</td>`
            + `<td class="num">${{a.impressions.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{a.clicks.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{a.ctr.toFixed(2)}}%</td>`
            + `<td class="num">${{a.leads}}</td>`
            + `<td class="num ${{_cplClass(a.cpl, minCpl, maxCpl)}}">${{cplDisp}}</td>`
            + `<td class="num">${{a.link_clicks.toLocaleString('es-CO')}}</td>`
            + `<td class="num">${{a.video_views.toLocaleString('es-CO')}}</td>`
            + `</tr>`;
    }}).join('');
}}

function filterByDateRange() {{
    const fromDate = document.getElementById('dateFrom').value;
    const toDate = document.getElementById('dateTo').value;
    if (!fromDate || !toDate) return;

    // Filter indices
    const indices = [];
    ALL_DATES.forEach((d, i) => {{
        if (d >= fromDate && d <= toDate) indices.push(i);
    }});

    if (indices.length === 0) return;

    const labels = indices.map(i => ALL_LABELS[i]);
    const spend = indices.map(i => ALL_SPEND[i]);
    const leads = indices.map(i => ALL_LEADS[i]);
    const cpl = indices.map(i => ALL_CPL[i]);
    const ctr = indices.map(i => ALL_CTR[i]);
    const cpm = indices.map(i => ALL_CPM[i]);
    const impressions = indices.map(i => ALL_IMPRESSIONS[i]);
    const clicks = indices.map(i => ALL_CLICKS[i]);
    const reach = indices.map(i => ALL_REACH[i]);

    // Update charts
    dailyChart.data.labels = labels;
    dailyChart.data.datasets[0].data = spend;
    dailyChart.data.datasets[1].data = leads;
    dailyChart.update();

    cplChart.data.labels = labels;
    cplChart.data.datasets[0].data = cpl;
    cplChart.update();

    ctrChart.data.labels = labels;
    ctrChart.data.datasets[0].data = ctr;
    ctrChart.update();

    cpmChart.data.labels = labels;
    cpmChart.data.datasets[0].data = cpm;
    cpmChart.update();

    // Update KPIs
    const totalSpend = spend.reduce((a,b) => a+b, 0);
    const totalLeads = leads.reduce((a,b) => a+b, 0);
    const totalImpressions = impressions.reduce((a,b) => a+b, 0);
    const totalClicks = clicks.reduce((a,b) => a+b, 0);
    const totalReach = reach.reduce((a,b) => a+b, 0);
    const avgCPL = totalLeads > 0 ? totalSpend / totalLeads : 0;
    const avgCTR = totalImpressions > 0 ? (totalClicks / totalImpressions * 100) : 0;
    const avgCPM = totalImpressions > 0 ? (totalSpend / totalImpressions * 1000) : 0;
    const numDays = indices.length;

    document.getElementById('kpi-spend').textContent = fmtCOPFull(totalSpend);
    document.getElementById('kpi-spend-sub').textContent = `COP (${{numDays}} dias)`;
    document.getElementById('kpi-leads').textContent = fmtNum(totalLeads);
    document.getElementById('kpi-cpl').textContent = fmtCOPFull(avgCPL);
    document.getElementById('kpi-impressions').textContent = fmtNum(totalImpressions);
    document.getElementById('kpi-cpm-sub').textContent = 'CPM: ' + fmtCOPFull(avgCPM);
    document.getElementById('kpi-ctr').textContent = avgCTR.toFixed(2) + '%';
    document.getElementById('kpi-clicks-sub').textContent = fmtNum(totalClicks) + ' clics totales';
    document.getElementById('kpi-reach').textContent = fmtNum(totalReach);

    // Update date range display
    document.getElementById('dateRangeDisplay').textContent = fmtDateES(fromDate) + ' \u2014 ' + fmtDateES(toDate);

    // Update performers (dynamic)
    updatePerformers(fromDate, toDate);

    // Update tables (dynamic)
    updateCampaignTable(fromDate, toDate);
    updateAdsetTable(fromDate, toDate);
}}

// Attach date picker events
document.getElementById('dateFrom').addEventListener('change', filterByDateRange);
document.getElementById('dateTo').addEventListener('change', filterByDateRange);

// Initial call to apply date range on page load
filterByDateRange();

// Open calendar on click anywhere in the input
document.querySelectorAll('.date-range-picker input[type="date"]').forEach(inp => {{
    inp.addEventListener('click', function() {{
        try {{ this.showPicker(); }} catch(e) {{}}
    }});
}});

// ── SOURCE FILTER ──────────────────────────────────────
let currentSource = 'ambos';

function filterSource(source) {{
    currentSource = source;
    // Update button states
    document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.source-btn[data-source="${{source}}"]`).classList.add('active');

    const metaSections = document.querySelectorAll('.section-source-meta');
    const sheetSections = document.querySelectorAll('.section-source-sheet');
    const ventasSections = document.querySelectorAll('.section-source-ventas');

    if (source === 'meta') {{
        metaSections.forEach(s => s.classList.remove('section-hidden'));
        ventasSections.forEach(s => s.classList.add('section-hidden'));
        sheetSections.forEach(s => s.classList.add('section-hidden'));
    }} else if (source === 'sheet') {{
        metaSections.forEach(s => s.classList.add('section-hidden'));
        ventasSections.forEach(s => s.classList.remove('section-hidden'));
        sheetSections.forEach(s => s.classList.remove('section-hidden'));
    }} else {{
        // ambos
        metaSections.forEach(s => s.classList.remove('section-hidden'));
        ventasSections.forEach(s => s.classList.remove('section-hidden'));
        sheetSections.forEach(s => s.classList.remove('section-hidden'));
    }}
}}

function filterVentas(mes) {{
    currentMes = mes;
    // Update button states
    document.querySelectorAll('.filter-ventas').forEach(b => b.classList.remove('active'));
    document.querySelector(`.filter-ventas[data-mes="${{mes}}"]`).classList.add('active');

    const filtered = mes === 'ALL' ? ALL_VENTAS : ALL_VENTAS.filter(v => v.mes === mes);
    const metaFiltered = filtered.filter(v => v.fuente === 'META');

    // Recalculate ventas KPIs
    const totalCount = filtered.length;
    const totalRevenue = filtered.reduce((a,v) => a + v.precio, 0);
    const metaCount = metaFiltered.length;
    const metaRevenue = metaFiltered.reduce((a,v) => a + v.precio, 0);
    const metaTicket = metaCount > 0 ? metaRevenue / metaCount : 0;
    const metaDias = metaFiltered.filter(v => v.dias_cierre !== null).map(v => v.dias_cierre);
    const medianDias = metaDias.length > 0 ? metaDias.sort((a,b)=>a-b)[Math.floor(metaDias.length/2)] : 0;
    const avgDias = metaDias.length > 0 ? metaDias.reduce((a,b)=>a+b,0)/metaDias.length : 0;

    // Get current ads spend for ROAS calc (use actual calculated value)\n    const currentSpend = (function() {{\n        const from = document.getElementById('dateFrom').value;\n        const to = document.getElementById('dateTo').value;\n        const s = ALL_DATES.findIndex(d => d >= from);\n        const eIdx = ALL_DATES.findIndex(d => d > to);\n        const e = eIdx === -1 ? ALL_DATES.length : eIdx;\n        return ALL_SPEND.slice(s === -1 ? 0 : s, e).reduce((a,b) => a+b, 0);\n    }})() || {total_spend};
    const roas = currentSpend > 0 ? metaRevenue / currentSpend : 0;
    const cpv = metaCount > 0 ? currentSpend / metaCount : 0;

    document.getElementById('kpi-roas').textContent = roas.toFixed(1) + 'x';
    document.getElementById('kpi-meta-revenue').textContent = fmtCOPFull(metaRevenue);
    document.getElementById('kpi-meta-revenue-sub').textContent = metaCount + ' lotes vendidos via Meta';
    document.getElementById('kpi-total-revenue').textContent = fmtCOPFull(totalRevenue);
    document.getElementById('kpi-total-revenue-sub').textContent = totalCount + ' ventas todas las fuentes';
    document.getElementById('kpi-ticket').textContent = metaTicket > 0 ? fmtCOPFull(metaTicket) : '$0';
    document.getElementById('kpi-dias').textContent = medianDias + ' dias';
    document.getElementById('kpi-dias-sub').textContent = 'Mediana (' + avgDias.toFixed(1) + ' promedio)';
    document.getElementById('kpi-cpv').textContent = metaCount > 0 ? fmtCOPFull(cpv) : '$0';

    // Update source chart
    const bySource = {{}};
    filtered.forEach(v => {{
        if (!v.fuente) return;
        if (!bySource[v.fuente]) bySource[v.fuente] = {{count:0, revenue:0}};
        bySource[v.fuente].count++;
        bySource[v.fuente].revenue += v.precio;
    }});
    const srcEntries = Object.entries(bySource).sort((a,b) => b[1].revenue - a[1].revenue);
    const srcChart = Chart.getChart('sourceChart');
    if (srcChart) {{
        srcChart.data.labels = srcEntries.map(e => e[0]);
        srcChart.data.datasets[0].data = srcEntries.map(e => e[1].count);
        srcChart.data.datasets[1].data = srcEntries.map(e => e[1].revenue);
        srcChart.update();
    }}

    // Update source attribution table
    const sourceTableBody = document.querySelector('.section:has(#sourceChart) + .section tbody');
    if (sourceTableBody) {{
        let html = '';
        srcEntries.forEach(([src, data]) => {{
            const pctCount = totalCount > 0 ? (data.count/totalCount*100).toFixed(1) : '0.0';
            const pctRev = totalRevenue > 0 ? (data.revenue/totalRevenue*100).toFixed(1) : '0.0';
            const revD = data.revenue > 0 ? fmtCOPFull(data.revenue) : '<span style="color:var(--text-muted);font-size:11px">Sin dato</span>';
            const color = src === 'META' ? '#4361ee' : '#8892b0';
            html += `<tr><td style="font-weight:600;color:${{color}}">${{src}}</td><td class="num">${{data.count}}</td><td class="num">${{pctCount}}%</td><td class="num">${{revD}}</td><td class="num">${{pctRev}}%</td></tr>`;
        }});
        sourceTableBody.innerHTML = html;
    }}
}}

// AI Analysis generated server-side by OpenAI at build time.
// Client-side refresh available via button.

// ── Encrypted key + prompts for client-side refresh ──
const _ENC_KEY = "{_enc_key_b64}";
const _ENC_SALT = "meta-ads-los-lagos-2026";
const _SYS_PROMPT = {_system_prompt_js};
const _USR_PROMPT_TEMPLATE = {_user_prompt_js};

// ── Dynamic prompt builder based on date range ──
function _buildDynamicPrompt() {{
    const NL = String.fromCharCode(10);
    const fromVal = document.getElementById('dateFrom').value;
    const toVal = document.getElementById('dateTo').value;
    if (!fromVal || !toVal) return _USR_PROMPT_TEMPLATE;

    // ── Filter daily aggregated data by range ──
    const idxStart = ALL_DATES.findIndex(d => d >= fromVal);
    const idxEnd = ALL_DATES.findIndex(d => d > toVal);
    const end = idxEnd === -1 ? ALL_DATES.length : idxEnd;
    const start = idxStart === -1 ? 0 : idxStart;
    const numDays = end - start;
    if (numDays <= 0) return _USR_PROMPT_TEMPLATE;

    const fmt = n => Math.round(n).toLocaleString('es-CO');

    // ── Filter per-campaign daily data by range ──
    // ALL_DAILY_RAW: [date, camp_name, spend, leads, impr, clicks, reach, ctr, cpm]
    const filteredDaily = ALL_DAILY_RAW.filter(r => r[0] >= fromVal && r[0] <= toVal);

    // ── Aggregate per-campaign for the filtered range ──
    const campAgg = {{}};
    filteredDaily.forEach(r => {{
        const name = r[1];
        if (!campAgg[name]) campAgg[name] = {{spend:0, leads:0, impr:0, clicks:0, reach:0}};
        campAgg[name].spend += r[2];
        campAgg[name].leads += r[3];
        campAgg[name].impr += r[4];
        campAgg[name].clicks += r[5];
        campAgg[name].reach += r[6];
    }});

    // ── Build active campaigns list with filtered metrics ──
    const activeCamps = ALL_CAMPAIGNS.filter(c => c.is_active);
    const pausedCamps = ALL_CAMPAIGNS.filter(c => !c.is_active);
    const activeAdsets = ALL_ADSETS.filter(a => a.is_active);

    // Enrich campaigns with filtered data
    const campData = activeCamps.map(c => {{
        const agg = campAgg[c.name] || {{spend:0, leads:0, impr:0, clicks:0, reach:0}};
        const cpl = agg.leads > 0 ? agg.spend / agg.leads : 0;
        const ctr = agg.impr > 0 ? (agg.clicks / agg.impr * 100) : 0;
        const freq = agg.reach > 0 ? (agg.impr / agg.reach) : 0;
        return {{name: c.name, spend: agg.spend, leads: agg.leads, cpl, ctr, freq, reach: agg.reach, impr: agg.impr}};
    }}).filter(c => c.spend > 0).sort((a,b) => b.spend - a.spend);

    // Enrich adsets - aggregate per adset from daily (by campaign match)
    const adsetData = activeAdsets.map(a => {{
        // Use campaign-level daily to get ratio for this adset (proportional)
        // Since daily is per-campaign, use adset's original proportions within its campaign
        const campTotal = ALL_CAMPAIGNS.find(c => c.name === a.campaign_name);
        const campFiltered = campAgg[a.campaign_name];
        if (!campTotal || !campFiltered || campTotal.spend === 0) return null;
        const ratio = campFiltered.spend / campTotal.spend;
        const spend = a.spend * ratio;
        const leads = Math.round(a.leads * ratio);
        const cpl = leads > 0 ? spend / leads : 0;
        const impr = Math.round(a.impressions * ratio);
        const reach = Math.round(a.reach * ratio);
        const ctr = impr > 0 ? (Math.round(a.ctr * 100) / 100) : 0;
        const freq = a.frequency;
        return {{campaign: a.campaign_name, name: a.name, spend, leads, cpl, ctr, freq, reach}};
    }}).filter(a => a && a.spend > 0).sort((a,b) => b.spend - a.spend);

    // Paused campaigns with filtered data
    const pausedData = pausedCamps.map(c => {{
        const agg = campAgg[c.name] || {{spend:0, leads:0}};
        const cpl = agg.leads > 0 ? agg.spend / agg.leads : 0;
        return {{name: c.name, spend: agg.spend, leads: agg.leads, cpl}};
    }}).sort((a,b) => b.spend - a.spend);

    // ── Account-level totals for filtered range ──
    const fSpend = ALL_SPEND.slice(start, end);
    const fLeads = ALL_LEADS.slice(start, end);
    const fImpr = ALL_IMPRESSIONS.slice(start, end);
    const fClicks = ALL_CLICKS.slice(start, end);
    const fReach = ALL_REACH.slice(start, end);
    const fLabels = ALL_LABELS.slice(start, end);
    const fCPL = ALL_CPL.slice(start, end);
    const fCTR = ALL_CTR.slice(start, end);

    const sumSpend = fSpend.reduce((a,b) => a+b, 0);
    const sumLeads = fLeads.reduce((a,b) => a+b, 0);
    const sumImpr = fImpr.reduce((a,b) => a+b, 0);
    const sumClicks = fClicks.reduce((a,b) => a+b, 0);
    const sumReach = fReach.reduce((a,b) => a+b, 0);
    const avgCPL = sumLeads > 0 ? sumSpend / sumLeads : 0;
    const avgCTR = sumImpr > 0 ? (sumClicks / sumImpr * 100) : 0;
    const avgCPM = sumImpr > 0 ? (sumSpend / sumImpr * 1000) : 0;
    const avgCPC = sumClicks > 0 ? (sumSpend / sumClicks) : 0;
    const cplUSD = avgCPL / 4400;

    // Video views & engagement from active campaigns (proportional)
    let totalVV = 0, totalEng = 0, totalMsg = 0;
    activeCamps.forEach(c => {{
        const campOrig = campAgg[c.name];
        if (campOrig && c.spend > 0) {{
            const ratio = campOrig.spend / c.spend;
            totalVV += Math.round(c.video_views * ratio);
            totalEng += Math.round(c.engagement * ratio);
            totalMsg += Math.round(c.messaging * ratio);
        }}
    }});

    // ── Daily trend (last 7 of filtered range) ──
    const trendN = Math.min(7, numDays);
    const tS = numDays - trendN;
    let dailyLines = [];
    for (let i = tS; i < numDays; i++) {{
        const d = ALL_DATES.slice(start, end)[i];
        dailyLines.push('  - ' + d + ' | Spend: $' + fmt(fSpend[i]) + ' | Leads: ' + fLeads[i] + ' | CPL: $' + fmt(fCPL[i]) + ' | CTR: ' + fCTR[i] + '%');
    }}

    // ── Weekly comparison within range ──
    const midE = Math.max(0, numDays - 7);
    const midW = Math.max(0, numDays - 14);
    const w1Spend = fSpend.slice(midW, midE).reduce((a,b) => a+b, 0);
    const w1Leads = fLeads.slice(midW, midE).reduce((a,b) => a+b, 0);
    const w1CPL = w1Leads > 0 ? w1Spend / w1Leads : 0;
    const w2Spend = fSpend.slice(midE).reduce((a,b) => a+b, 0);
    const w2Leads = fLeads.slice(midE).reduce((a,b) => a+b, 0);
    const w2CPL = w2Leads > 0 ? w2Spend / w2Leads : 0;

    // ── Campaign lines ──
    const campLines = campData.map(c =>
        '  - ' + c.name + ' | Spend: $' + fmt(c.spend) + ' | Leads: ' + c.leads + ' | CPL: $' + fmt(c.cpl) + ' | CTR: ' + c.ctr.toFixed(2) + '% | Freq: ' + c.freq.toFixed(2) + ' | Reach: ' + fmt(c.reach) + ' | Impr: ' + fmt(c.impr)
    );
    const pausedLines = pausedData.filter(c => c.spend > 0).map(c =>
        '  - ' + c.name + ' | Spend: $' + fmt(c.spend) + ' | Leads: ' + c.leads + ' | CPL: $' + fmt(c.cpl)
    );
    const adsetLines = adsetData.map(a =>
        '  - ' + a.campaign + ' -> ' + a.name + ' | Spend: $' + fmt(a.spend) + ' | Leads: ' + a.leads + ' | CPL: $' + fmt(a.cpl) + ' | CTR: ' + a.ctr.toFixed(2) + '% | Freq: ' + a.freq.toFixed(2) + ' | Reach: ' + fmt(a.reach)
    );

    // ── Build the full prompt from scratch ──
    const prompt = 'Analiza estos datos de Meta Ads para Los Lagos Condominio y genera recomendaciones:' + NL + NL +
        'RESUMEN GENERAL (periodo: ' + fromVal + ' a ' + toVal + ', ' + numDays + ' dias):' + NL +
        '- Inversion total: $' + fmt(sumSpend) + ' COP' + NL +
        '- Leads totales: ' + fmt(sumLeads) + NL +
        '- CPL promedio: $' + fmt(avgCPL) + ' COP (~$' + cplUSD.toFixed(2) + ' USD)' + NL +
        '- CTR: ' + avgCTR.toFixed(2) + '%' + NL +
        '- CPM: $' + fmt(avgCPM) + ' COP' + NL +
        '- CPC: $' + fmt(avgCPC) + ' COP' + NL +
        '- Impresiones: ' + fmt(sumImpr) + NL +
        '- Alcance: ' + fmt(sumReach) + NL +
        '- Video Views: ' + fmt(totalVV) + NL +
        '- Engagement: ' + fmt(totalEng) + NL +
        '- Mensajeria: ' + fmt(totalMsg) + NL + NL +
        'ESTADO DE CUENTA:' + NL +
        '- Campanas activas (ON): ' + campData.length + ' de ' + ALL_CAMPAIGNS.length + NL +
        '- Conjuntos activos: ' + adsetData.length + ' de ' + ALL_ADSETS.length + NL +
        '- Campanas pausadas: ' + pausedCamps.length + NL + NL +
        'CAMPANAS ACTIVAS (ordenadas por inversion, datos del periodo seleccionado):' + NL +
        (campLines.length > 0 ? campLines.join(NL) : '  Ninguna con gasto en este periodo') + NL + NL +
        'CAMPANAS PAUSADAS:' + NL +
        (pausedLines.length > 0 ? pausedLines.join(NL) : '  Ninguna') + NL + NL +
        'CONJUNTOS DE ANUNCIOS ACTIVOS (ordenados por inversion):' + NL +
        (adsetLines.length > 0 ? adsetLines.join(NL) : '  Ninguno con gasto en este periodo') + NL + NL +
        'TENDENCIA DIARIA (ultimos ' + trendN + ' dias):' + NL +
        dailyLines.join(NL) + NL + NL +
        'TENDENCIA SEMANAL:' + NL +
        '- Semana anterior: Spend $' + fmt(w1Spend) + ' | Leads: ' + w1Leads + ' | CPL: $' + fmt(w1CPL) + NL +
        '- Ultima semana: Spend $' + fmt(w2Spend) + ' | Leads: ' + w2Leads + ' | CPL: $' + fmt(w2CPL) + NL + NL +
        'BENCHMARKS SECTOR INMOBILIARIO COLOMBIA:' + NL +
        '- CTR promedio: 0.9% - 1.5%' + NL +
        '- CPM promedio: $5,000 - $12,000 COP' + NL +
        '- Frecuencia ideal: < 2.5' + NL +
        '- CPL competitivo real estate: $8,000 - $25,000 COP' + NL + NL +
        'Responde ESTRICTAMENTE en JSON valido con esta estructura (sin markdown, sin ' + '`' + '`' + '`' + 'json, solo el JSON puro):' + NL +
        '{{' + NL +
        '  "positivo": ["item1", "item2", ...maximo 6 items],' + NL +
        '  "vigilar": ["item1", "item2", ...maximo 6 items],' + NL +
        '  "recomendaciones": ["item1", "item2", ...maximo 6 items]' + NL +
        '}}' + NL + NL +
        'REGLAS:' + NL +
        '1. Cada item: 1-2 oraciones con datos numericos especificos' + NL +
        '2. "positivo": Metricas que funcionan bien vs benchmarks inmobiliarios' + NL +
        '3. "vigilar": Senales de alerta, tendencias negativas, riesgos de Auction Overlap, fatiga, learning phase' + NL +
        '4. "recomendaciones": Acciones concretas y especificas para optimizar Meta Ads' + NL +
        '5. Mencionar nombres de campanas y conjuntos especificos cuando sea relevante' + NL +
        '6. NO mencionar Google Sheets, ventas reales, ROAS de ventas ni datos externos' + NL +
        '7. Solo metricas de Meta Ads API';

    return prompt;
}}

// Populate prompt viewer with initial prompt
let _currentPrompt = _USR_PROMPT_TEMPLATE;
document.getElementById('systemPromptText').textContent = _SYS_PROMPT;
document.getElementById('userPromptText').textContent = _currentPrompt;

function togglePrompt() {{
    // Refresh prompt display with current dynamic values
    _currentPrompt = _buildDynamicPrompt();
    document.getElementById('userPromptText').textContent = _currentPrompt;
    const el = document.getElementById('promptViewer');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}

async function _deriveKey(salt) {{
    const enc = new TextEncoder();
    const keyData = await crypto.subtle.digest('SHA-256', enc.encode(salt));
    return new Uint8Array(keyData);
}}

async function _decryptKey() {{
    const key = await _deriveKey(_ENC_SALT);
    const encrypted = Uint8Array.from(atob(_ENC_KEY), c => c.charCodeAt(0));
    const decrypted = new Uint8Array(encrypted.length);
    for (let i = 0; i < encrypted.length; i++) {{
        decrypted[i] = encrypted[i] ^ key[i % key.length];
    }}
    return new TextDecoder().decode(decrypted);
}}

function _highlightText(text) {{
    return text.replace(/(\\$[\\d,.]+|\\d+[.,]?\\d*%|\\d+[.,]\\d+x)/g, '<span class="analysis-highlight">$1</span>');
}}

function _buildCardHTML(cls, icon, title, items) {{
    let html = '<div class="analysis-card ' + cls + '"><div class="analysis-card-header"><span class="analysis-icon">' + icon + '</span><h3>' + title + '</h3></div>';
    items.slice(0, 8).forEach(item => {{
        html += '<div class="analysis-item"><span class="analysis-bullet"></span><span>' + _highlightText(item) + '</span></div>';
    }});
    html += '</div>';
    return html;
}}

async function refreshAnalysis() {{
    const btn = document.getElementById('btnRefreshAI');
    const grid = document.getElementById('analysisGrid');
    const ts = document.getElementById('analysisTimestamp');

    btn.disabled = true;
    btn.innerHTML = '&#9203; Generando...';
    btn.style.opacity = '0.6';
    ts.textContent = 'Conectando con OpenAI...';

    try {{
        const apiKey = await _decryptKey();
        const dynamicPrompt = _buildDynamicPrompt();
        _currentPrompt = dynamicPrompt;
        const fromD = document.getElementById('dateFrom').value;
        const toD = document.getElementById('dateTo').value;
        ts.textContent = 'Analizando periodo ' + fromD + ' a ' + toD + '...';

        const response = await fetch('https://api.openai.com/v1/chat/completions', {{
            method: 'POST',
            headers: {{
                'Authorization': 'Bearer ' + apiKey,
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify({{
                model: 'gpt-4o-mini',
                messages: [
                    {{ role: 'system', content: _SYS_PROMPT }},
                    {{ role: 'user', content: dynamicPrompt }},
                ],
                temperature: 0.7,
                max_tokens: 2500,
            }}),
        }});

        if (!response.ok) {{
            const err = await response.text();
            throw new Error('API ' + response.status + ': ' + err.substring(0, 200));
        }}

        const data = await response.json();
        let content = data.choices[0].message.content.trim();

        // Strip markdown code fences if present
        if (content.startsWith('`' + '``')) {{
            content = content.split(String.fromCharCode(10)).slice(1).join(String.fromCharCode(10));
        }}
        if (content.endsWith('`' + '``')) {{
            content = content.slice(0, -3);
        }}
        content = content.trim();

        const analysis = JSON.parse(content);
        const now = new Date();
        const pad = n => String(n).padStart(2, '0');
        const timestamp = pad(now.getDate()) + '/' + pad(now.getMonth()+1) + '/' + now.getFullYear() + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());

        grid.innerHTML =
            _buildCardHTML('positive', '&#9989;', 'Lo Positivo', analysis.positivo || []) +
            _buildCardHTML('warning', '&#9888;&#65039;', 'A Vigilar', analysis.vigilar || []) +
            _buildCardHTML('recommend', '&#128161;', 'Recomendaciones', analysis.recomendaciones || []);

        ts.innerHTML = 'Actualizado por OpenAI (gpt-4o-mini) | ' + timestamp + ' | <span style="color:var(--accent-cyan)">&#9889; Refresh exitoso</span>';

    }} catch (e) {{
        ts.innerHTML = '<span style="color:var(--accent-red)">&#9888; Error: ' + e.message.substring(0, 150) + '</span>';
        console.error('OpenAI refresh error:', e);
    }} finally {{
        btn.disabled = false;
        btn.innerHTML = '&#9889; Actualizar Analisis';
        btn.style.opacity = '1';
    }}
}}

// ── REFRESH DATA (Meta Ads + Google Sheets + Rebuild) ──
async function refreshData() {{
    const btn = document.getElementById('btnRefreshData');
    const updatedEl = document.getElementById('lastUpdated');
    const origText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Refrescando...';

    // Create or show log element
    let logEl = document.getElementById('refreshLog');
    if (!logEl) {{
        logEl = document.createElement('div');
        logEl.id = 'refreshLog';
        logEl.className = 'refresh-log';
        btn.parentElement.appendChild(logEl);
    }}
    logEl.style.display = 'block';
    logEl.textContent = 'Iniciando refresh de datos...\\n';

    try {{
        const resp = await fetch('/api/refresh');
        const data = await resp.json();

        logEl.textContent = data.log || 'Sin log disponible';

        if (data.ok) {{
            updatedEl.textContent = 'Ultima actualizacion: ' + data.timestamp;
            logEl.textContent += '\\n\\n✅ Recargando pagina en 3s...';
            setTimeout(() => window.location.reload(), 3000);
        }} else {{
            logEl.textContent += '\\n\\n⚠️ Hubo errores. Revisa el log arriba.';
            btn.disabled = false;
            btn.innerHTML = origText;
        }}
    }} catch (e) {{
        logEl.textContent = '❌ Error de conexion: ' + e.message + '\\n\\n';
        logEl.textContent += 'Asegurate de estar usando server.py:\\n';
        logEl.textContent += '  python3 server.py\\n';
        logEl.textContent += '\\n(El servidor simple de Python no soporta /api/refresh)';
        btn.disabled = false;
        btn.innerHTML = origText;
    }}
}}

</script>
</body>
</html>""" 

# ── Write output ────────────────────────────────────────────────────────────
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

file_size = os.path.getsize(OUTPUT_FILE)
print(f"\nDashboard generated successfully!")
print(f"Output: {OUTPUT_FILE}")
print(f"File size: {file_size / 1024:.1f} KB")
print(f"\nAccount KPIs:")
print(f"  Total Spend:      ${total_spend:,.0f} COP")
print(f"  Total Leads:      {total_leads:,}")
print(f"  Avg CPL:          ${avg_cpl:,.0f} COP")
print(f"  Total Impressions: {total_impressions:,}")
print(f"  CTR:              {avg_ctr:.2f}%")
print(f"  Total Reach:      {total_reach:,}")
print(f"  Video Views:      {total_video_views:,}")
print(f"  Engagement:       {total_engagement:,}")
print(f"  Campaigns:        {len(campaigns)}")
print(f"  Ad Sets:          {len(adsets)}")
print(f"  Daily Data Points: {len(daily_dates)}")
