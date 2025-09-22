# TRMNL Security Conference Deadlines

This is an automated plugin for TRMNL that displays upcoming cybersecurity conference deadlines.

## ✨ Features

- **Automated Updates**: Updates every 6 hours using GitHub Actions
- **No Manual Work**: Set it up once, runs forever
- **Real-time Data**: Fetches from the official sec-deadlines repository
- **Smart Filtering**: Only shows conferences you care about

## 🚀 Quick Setup (5 minutes)

### Step 1: Get Your TRMNL Credentials

1. Go to your [TRMNL Plugin Settings](https://usetrmnl.com/plugin_settings)
2. Find your existing Security Deadlines plugin
3. Copy these two values:
   - **API Key**: Your TRMNL developer API key
   - **Plugin UUID**: The unique ID for your plugin

### Step 2: Add Secrets to GitHub

1. Go to your GitHub repository page
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret** and add:
   - Name: `TRMNL_API_KEY` → Value: Your TRMNL API key
   - Name: `PLUGIN_UUID` → Value: Your plugin UUID

### Step 3: Enable GitHub Actions

1. Push your code to GitHub (if not already done)
2. Go to the **Actions** tab in your repository
3. You should see "Update TRMNL Security Deadlines" workflow
4. Click **Enable** if prompted

### Step 4: Test It

1. In the Actions tab, click "Update TRMNL Security Deadlines"
2. Click **Run workflow** → **Run workflow**
3. Wait 1-2 minutes and check if it succeeds ✅

## 🎯 What Happens Next

- **Automatic Updates**: Every 6 hours at 00:00, 06:00, 12:00, 18:00 UTC
- **No Maintenance**: Runs forever without your intervention  
- **Smart Caching**: TRMNL only updates display when data changes
- **Error Handling**: Logs any issues in GitHub Actions

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

## 🐛 Troubleshooting

1. **Actions failing?** Check the logs in GitHub Actions tab
2. **No updates on TRMNL?** Verify your API key and Plugin UUID in secrets
3. **Wrong conferences?** Update the `TRACKED_NAMES` list
4. **Manual trigger**: Use "Run workflow" button in Actions tab

## 🎨 Plugin Improvements

### **Enhanced Core Features**

✅ **Smart Deadline Urgency**: Color-coded urgency levels (Urgent, Soon, Upcoming, Distant)  
✅ **Conference Rankings**: TOP4, TIER1, TIER2, and Workshop classifications  
✅ **Multi-Deadline Support**: Shows position (e.g., "2/3") for conferences with multiple deadlines  
✅ **Enhanced Metadata**: Venue, type, location, and conference descriptions  
✅ **Smart Filtering**: Configurable options for workshops, date ranges, and display limits  
✅ **Statistics Dashboard**: Quick overview of urgent deadlines and top-tier conferences  

### **Visual Presentation Improvements**

✅ **Highlighted Urgent Deadlines**: Next urgent deadline prominently displayed  
✅ **Clean Information Hierarchy**: Title, urgency, venue, location in organized layout  
✅ **Visual Urgency Indicators**: Badges and styling for different urgency levels  
✅ **Conference Status Icons**: ⭐ for TOP4 conferences, badges for urgent deadlines  
✅ **Responsive Layout**: Optimized for TRMNL's e-ink display constraints  
✅ **Smart Truncation**: Handles long conference names and locations gracefully  

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
