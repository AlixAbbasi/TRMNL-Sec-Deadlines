import requests
import yaml
import os
from datetime import datetime, timedelta
from dateutil import parser
import pytz
import re

# Get credentials from environment variables (for GitHub Actions)
# Fallback to placeholder values for local testing
TRMNL_API_KEY = os.getenv("TRMNL_API_KEY", "YOUR DEVELOPER API KEY HERE")
PLUGIN_UUID = os.getenv("PLUGIN_UUID", "YOUR PLUGIN ID HERE")
TRMNL_WEBHOOK_URL = f"https://usetrmnl.com/api/custom_plugins/{PLUGIN_UUID}"

TRACKED_NAMES = [
    "S&P (Oakland)", "USENIX Security", "CCS", "NDSS",
    "ACSAC", "RAID", "DIMVA", "Euro S&P",
    "SpaceSec", "ESORICS", "CPSS", "ASIACCS", "WiSec", "FUZZING", "DSN"
]

# Configuration options
CONFIG = {
    "max_days_ahead": 365,  # Don't show deadlines more than 1 year away
    "include_workshops": True,  # Set to False to exclude workshops
    "prioritize_top_tier": True,  # Show top tier conferences first
    "show_expired_days": 7,  # Show expired deadlines for X days (set to 0 to hide)
    "max_display_items": 15,  # Maximum conferences to show
}

# Conference ranking and categories for better display
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

# Default to AoE (UTC-12) if no timezone specified
DEFAULT_TZ = pytz.timezone("Etc/GMT+12")  # UTC-12 equivalent
TARGET_TZ = pytz.timezone("Europe/Berlin")

def get_urgency_info(deadline_dt, now_dt):
    """Calculate urgency level and friendly time remaining"""
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
    """Extract enhanced conference information"""
    description = conf.get('description', '')
    tags = conf.get('tags', [])
    
    # Determine conference type
    conf_type = "Conference"
    if "SHOP" in tags:
        conf_type = "Workshop"
    elif "CONF" in tags:
        conf_type = "Conference"
    
    # Extract venue/organization from description
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
            # If invalid timezone in data, fallback to AoE
            return DEFAULT_TZ
    else:
        # No timezone field, default to AoE
        return DEFAULT_TZ

def adjust_midnight(deadline_str):
    """
    If the deadline ends in :00 (e.g. 00:00, 10:00, etc.), 
    convert it to (hour-1):59:59. For example:
    - 2025-01-10 00:00 -> 2025-01-09 23:59:59
    - 2025-05-10 10:00 -> 2025-05-10 09:59:59
    """
    date_part, time_part = deadline_str.split()
    # time_part like HH:MM or HH:MM:SS
    # Ensure we have HH:MM format at least
    segments = time_part.split(":")
    if len(segments) == 2 and segments[1] == "00":
        # HH:00 case with no seconds
        hour = int(segments[0])
        if hour == 0:
            # midnight: go to previous day 23:59:59
            # We can parse date, subtract one day, then set time to 23:59:59
            dt_base = datetime.strptime(date_part, "%Y-%m-%d")
            dt_base -= timedelta(days=1)
            date_part = dt_base.strftime("%Y-%m-%d")
            time_part = "23:59:59"
        else:
            # Just hour-1:59:59 same day
            hour -= 1
            time_part = f"{hour:02d}:59:59"
    elif len(segments) == 3 and segments[2] == "00":
        # If we have seconds and it's :00, similar logic
        # This might be rare if deadlines are not given with seconds normally
        hour = int(segments[0])
        minute = int(segments[1])
        second = int(segments[2])
        if minute == 0 and second == 0:
            if hour == 0:
                # midnight with seconds
                dt_base = datetime.strptime(date_part, "%Y-%m-%d")
                dt_base -= timedelta(days=1)
                date_part = dt_base.strftime("%Y-%m-%d")
                time_part = "23:59:59"
            else:
                hour -= 1
                time_part = f"{hour:02d}:59:59"
    return f"{date_part} {time_part}"

def handle_placeholders(dl_str, conf_year):
    """
    Substitute %y with conference year and %Y with conference year - 1
    before parsing.
    """
    # Convert conference year to int
    conf_year_int = int(conf_year)
    dl_str = dl_str.replace("%y", str(conf_year_int))
    dl_str = dl_str.replace("%Y", str(conf_year_int - 1))
    return dl_str

def parse_deadline(dl_str, source_tz, conf_year):
    """
    Parse the deadline string:
    - Handle %y/%Y placeholders.
    - Adjust midnight if needed.
    - Add :59 seconds if only HH:MM given.
    """
    dl_str = handle_placeholders(dl_str, conf_year)
  
    # Check if we need to add :59 at the end if only HH:MM is present
    # The instructions mention if deadline hour is {h}:00, 
    # we should do {h-1}:59:59 which adjust_midnight handles.
    # Also, if no seconds are given and not exactly on :00, we can add :59 
    # if you want to replicate the site logic. 
    # For simplicity, let's first do midnight adjustment:
    if " " in dl_str:
        # if there's a time component
        dl_str = adjust_midnight(dl_str)
        # After this, if we still have no seconds and not :00, 
        # append ':59' for end of minute representation
        date_part, time_part = dl_str.split()
        if time_part.count(":") == 1:
            # means HH:MM
            # add :59
            dl_str = f"{date_part} {time_part}:59"
    else:
        # if there's no time at all, assume something like a full day?
        # The doc says deadlines are date+time, so this case might be rare.
        # You can decide on a default (like 23:59:59)
        dl_str = dl_str.strip() + " 23:59:59"

    # Now parse as naive datetime
    naive_dt = parser.parse(dl_str)
    # Localize to source timezone
    dt = source_tz.localize(naive_dt)
    return dt

def main():
    # Check if we have the required credentials
    if TRMNL_API_KEY == "YOUR DEVELOPER API KEY HERE" or PLUGIN_UUID == "YOUR PLUGIN ID HERE":
        print("❌ Error: TRMNL_API_KEY and PLUGIN_UUID must be set as environment variables")
        print("For local testing, set them manually in the script")
        return
    
    print("🔄 Starting TRMNL Security Deadlines update...")
    print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        return

    now_local = datetime.now(TARGET_TZ)
    filtered = []
    
    # Track some statistics
    total_processed = 0
    excluded_workshops = 0
    excluded_too_far = 0
  
    for conf in conferences_data:
        conf_name = conf.get('name')
        if conf_name in TRACKED_NAMES:
            total_processed += 1
            
            # Check if we should exclude workshops
            conf_info = extract_conference_info(conf)
            if not CONFIG["include_workshops"] and conf_info["type"] == "Workshop":
                excluded_workshops += 1
                continue
            
            deadlines = conf.get('deadline', [])
            if not deadlines:
                continue

            source_tz = get_conference_timezone(conf)
            conf_year = conf.get('year')  # needed for placeholders
            parsed_all = []
            for dl_str in deadlines:
                dt = parse_deadline(dl_str, source_tz, conf_year)
                dt_local = dt.astimezone(TARGET_TZ)
                parsed_all.append(dt_local)

            parsed_all.sort()
            
            # Filter deadlines based on config
            valid_deadlines = []
            for dl in parsed_all:
                days_diff = (dl - now_local).days
                
                # Include if within range or recently expired
                if days_diff >= -CONFIG["show_expired_days"] and days_diff <= CONFIG["max_days_ahead"]:
                    valid_deadlines.append(dl)
                elif days_diff > CONFIG["max_days_ahead"]:
                    excluded_too_far += 1
            
            if not valid_deadlines:
                continue
                
            # Get the next valid deadline (could be expired if within show_expired_days)
            future_deadlines = [d for d in valid_deadlines if d > now_local]
            next_dl = future_deadlines[0] if future_deadlines else valid_deadlines[-1]
            
            total_count = len(parsed_all)
            deadline_position = parsed_all.index(next_dl) + 1
            
            # Get enhanced conference info
            conf_info = extract_conference_info(conf)
            tier_info = CONFERENCE_TIERS.get(conf_name, {
                "tier": "OTHER", "category": "General", "rank": 99
            })
            urgency_info = get_urgency_info(next_dl, now_local)
            
            # Calculate days until deadline
            days_until = (next_dl - now_local).days
            
            # Format conference date nicely
            conf_date = conf.get('date', 'TBD')
            if conf_date and conf_date != 'TBD':
                # Clean up date format
                conf_date = re.sub(r'\s+', ' ', conf_date.strip())
            
            # Create short name for display
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
                
                # Enhanced metadata
                "tier": tier_info["tier"],
                "category": tier_info["category"],
                "rank": tier_info["rank"],
                "urgency": urgency_info,
                "venue": conf_info["venue"],
                "type": conf_info["type"],
                "description": conf_info["description"],
                
                # Additional deadline info
                "is_multi_deadline": total_count > 1,
                "comment": conf.get('comment', ''),
            }
            filtered.append(conf_record)

    # Smart sorting: prioritize urgent deadlines and top tier conferences
    if CONFIG["prioritize_top_tier"]:
        filtered.sort(key=lambda c: (
            0 if c["urgency"]["level"] in ["URGENT", "SOON"] else 1,  # Urgent first
            c["rank"],  # Then by rank
            parser.isoparse(c["next_deadline"])  # Then by deadline
        ))
    else:
        filtered.sort(key=lambda c: parser.isoparse(c["next_deadline"]))
    
    # Limit results
    filtered = filtered[:CONFIG["max_display_items"]]
    
    print(f"📊 Found {len(filtered)} conferences with upcoming deadlines")
    print(f"📈 Processed {total_processed} tracked conferences")
    if excluded_workshops > 0:
        print(f"🏗️  Excluded {excluded_workshops} workshops")
    if excluded_too_far > 0:
        print(f"📅 Excluded {excluded_too_far} deadlines too far in future")
    
    # Generate summary statistics
    urgent_count = len([c for c in filtered if c["urgency"]["level"] in ["URGENT", "SOON"]])
    top_tier_count = len([c for c in filtered if c["tier"] == "TOP4"])
    workshop_count = len([c for c in filtered if c["type"] == "Workshop"])
    expired_count = len([c for c in filtered if c["days_until"] < 0])
    
    # Find next most urgent deadline
    next_urgent = None
    if urgent_count > 0:
        urgent_confs = [c for c in filtered if c["urgency"]["level"] in ["URGENT", "SOON"]]
        urgent_confs.sort(key=lambda c: parser.isoparse(c["next_deadline"]))
        next_urgent = urgent_confs[0]

    payload = {
        "merge_variables": {
            "conferences": filtered,
            "stats": {
                "total_conferences": len(filtered),
                "urgent_count": urgent_count,
                "top_tier_count": top_tier_count,
                "workshop_count": workshop_count,
                "expired_count": expired_count,
                "next_urgent": next_urgent,
                "config": CONFIG  # Include config for template use
            },
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated_friendly": datetime.now().strftime("%b %d, %H:%M")
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TRMNL_API_KEY}"
    }

    try:
        print("📤 Sending data to TRMNL...")
        resp = requests.post(TRMNL_WEBHOOK_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            print("✅ Data sent successfully to TRMNL!")
            print("🖥️  Your TRMNL display will update on its next refresh cycle")
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Error sending to TRMNL: {e}")

if __name__ == "__main__":
    main()
