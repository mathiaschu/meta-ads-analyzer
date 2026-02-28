#!/usr/bin/env python3
"""
Refresh Meta Ads data directly from Graph API.
Fetches campaign, adset, and daily insights → saves to JSON files.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AD_ACCOUNT_ID = "act_1089998585939349"
API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

# Output files
AD_INSIGHTS_FILE = os.path.join(SCRIPT_DIR, "ad_insights.json")
DAILY_INSIGHTS_FILE = os.path.join(SCRIPT_DIR, "daily_insights.json")
ADSET_INSIGHTS_FILE = os.path.join(SCRIPT_DIR, "adset_insights.json")
DAILY_ADSET_INSIGHTS_FILE = os.path.join(SCRIPT_DIR, "daily_adset_insights.json")

# Date range: last 30 days
DATE_END = datetime.now().strftime("%Y-%m-%d")
DATE_START = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

FIELDS_AD = ",".join([
    "campaign_id", "campaign_name", "ad_id", "ad_name", "adset_name",
    "impressions", "clicks", "spend", "cpc", "cpm", "ctr",
    "reach", "frequency", "actions", "cost_per_action_type"
])

FIELDS_CAMPAIGN_DAILY = ",".join([
    "campaign_id", "campaign_name",
    "impressions", "clicks", "spend", "cpc", "cpm", "ctr",
    "reach", "frequency", "actions", "cost_per_action_type"
])

FIELDS_ADSET = ",".join([
    "campaign_name", "adset_id", "adset_name",
    "impressions", "clicks", "spend", "cpc", "cpm", "ctr",
    "reach", "frequency", "actions", "cost_per_action_type"
])

FIELDS_ADSET_DAILY = ",".join([
    "campaign_name", "adset_id", "adset_name",
    "impressions", "clicks", "spend", "cpm", "ctr",
    "reach", "actions"
])


def load_token():
    """Load access token from .env.meta-ads or .mcp.json."""
    env_file = os.path.join(SCRIPT_DIR, ".env.meta-ads")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("export META_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    mcp_file = os.path.join(SCRIPT_DIR, ".mcp.json")
    if os.path.exists(mcp_file):
        with open(mcp_file) as f:
            mcp = json.load(f)
        env = mcp.get("mcpServers", {}).get("meta-ads", {}).get("env", {})
        return env.get("META_ACCESS_TOKEN", "")

    return ""


def api_call(path, params=None):
    """Make a GET request to the Graph API, handling pagination."""
    token = load_token()
    if not token:
        raise ValueError("No Meta access token found. Run scripts/setup.sh first.")

    all_data = []
    base_params = params or {}
    base_params["access_token"] = token

    query = "&".join(f"{k}={urllib.request.quote(str(v), safe='{}:,\"')}" for k, v in base_params.items())
    url = f"{BASE_URL}/{path}?{query}"

    while url:
        req = urllib.request.Request(url, headers={"User-Agent": "MetaAdsDashboard/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise Exception(f"HTTP {e.code}: {body[:500]}")

        all_data.extend(data.get("data", []))
        url = data.get("paging", {}).get("next", "")

    return {"data": all_data}


def fetch_ad_insights():
    """Fetch ad-level insights (30-day aggregate)."""
    print(f"  Fetching ad insights ({DATE_START} → {DATE_END})...")
    result = api_call(f"{AD_ACCOUNT_ID}/insights", {
        "level": "ad",
        "fields": FIELDS_AD,
        "time_range": json.dumps({"since": DATE_START, "until": DATE_END}),
        "limit": "500"
    })
    with open(AD_INSIGHTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"    ✅ {len(result['data'])} ad records → ad_insights.json")
    return True


def fetch_daily_insights():
    """Fetch campaign-level daily insights."""
    print(f"  Fetching daily insights ({DATE_START} → {DATE_END})...")
    result = api_call(f"{AD_ACCOUNT_ID}/insights", {
        "level": "campaign",
        "fields": FIELDS_CAMPAIGN_DAILY,
        "time_range": json.dumps({"since": DATE_START, "until": DATE_END}),
        "time_increment": "1",
        "limit": "500"
    })
    with open(DAILY_INSIGHTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    dates = sorted(set(r.get("date_start", "") for r in result["data"]))
    camps = set(r.get("campaign_name", "") for r in result["data"])
    print(f"    ✅ {len(result['data'])} daily records ({len(camps)} campaigns, "
          f"{len(dates)} days) → daily_insights.json")
    return True


def fetch_adset_insights():
    """Fetch adset-level insights (30-day aggregate)."""
    print(f"  Fetching adset insights ({DATE_START} → {DATE_END})...")
    result = api_call(f"{AD_ACCOUNT_ID}/insights", {
        "level": "adset",
        "fields": FIELDS_ADSET,
        "time_range": json.dumps({"since": DATE_START, "until": DATE_END}),
        "limit": "500"
    })
    with open(ADSET_INSIGHTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"    ✅ {len(result['data'])} adset records → adset_insights.json")
    return True


def fetch_daily_adset_insights():
    """Fetch adset-level daily insights."""
    print(f"  Fetching daily adset insights ({DATE_START} → {DATE_END})...")
    result = api_call(f"{AD_ACCOUNT_ID}/insights", {
        "level": "adset",
        "fields": FIELDS_ADSET_DAILY,
        "time_range": json.dumps({"since": DATE_START, "until": DATE_END}),
        "time_increment": "1",
        "limit": "500"
    })
    with open(DAILY_ADSET_INSIGHTS_FILE, "w") as f:
        json.dump(result, f, indent=2)
    dates = sorted(set(r.get("date_start", "") for r in result["data"]))
    adsets = set(r.get("adset_name", "") for r in result["data"])
    print(f"    ✅ {len(result['data'])} daily adset records ({len(adsets)} adsets, "
          f"{len(dates)} days) → daily_adset_insights.json")
    return True


def main():
    print(f"=== Refreshing Meta Ads Data ===")
    print(f"Account: {AD_ACCOUNT_ID}")
    print(f"Period: {DATE_START} to {DATE_END}")
    print()

    ok = True
    try:
        fetch_ad_insights()
    except Exception as e:
        print(f"    ❌ ad insights error: {e}")
        ok = False

    try:
        fetch_daily_insights()
    except Exception as e:
        print(f"    ❌ daily insights error: {e}")
        ok = False

    try:
        fetch_adset_insights()
    except Exception as e:
        print(f"    ❌ adset insights error: {e}")
        ok = False

    try:
        fetch_daily_adset_insights()
    except Exception as e:
        print(f"    ❌ daily adset insights error: {e}")
        ok = False

    if ok:
        print(f"\n✅ All Meta Ads data refreshed successfully!")
    else:
        print(f"\n⚠️  Some data failed to refresh.")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
