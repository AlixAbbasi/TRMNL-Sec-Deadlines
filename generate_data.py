import requests
import yaml
import os
import json
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import re

# Same configuration as main script
TRACKED_NAMES = [
    "S&P (Oakland)", "USENIX Security", "CCS", "NDSS",
    "ACSAC", "RAID", "DIMVA", "Euro S&P",
    "SpaceSec", "ESORICS", "CPSS", "ASIACCS", "WiSec", "FUZZING", "DSN"
]

CONFIG = {
    "max_days_ahead": 365,
    "include_workshops": True,
    "prioritize_top_tier": True,
    "show_expired_days": 7,
    "max_display_items": 15,
}

CONFERENCE_TIERS = {
    "S&P (Oakland)": {"tier": "TOP4", "category": "Security & Privacy", "rank": 1},
    "USENIX Security": {"tier": "TOP4", "category": "Security & Privacy", "rank": 2},
    "CCS": {"tier": "TOP4", "category": "Security & Privacy", "rank": 3},
    "NDSS": {"tier": "TOP4", "category": "Security & Privacy", "rank": 4},
    "ACSAC": {"tier": "TIER2", "category": "Security Applications", "rank": 5},
    "RAID": {"tier": "TIER2", "category": "Security Defense", "rank": 6},
    "DIMVA": {"tier": "TIER2", "category": "Malware & Vulnerabilities", "rank": 7},
    "Euro S&P": {"tier": "TIER2", "category": "Security & Privacy", "rank": 8},
    "ESORICS": {"tier": "TIER2", "category": "Security Research", "rank": 9},
    "ASIACCS": {"tier": "TIER2", "category": "Security & Privacy", "rank": 10},
    "DSN": {"tier": "TIER2", "category": "Dependable Systems", "rank": 11},
    "CPSS": {"tier": "WORKSHOP", "category": "Cyber-Physical", "rank": 12},
    "WiSec": {"tier": "TIER3", "category": "Wireless Security", "rank": 13},
    "FUZZING": {"tier": "WORKSHOP", "category": "Testing", "rank": 14},
    "SpaceSec": {"tier": "WORKSHOP", "category": "Space Security", "rank": 15}
}

DEFAULT_TZ = pytz.timezone("Etc/GMT+12")
TARGET_TZ = pytz.timezone("Europe/Berlin")

def get_urgency_info(deadline_dt, now_dt):
    time_diff = deadline_dt - now_dt
    days = time_diff.days
    hours = time_diff.seconds // 3600
    
    if days < 0:
        return {"level": "EXPIRED", "text": "Expired", "class": "expired"}
    elif days == 0:
        return {"level": "URGENT", "text": f"{hours}h left", "class": "urgent"}
    elif days <= 1:
        return {"level": "URGENT", "text": f"{days}d {hours}h", "class": "urgent"}
    elif days <= 7:
        return {"level": "SOON", "text": f"{days} days", "class": "soon"}
    elif days <= 30:
        return {"level": "UPCOMING", "text": f"{days} days", "class": "upcoming"}
    else:
        return {"level": "DISTANT", "text": f"{days} days", "class": "distant"}

def extract_conference_info(conf):
    description = conf.get('description', '')
    tags = conf.get('tags', [])
    
    conf_type = "Conference"
    if "SHOP" in tags:
        conf_type = "Workshop"
    elif "CONF" in tags:
        conf_type = "Conference"
    
    venue = "Unknown"
    if "IEEE" in description:
        venue = "IEEE"
    elif "ACM" in description:
        venue = "ACM"
    elif "USENIX" in description:
        venue = "USENIX"
    elif "ISOC" in description:
        venue = "ISOC"
    
    return {
        "type": conf_type,
        "venue": venue,
        "description": description,
        "tags": tags
    }

def get_conference_timezone(conf):
    tz_str = conf.get('timezone', None)
    if tz_str:
        try:
            return pytz.timezone(tz_str)
        except Exception:
            return DEFAULT_TZ
    else:
        return DEFAULT_TZ

def adjust_midnight(deadline_str):
    date_part, time_part = deadline_str.split()
    segments = time_part.split(":")
    if len(segments) == 2 and segments[1] == "00":
        hour = int(segments[0])
        if hour == 0:
            dt_base = datetime.strptime(date_part, "%Y-%m-%d")
            dt_base -= timedelta(days=1)
            date_part = dt_base.strftime("%Y-%m-%d")
            time_part = "23:59:59"
        else:
            hour -= 1
            time_part = f"{hour:02d}:59:59"
    elif len(segments) == 3 and segments[2] == "00":
        hour = int(segments[0])
        minute = int(segments[1])
        second = int(segments[2])
        if minute == 0 and second == 0:
            if hour == 0:
                dt_base = datetime.strptime(date_part, "%Y-%m-%d")
                dt_base -= timedelta(days=1)
                date_part = dt_base.strftime("%Y-%m-%d")
                time_part = "23:59:59"
            else:
                hour -= 1
                time_part = f"{hour:02d}:59:59"
    return f"{date_part} {time_part}"

def handle_placeholders(dl_str, conf_year):
    conf_year_int = int(conf_year)
    dl_str = dl_str.replace("%y", str(conf_year_int))
    dl_str = dl_str.replace("%Y", str(conf_year_int - 1))
    return dl_str

def parse_deadline(dl_str, source_tz, conf_year):
    dl_str = handle_placeholders(dl_str, conf_year)
    
    if " " in dl_str:
        dl_str = adjust_midnight(dl_str)
        date_part, time_part = dl_str.split()
        if time_part.count(":") == 1:
            dl_str = f"{date_part} {time_part}:59"
    else:
        dl_str = dl_str.strip() + " 23:59:59"

    naive_dt = parser.parse(dl_str)
    dt = source_tz.localize(naive_dt)
    return dt

def generate_conference_data():
    """Generate the conference data for TRMNL polling - Updated Sep 22"""
    print("🔄 Generating conference data for TRMNL polling...")
    
    url = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/refs/heads/master/_data/conferences.yml"
    
    try:
        print("📥 Fetching conference data...")
        response = requests.get(url)
        response.raise_for_status()
        raw_yaml = response.text
        conferences_data = yaml.safe_load(raw_yaml)
        print(f"✅ Successfully loaded {len(conferences_data)} conferences")
    except Exception as e:
        print(f"❌ Error fetching conference data: {e}")
        return None

    now_local = datetime.now(TARGET_TZ)
    filtered = []
    
    total_processed = 0
    excluded_workshops = 0
    excluded_too_far = 0
  
    for conf in conferences_data:
        conf_name = conf.get('name')
        if conf_name in TRACKED_NAMES:
            total_processed += 1
            
            conf_info = extract_conference_info(conf)
            if not CONFIG["include_workshops"] and conf_info["type"] == "Workshop":
                excluded_workshops += 1
                continue
            
            deadlines = conf.get('deadline', [])
            if not deadlines:
                continue

            source_tz = get_conference_timezone(conf)
            conf_year = conf.get('year')
            parsed_all = []
            for dl_str in deadlines:
                dt = parse_deadline(dl_str, source_tz, conf_year)
                dt_local = dt.astimezone(TARGET_TZ)
                parsed_all.append(dt_local)

            parsed_all.sort()
            
            valid_deadlines = []
            for dl in parsed_all:
                days_diff = (dl - now_local).days
                
                if days_diff >= -CONFIG["show_expired_days"] and days_diff <= CONFIG["max_days_ahead"]:
                    valid_deadlines.append(dl)
                elif days_diff > CONFIG["max_days_ahead"]:
                    excluded_too_far += 1
            
            if not valid_deadlines:
                continue
                
            future_deadlines = [d for d in valid_deadlines if d > now_local]
            next_dl = future_deadlines[0] if future_deadlines else valid_deadlines[-1]
            
            total_count = len(parsed_all)
            deadline_position = parsed_all.index(next_dl) + 1
            
            tier_info = CONFERENCE_TIERS.get(conf_name, {
                "tier": "OTHER", "category": "General", "rank": 99
            })
            urgency_info = get_urgency_info(next_dl, now_local)
            days_until = (next_dl - now_local).days
            
            conf_date = conf.get('date', 'TBD')
            if conf_date and conf_date != 'TBD':
                conf_date = re.sub(r'\s+', ' ', conf_date.strip())
            
            short_name = conf_name
            if conf_name == "S&P (Oakland)":
                short_name = "IEEE S&P"
            elif conf_name == "USENIX Security":
                short_name = "USENIX Sec"
            elif "Euro S&P" in conf_name:
                short_name = "Euro S&P"

            conf_record = {
                "name": conf_name,
                "short_name": short_name,
                "year": conf.get('year'),
                "place": conf.get('place', 'TBD'),
                "date": conf_date,
                "link": conf.get('link'),
                "next_deadline": next_dl.strftime("%Y-%m-%d %H:%M:%S"),
                "deadline_formatted": next_dl.strftime("%b %d, %H:%M"),
                "days_until": days_until,
                "total_deadlines": total_count,
                "deadline_position": deadline_position,
                "remaining_deadlines": total_count - deadline_position,
                "tier": tier_info["tier"],
                "category": tier_info["category"],
                "rank": tier_info["rank"],
                "urgency": urgency_info,
                "venue": conf_info["venue"],
                "type": conf_info["type"],
                "description": conf_info["description"],
                "is_multi_deadline": total_count > 1,
                "comment": conf.get('comment', ''),
            }
            filtered.append(conf_record)

    if CONFIG["prioritize_top_tier"]:
        filtered.sort(key=lambda c: (
            0 if c["urgency"]["level"] in ["URGENT", "SOON"] else 1,
            c["rank"],
            parser.isoparse(c["next_deadline"])
        ))
    else:
        filtered.sort(key=lambda c: parser.isoparse(c["next_deadline"]))
    
    filtered = filtered[:CONFIG["max_display_items"]]
    
    print(f"📊 Generated data for {len(filtered)} conferences")
    
    urgent_count = len([c for c in filtered if c["urgency"]["level"] in ["URGENT", "SOON"]])
    top_tier_count = len([c for c in filtered if c["tier"] == "TOP4"])
    workshop_count = len([c for c in filtered if c["type"] == "Workshop"])
    expired_count = len([c for c in filtered if c["days_until"] < 0])
    
    next_urgent = None
    if urgent_count > 0:
        urgent_confs = [c for c in filtered if c["urgency"]["level"] in ["URGENT", "SOON"]]
        urgent_confs.sort(key=lambda c: parser.isoparse(c["next_deadline"]))
        next_urgent = urgent_confs[0]

    return {
        "conferences": filtered,
        "stats": {
            "total_conferences": len(filtered),
            "urgent_count": urgent_count,
            "top_tier_count": top_tier_count,
            "workshop_count": workshop_count,
            "expired_count": expired_count,
            "next_urgent": next_urgent,
            "config": CONFIG
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_updated_friendly": datetime.now().strftime("%b %d, %H:%M")
    }

if __name__ == "__main__":
    data = generate_conference_data()
    if data:
        # Save to JSON file for GitHub Pages or other hosting
        with open('trmnl-data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("✅ Data saved to trmnl-data.json")
        print("📁 Upload this file to a web server for TRMNL polling")
    else:
        print("❌ Failed to generate data")