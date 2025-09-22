# TRMNL Security Conference Deadlines

This is an automated plugin for TRMNL that displays upcoming cybersecurity conference deadlines.

## Features

- **Automated Updates**: Updates every 3 hours using GitHub Actions
- **No Manual Work**: Set it up once, runs forever with automatic TRMNL refresh
- **Real-time Data**: Fetches from the official sec-deadlines repository
- **Smart Filtering**: Only shows conferences you care about

## Quick Setup (5 minutes)

### Step 1: Enable GitHub Pages

1. Go to your GitHub repository **Settings** 
2. Scroll down to **Pages** (left sidebar)
3. Under **Source**, select **Deploy from a branch**
4. Choose **gh-pages** branch and **/ (root)** folder
5. Click **Save**

### Step 2: Run GitHub Action

1. Go to the **Actions** tab in your repository
2. Click "Update TRMNL Security Deadlines"
3. Click **Run workflow** → **Run workflow**
4. Wait 2-3 minutes for it to complete 
5. Note the polling URL in the action output

### Step 3: Configure TRMNL Plugin

1. Go to your [TRMNL Plugin Settings](https://usetrmnl.com/plugin_settings)
2. Find your Security Deadlines plugin
3. **Change Strategy from "Webhook" to "Polling"**
4. Set **Polling URL** to: `https://[your-username].github.io/TRMNL-Sec-Deadlines/trmnl-data.json`
5. Set **Refresh Rate** to **30 minutes** (or your preference)
6. Save settings

### Step 4: Enjoy Automatic Updates! 

- **Every 3 hours**: GitHub generates fresh data
- **Every 30 minutes**: TRMNL checks for updates automatically  
- **No manual clicking**: TRMNL refreshes when data changes
- **Monitor via Actions**: See update logs in GitHub Actions tab

## Why This Works Better

### **Before (Webhook Strategy):**
GitHub Action sends data → TRMNL receives data → **Manual "Force Refresh" needed**

### **After (Polling Strategy):**
GitHub Action generates data → TRMNL polls data automatically → **Auto-refresh when data changes**

**Key Benefits:**
- **No more manual refreshing** - TRMNL checks automatically
- **Proper refresh scheduling** - Updates based on TRMNL's refresh intervals  
- **Lazy loading** - Only refreshes display when data actually changes
- **Reliable automation** - Uses TRMNL's built-in polling system

## 🔧 Customization

### Change Update Frequency

Edit `.github/workflows/update-trmnl.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  # or
  - cron: '0 9 * * *'    # Daily at 9 AM
  # or  
  - cron: '0 */3 * * *'  # Every 3 hours
```

### Add/Remove Conferences

Edit the `TRACKED_NAMES` list in `push_conferences.py`:

```python
TRACKED_NAMES = [
    "S&P (Oakland)", "USENIX Security", "CCS", "NDSS",
    "Your Conference Name Here"
]
```

## Troubleshooting

1. **Actions failing?** Check the logs in GitHub Actions tab
2. **No updates on TRMNL?** Verify your API key and Plugin UUID in secrets
3. **Wrong conferences?** Update the `TRACKED_NAMES` list
4. **Manual trigger**: Use "Run workflow" button in Actions tab

## Plugin Improvements

### **Enhanced Core Features**

**Smart Deadline Urgency**: Color-coded urgency levels (Urgent, Soon, Upcoming, Distant)  
**Conference Rankings**: TOP4, TIER1, TIER2, and Workshop classifications  
**Multi-Deadline Support**: Shows position (e.g., "2/3") for conferences with multiple deadlines  
**Enhanced Metadata**: Venue, type, location, and conference descriptions  
**Smart Filtering**: Configurable options for workshops, date ranges, and display limits  
**Statistics Dashboard**: Quick overview of urgent deadlines and top-tier conferences  

### **Visual Presentation Improvements**

**Highlighted Urgent Deadlines**: Next urgent deadline prominently displayed  
**Clean Information Hierarchy**: Title, urgency, venue, location in organized layout  
**Visual Urgency Indicators**: Badges and styling for different urgency levels  
**Conference Status Icons**: for TOP4 conferences, badges for urgent deadlines  
**Responsive Layout**: Optimized for TRMNL's e-ink display constraints  
**Smart Truncation**: Handles long conference names and locations gracefully  

### **Advanced Configuration**

Edit these settings in `push_conferences.py`:

```python
CONFIG = {
    "max_days_ahead": 365,      # Don't show deadlines > 1 year away
    "include_workshops": True,   # Set False to exclude workshops  
    "prioritize_top_tier": True, # Show top conferences first
    "show_expired_days": 7,     # Show expired deadlines for X days
    "max_display_items": 15,    # Maximum conferences to display
}
```

### **Data Enhancements**

Each conference now includes:
- **Urgency Analysis**: Real-time calculation of deadline urgency
- **Conference Tier**: TOP4, TIER1, TIER2, Workshop classification
- **Venue Information**: IEEE, ACM, USENIX organization details
- **Enhanced Dates**: Human-friendly formatting (e.g., "Dec 15, 23:59")
- **Progress Tracking**: Shows which deadline in sequence (2/3)
- **Location Details**: Cleaned and truncated location information

### **Template Files**

**`trmnl_template.html`** - Enhanced TRMNL template with:
- Prominent urgent deadline display
- Statistics overview (Total, Urgent, Top Tier)
- Clean conference list with urgency indicators
- Optimized for e-ink display readability

**Usage**: Copy the contents of `trmnl_template.html` into your TRMNL plugin's markup editor.

## 📊 Monitored Conferences

Currently tracking deadlines for:
- **TOP4**: S&P (Oakland), USENIX Security, CCS, NDSS
- **TIER1**: ACSAC, RAID, DIMVA, Euro S&P, ESORICS, ASIACCS, DSN  
- **Workshops**: SpaceSec, CPSS, WiSec, FUZZING

Data source: [sec-deadlines.github.io](https://sec-deadlines.github.io)