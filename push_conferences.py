import requests
import yaml
from datetime import datetime, timedelta
from dateutil import parser
import pytz

TRMNL_API_KEY = "YOUR DEVELOPER API KEY HERE"
PLUGIN_UUID = "YOUR PLUGIN ID HERE"
TRMNL_WEBHOOK_URL = f"https://usetrmnl.com/api/custom_plugins/{PLUGIN_UUID}"

TRACKED_NAMES = [
    "S&P (Oakland)", "USENIX Security", "CCS", "NDSS",
    "ACSAC", "RAID", "DIMVA", "Euro S&P",
    "SpaceSec", "ESORICS", "CPSS", "ASIACCS", "WiSec", "FUZZING", "DSN"
]

# Default to AoE (UTC-12) if no timezone specified
DEFAULT_TZ = pytz.timezone("Etc/GMT+12")  # UTC-12 equivalent
TARGET_TZ = pytz.timezone("Europe/Berlin")

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
    url = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/refs/heads/master/_data/conferences.yml"
    response = requests.get(url)
    response.raise_for_status()
    raw_yaml = response.text
    conferences_data = yaml.safe_load(raw_yaml)

    now_local = datetime.now(TARGET_TZ)
    filtered = []
  
    for conf in conferences_data:
        conf_name = conf.get('name')
        if conf_name in TRACKED_NAMES:
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
            future_deadlines = [d for d in parsed_all if d > now_local]

            if future_deadlines:
                next_dl = future_deadlines[0]
                total_count = len(parsed_all)
                deadline_position = parsed_all.index(next_dl) + 1

                conf_record = {
                    "name": conf_name,
                    "year": conf.get('year'),
                    "place": conf.get('place'),
                    "link": conf.get('link'),
                    "next_deadline": next_dl.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_deadlines": total_count,
                    "deadline_position": deadline_position
                }
                filtered.append(conf_record)

    filtered.sort(key=lambda c: parser.isoparse(c["next_deadline"]))

    payload = {
        "merge_variables": {
            "conferences": filtered,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TRMNL_API_KEY}"
    }

    print("Posting data to TRMNL webhook...")
    resp = requests.post(TRMNL_WEBHOOK_URL, json=payload, headers=headers)
    if resp.status_code == 200:
        print("Data sent successfully to TRMNL!")
    else:
        print(f"Error {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    main()
