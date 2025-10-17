# NGL User Manual
## Next Generation LiveU Log Analyzer - Complete Guide

**Version:** 4.0.0
**Last Updated:** October 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [User Interface Overview](#user-interface-overview)
4. [Logging In](#logging-in)
5. [Uploading and Analyzing Log Files](#uploading-and-analyzing-log-files)
6. [Understanding Parse Modes](#understanding-parse-modes)
7. [Interpreting Results](#interpreting-results)
8. [Analysis History](#analysis-history)
9. [Admin Dashboard](#admin-dashboard)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Security and Privacy](#security-and-privacy)
13. [FAQs](#faqs)

---

## Introduction

### What is NGL?

NGL (Next Gen LULA) is a modern web-based application designed to analyze LiveU device log files. It provides powerful visualization capabilities and interactive charts to help you understand device performance, troubleshoot issues, and optimize streaming operations.

### Key Features

- **19+ Analysis Modes**: From error analysis to bandwidth monitoring
- **Interactive Visualizations**: Charts, graphs, and tables for easy interpretation
- **Session Tracking**: Track streaming sessions with automatic duration calculation
- **User Management**: Secure authentication with role-based access control
- **Analysis History**: Access all your past analyses anytime
- **Auto-Cleanup**: Automatic file management with configurable retention
- **Admin Tools**: Comprehensive dashboard for system management

### Who Should Use NGL?

- **Field Engineers**: Troubleshoot device issues in the field
- **Technical Support**: Analyze customer log files for support cases
- **Operations Teams**: Monitor device performance and bandwidth usage
- **System Administrators**: Manage users and system resources

---

## Getting Started

### System Requirements

**For Users:**
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection to access the NGL server
- Valid user account credentials

**For Administrators:**
- Docker and Docker Compose installed
- 4GB+ RAM available
- 20GB+ disk space

### Accessing NGL

1. Open your web browser
2. Navigate to your NGL server URL (e.g., `http://your-server:3000`)
3. You'll be directed to the login page

### First-Time Login

**Default Admin Credentials:**
- Username: `admin`
- Password: `Admin123!`

**⚠️ IMPORTANT:** Change the default admin password immediately after first login!

To change password:
1. Log in as admin
2. Click your username in the top-right corner
3. Select "Change Password"
4. Enter current and new password
5. Click "Update Password"

---

## User Interface Overview

### Main Navigation

The NGL interface consists of several main sections:

1. **Upload Page** (Home): Primary interface for uploading and analyzing log files
2. **Analysis History**: View all your past analyses
3. **Admin Dashboard**: System management (admin users only)
4. **User Menu**: Access settings, change password, and logout

### Activity Timeout

For security, NGL automatically logs you out after **10 minutes of inactivity**. Activity includes:
- Mouse movements
- Keyboard input
- Scrolling
- Touch interactions

A warning will appear 1 minute before automatic logout.

---

## Logging In

### Standard Login Process

1. Navigate to the NGL login page
2. Enter your **username** (not email)
3. Enter your **password**
4. Click "Sign In"

### Password Requirements

Passwords must meet these criteria:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

Example valid passwords: `Support2024!`, `Engineer12345`, `LiveU2025Pass`

### Troubleshooting Login Issues

**"Invalid credentials" error:**
- Verify username (not email)
- Check caps lock is off
- Ensure correct password

**Account locked or disabled:**
- Contact your administrator
- Admin can reactivate accounts in Admin Dashboard → Users tab

---

## Uploading and Analyzing Log Files

### Step-by-Step Upload Process

#### 1. Select Your Log File

Click the **"Choose File"** button or drag-and-drop your log file into the upload area.

**Supported File Types:**
- `.tar.gz` - Compressed archives (most common)
- `.tgz` - Compressed archives
- `.tar` - Uncompressed archives
- `.zip` - ZIP archives
- `.log` - Individual log files

**File Size Limits:**
- Maximum: 500MB per file
- Check your storage quota in the upload page header

#### 2. Select Parse Mode(s)

Choose one or more analysis modes from the dropdown:

**Quick Analysis (Recommended for First-Time Users):**
- `known` - Known errors only
- `sessions` - Streaming sessions
- `bw` - Bandwidth analysis

**Advanced Analysis:**
- `all` - All errors (detailed)
- `md` - Modem statistics
- `memory` - Memory usage
- `grading` - Modem grading/quality

**Pro Tip:** You can select multiple parse modes in a single upload to get comprehensive analysis!

#### 3. Configure Analysis Settings

**Timezone Selection:**
- Choose the timezone where the device was operating
- Affects timestamp interpretation
- Default: UTC
- Common options: PST, EST, GMT, Local

**Date Range (Optional):**
- Filter logs to specific time period
- Format: YYYY-MM-DD HH:MM
- Leave blank to analyze entire log file
- Useful for large files to focus on specific incidents

**Session Name (Optional but Recommended):**
- Give your analysis a memorable name
- Example: "LA Stadium - Audio Drop Issue"
- Helps identify analyses in history

**Zendesk Case Number (Optional):**
- Link analysis to support ticket
- Example: "12345"
- Searchable in analysis history

#### 4. Upload and Process

1. Click **"Upload and Parse"**
2. File uploads to server (progress bar shown)
3. Analysis begins automatically
4. Progress indicators show parsing status
5. Results appear when complete (typically 30 seconds to 2 minutes)

**During Processing:**
- Progress bars show completion for each parse mode
- You can navigate away and return - progress is preserved
- Don't close browser tab if you want real-time updates

---

## Understanding Parse Modes

NGL offers 19+ specialized parse modes. Here's what each one does:

### Error Analysis Modes

#### `known` - Known Errors
**Purpose:** Detects common, well-documented errors
**Best For:** Quick health check, first-pass analysis
**Output:** List of known error patterns with timestamps
**When to Use:** Initial troubleshooting, routine checks

#### `error` - Error Messages
**Purpose:** Extracts all error-level log messages
**Best For:** Finding issues not in known patterns
**Output:** All lines containing "error" keywords
**When to Use:** When `known` doesn't reveal issues

#### `v` - Verbose Errors
**Purpose:** Includes warnings and verbose error messages
**Best For:** Deep-dive troubleshooting
**Output:** Errors, warnings, and debug messages
**When to Use:** Complex issues requiring detailed context

#### `all` - All Errors
**Purpose:** Most comprehensive error analysis
**Best For:** Complete error audit
**Output:** Every error, warning, and info message
**When to Use:** Root cause analysis, compliance audits

### Bandwidth Analysis Modes

#### `bw` - Stream Bandwidth
**Purpose:** Analyzes streaming bandwidth over time
**Best For:** Understanding data throughput
**Output:** Interactive time-series chart with bandwidth metrics
**When to Use:** Investigating buffering, quality issues

**Visualization Features:**
- Time-series area chart
- Per-modem breakdown
- Aggregate total bandwidth
- Tooltip shows exact values

#### `md-bw` - Modem Bandwidth
**Purpose:** Per-modem bandwidth analysis
**Best For:** Identifying problematic modems
**Output:** Individual modem bandwidth charts
**When to Use:** Modem comparison, load balancing analysis

#### `md-db-bw` - Data Bridge Bandwidth
**Purpose:** Data bridge bandwidth statistics
**Best For:** Backhaul analysis
**Output:** Data bridge throughput metrics
**When to Use:** Network infrastructure troubleshooting

### Modem Analysis Modes

#### `md` - Modem Statistics
**Purpose:** Comprehensive modem performance metrics
**Best For:** Modem health assessment
**Output:** Signal strength, throughput, packet loss, latency
**When to Use:** Connection quality issues, modem problems

**Key Metrics:**
- **Signal Strength (RSSI)**: Radio signal quality
- **Throughput**: Actual data rate achieved
- **Packet Loss**: Percentage of lost packets
- **Latency**: Round-trip time
- **Connection Type**: 4G, 5G, LTE, etc.

**Visualization:**
- Bar charts for comparison
- Line graphs for trends
- Sortable tables for detailed data

#### `grading` - Modem Grading
**Purpose:** Quality scoring over time
**Best For:** Service level analysis
**Output:** Timeline of modem quality grades (A, B, C, D, F)
**When to Use:** SLA compliance, quality trends

**Grade Meanings:**
- **A**: Excellent (>90% quality)
- **B**: Good (75-90%)
- **C**: Fair (60-75%)
- **D**: Poor (50-60%)
- **F**: Failing (<50%)

### Session Analysis Modes

#### `sessions` - Streaming Sessions
**Purpose:** Tracks streaming sessions with start/end times
**Best For:** Session history, duration analysis
**Output:** Table with session details
**When to Use:** Investigating specific streams, billing

**Session Information:**
- Start and end timestamps
- Duration (calculated automatically)
- Session ID
- Status (Complete/Incomplete)
- Server information

**Pro Tip:** Filter by date range to find specific sessions quickly!

### System Metrics Modes

#### `memory` - Memory Usage
**Purpose:** Tracks memory consumption over time
**Best For:** Memory leak detection
**Output:** Time-series chart by component
**When to Use:** Performance degradation, crashes

**Components Tracked:**
- VIC (Video Input Card)
- Corecard
- Server processes
- Total system memory

#### `cpu` - CPU Usage
**Purpose:** CPU utilization analysis
**Best For:** Performance bottleneck identification
**Output:** Multi-core CPU visualization
**When to Use:** High load investigation

### Device Information Modes

#### `id` - Device/Server IDs
**Purpose:** Extracts device and server identifiers
**Best For:** Device identification, inventory
**Output:** Device ID, server ID, firmware version
**When to Use:** Device tracking, version verification

---

## Interpreting Results

### Result Types

NGL presents results in several formats:

#### 1. Interactive Charts

**Bandwidth Charts:**
- Hover over points to see exact values
- Click legend items to show/hide series
- Zoom in on specific time ranges
- Compare multiple modems visually

**Tips for Reading Bandwidth Charts:**
- Look for drops (service interruptions)
- Check consistency (stable vs. fluctuating)
- Compare modems (load distribution)
- Note time patterns (peak usage times)

**Modem Statistics Charts:**
- Bar charts for metric comparison
- Line charts for time-series trends
- Color coding for severity (red = poor, green = good)

#### 2. Data Tables

**Sessions Table:**
- Sortable columns (click headers)
- Filterable by status
- Chronologically ordered
- Duration auto-calculated

**Modem Tables:**
- Sortable by any metric
- Color-coded values
- Expandable details

#### 3. Raw Output

- Original parser output
- Downloadable for external analysis
- Searchable with Ctrl+F
- Copy-paste friendly

### Common Patterns to Recognize

#### Error Analysis

**High Error Count:**
- >100 errors/hour: Serious issue
- 10-100 errors/hour: Moderate concern
- <10 errors/hour: Normal operation

**Error Clustering:**
- Errors at same timestamp: System event
- Periodic errors: Configuration issue
- Random errors: Environmental factors

#### Bandwidth Analysis

**Healthy Bandwidth:**
- Smooth, consistent line
- Gradual changes
- All modems contributing

**Problematic Patterns:**
- Frequent drops to zero: Connection loss
- Sawtooth pattern: Retry loops
- Single modem carrying load: Bonding issue

#### Modem Statistics

**Good Modem:**
- Signal strength: -60 to -80 dBm
- Packet loss: <1%
- Latency: <100ms
- Consistent throughput

**Bad Modem:**
- Signal strength: <-100 dBm
- Packet loss: >5%
- Latency: >200ms
- Erratic throughput

---

## Analysis History

### Accessing Your History

1. Click **"Analysis History"** in the navigation menu
2. View all your past analyses
3. Filter by date, session name, or status

### History Features

**Information Displayed:**
- Session name (if provided)
- Parse modes used
- Upload date and time
- File name
- Analysis status
- Zendesk case number (if provided)

**Actions Available:**
- **View Results**: Re-open any past analysis
- **Download Raw**: Export raw parser output
- **Delete**: Remove analysis (cannot be undone)

### Status Indicators

- **Completed**: Analysis finished successfully
- **Running**: Currently processing
- **Pending**: Queued for processing
- **Failed**: Error occurred during analysis

### Search and Filter

**Search by:**
- Session name
- File name
- Zendesk case number
- Date range

**Filter by:**
- Parse modes used
- Status
- Upload date

### Storage Management

**Check Your Quota:**
- Current usage shown in upload page header
- Default limit: 10GB per user (100GB for admins)

**Free Up Space:**
- Delete old analyses from history
- Remove duplicate uploads
- Contact admin to increase quota

---

## Admin Dashboard

*This section is for users with Administrator role only.*

### Accessing Admin Dashboard

1. Log in with admin credentials
2. Click **"Admin Dashboard"** in navigation
3. Three tabs available: Statistics, Users, Parsers

### Statistics Tab

**System Overview:**
- Total users registered
- Total files uploaded
- Total analyses completed
- Total storage used

**Quick Stats:**
- Active users (last 30 days)
- Today's uploads
- Failed analyses (requires attention)
- Average analysis time

### Users Tab

**View All Users:**
- Username, email, role
- Storage quota and usage
- Account status (active/inactive)
- Registration date

**User Management Actions:**

#### Create New User
1. Click **"Add User"** button
2. Enter username, email, password
3. Select role (User or Admin)
4. Set storage quota
5. Click "Create"

**Note:** Public registration is disabled by default for security.

#### Edit User
1. Click **"Edit"** next to user
2. Modify role, quota, or status
3. Click "Save Changes"

**Common Edits:**
- Promote user to admin
- Increase storage quota
- Deactivate account (temporarily disable)
- Reactivate account

#### Delete User
1. Click **"Delete"** next to user
2. Confirm deletion
3. All user's files and analyses are also deleted

**⚠️ Warning:** User deletion is permanent and cannot be undone!

### Parsers Tab

**Control Parser Availability:**
- Enable/disable parsers globally
- Control which users can access specific parsers
- Useful for:
  - Disabling broken parsers
  - Restricting advanced parsers to power users
  - Beta testing new parsers

**Parser Permissions:**
1. Select parser from list
2. Toggle "Available" status
3. Grant/revoke per-user access
4. Changes apply immediately

---

## Best Practices

### File Upload Best Practices

#### 1. Use Descriptive Session Names

**Bad:**
```
test
file1
log
```

**Good:**
```
LA_Stadium_Game_Night_Audio_Drop
Denver_Office_5G_Modem_Issue_Case_54321
NYC_Marathon_Bandwidth_Analysis
```

**Benefits:**
- Easy to find in history
- Team members understand context
- Professional documentation

#### 2. Always Include Zendesk Case Numbers

Link every analysis to support tickets for:
- Complete audit trail
- Quick case reference
- Billing and reporting

#### 3. Select Appropriate Parse Modes

**For Routine Checks:**
- `known`, `sessions`, `bw`

**For Troubleshooting:**
- `known`, `error`, `md`, `bw`

**For Deep Analysis:**
- `all`, `v`, `md`, `grading`, `memory`, `sessions`

**Don't Over-Parse:**
- Running `all` on 10GB files is slow
- Use date ranges to limit scope
- Start with `known`, escalate if needed

#### 4. Use Date Ranges Effectively

**Large Files (>100MB):**
- Always use date ranges
- Focus on incident time window
- Reduces processing time by 10x

**Example:**
- Incident occurred: 2025-01-15 14:30-15:00
- Date range: 2025-01-15 14:00 to 2025-01-15 16:00
- Includes buffer for context

#### 5. Set Correct Timezone

**Why It Matters:**
- Timestamps must match local time
- Correlate with external events
- Accurate session duration

**How to Choose:**
- Use device deployment location
- Not your current location
- When in doubt, ask customer

### Analysis Workflow Best Practices

#### Standard Troubleshooting Workflow

**Step 1: Quick Assessment (5 minutes)**
```
Parse modes: known, sessions
Goal: Identify if there are obvious issues
Action: If errors found, proceed to Step 2
```

**Step 2: Error Deep Dive (10 minutes)**
```
Parse modes: error, v
Goal: Understand error patterns and frequency
Action: Note error types and timestamps
```

**Step 3: System Metrics (15 minutes)**
```
Parse modes: md, bw, grading
Goal: Correlate errors with performance metrics
Action: Look for degradation before errors
```

**Step 4: Comprehensive Analysis (30 minutes)**
```
Parse modes: all, memory, cpu
Goal: Root cause identification
Action: Create detailed report
```

#### Bandwidth Investigation Workflow

**1. Overall Throughput:**
```
Parse mode: bw
Look for: Drops, fluctuations, trends
```

**2. Modem Contribution:**
```
Parse mode: md-bw
Look for: Uneven distribution, modem failures
```

**3. Modem Health:**
```
Parse mode: md
Look for: Signal issues, packet loss, latency
```

**4. Quality Trends:**
```
Parse mode: grading
Look for: Quality degradation over time
```

### Storage Management Best Practices

#### For Regular Users

**Monitor Your Quota:**
- Check header on upload page
- Plan for large files
- Delete old analyses regularly

**When to Delete:**
- Duplicate uploads
- Test analyses
- Analyses older than 90 days (if not needed)

**When to Keep:**
- Customer-facing analyses
- Reference cases
- Ongoing investigations

#### For Administrators

**Set Appropriate Quotas:**
- Field engineers: 10GB
- Support team: 25GB
- Power users: 50GB
- Admins: 100GB

**Monitor System Storage:**
- Check Statistics tab weekly
- Identify users near quota
- Purge old files from deleted users

**Retention Policy:**
- Default: 30 days auto-delete
- Configure in environment variables
- Pinned files are exempt

### Security Best Practices

#### Password Management

**Strong Passwords:**
- Use password manager
- Minimum 12 characters (required by system)
- Mix letters, numbers, symbols
- Don't reuse passwords

**Change Passwords:**
- Immediately after first login (admins)
- Every 90 days (recommended)
- After suspected compromise

#### Session Management

**Logout When Done:**
- Especially on shared computers
- Don't rely on auto-timeout
- Click "Logout" in user menu

**Shared Devices:**
- Never save passwords in browser
- Use private/incognito mode
- Clear browser data after use

#### File Handling

**Sensitive Logs:**
- Don't upload customer logs to public instances
- Verify server security before upload
- Delete immediately after analysis if sensitive

**Data Privacy:**
- Logs may contain device IDs, locations
- Follow company data handling policies
- Use session names carefully (no PII)

### Team Collaboration Best Practices

#### Naming Conventions

**Session Names Format:**
```
[Location]_[Event]_[Issue]_[Optional:CaseNumber]

Examples:
Boston_Concert_Modem4_Dropout_Case12345
Miami_Sports_Bandwidth_Test
Seattle_Office_5G_Performance_Baseline
```

**Benefits:**
- Everyone uses same format
- Easy searching
- Professional documentation

#### Documentation Standards

**After Analysis, Document:**
1. Session name and case number
2. Parse modes used
3. Key findings
4. Actions taken
5. Follow-up required

**Share Results:**
- Export raw output for reports
- Screenshot charts for presentations
- Reference history URL for team access

#### Knowledge Sharing

**Create Internal Wiki:**
- Common error patterns
- Parse mode selection guide
- Interpretation guidelines
- Case studies

**Training New Users:**
- Start with `known` and `sessions`
- Practice on non-critical files
- Review analysis history together
- Escalate complex cases

---

## Troubleshooting

### Login Issues

#### Cannot Login - "Invalid Credentials"

**Cause:** Incorrect username or password

**Solutions:**
1. Verify username (not email)
2. Check caps lock
3. Try password reset
4. Contact admin if account locked

#### Automatic Logout Too Frequent

**Cause:** 10-minute inactivity timeout

**Solutions:**
1. Move mouse periodically
2. Disable screensaver during analysis
3. Request admin to extend timeout (requires code change)

### Upload Issues

#### Upload Fails - "File Too Large"

**Cause:** File exceeds 500MB limit

**Solutions:**
1. Use date range to extract smaller portion
2. Split log file before upload
3. Contact admin to increase limit

#### Upload Fails - "Quota Exceeded"

**Cause:** Storage quota reached

**Solutions:**
1. Delete old analyses from history
2. Remove duplicate uploads
3. Contact admin to increase quota

#### Upload Succeeds but No Results

**Cause:** Analysis may still be running

**Solutions:**
1. Check Analysis History for status
2. Wait 5-10 minutes for large files
3. Refresh page
4. Check for "Failed" status - contact admin if failed

### Analysis Issues

#### Analysis Stuck at "Pending" or "Running"

**Cause:** Queue backlog or processing error

**Solutions:**
1. Wait 10 minutes (queue may be busy)
2. Check Analysis History for updates
3. Try smaller date range
4. Contact admin if stuck >30 minutes

#### Analysis Status "Failed"

**Cause:** Parser error, corrupt log, or system issue

**Solutions:**
1. Check if file is valid log archive
2. Try different parse mode
3. Use smaller date range
4. Contact admin with analysis ID

#### No Data in Results

**Cause:** Date range too narrow or logs don't contain requested data

**Solutions:**
1. Expand date range
2. Verify log file contains expected data
3. Try different parse mode
4. Check timezone setting

### Visualization Issues

#### Charts Not Displaying

**Cause:** Browser compatibility or data format issue

**Solutions:**
1. Refresh page (Ctrl+F5)
2. Try different browser (Chrome recommended)
3. Clear browser cache
4. Check browser console for errors (F12)

#### Chart Data Looks Wrong

**Cause:** Timezone mismatch or data parsing issue

**Solutions:**
1. Verify timezone setting matches log origin
2. Check date range includes incident time
3. Compare with raw output tab
4. Try re-uploading with correct settings

### Performance Issues

#### Slow Upload

**Cause:** Large file size or network speed

**Solutions:**
1. Check network connection
2. Use wired connection instead of WiFi
3. Compress file further if possible
4. Upload during off-peak hours

#### Slow Analysis

**Cause:** Large file or complex parse modes

**Solutions:**
1. Use date range to limit scope
2. Avoid `all` mode on large files
3. Select fewer parse modes
4. Contact admin about system resources

---

## Security and Privacy

### Data Security

**How NGL Protects Your Data:**

1. **Authentication:** JWT token-based, secure sessions
2. **Encryption:** HTTPS in production (configure SSL)
3. **Access Control:** Role-based permissions
4. **Audit Logging:** All actions tracked
5. **Auto-Cleanup:** Files deleted after retention period

### Privacy Considerations

**What Data Is Stored:**
- Uploaded log files (encrypted at rest)
- Analysis results (database)
- User credentials (hashed passwords)
- Audit logs (user actions)

**What Data Is NOT Stored:**
- Passwords (only bcrypt hashes)
- Session tokens (JWT, client-side only)
- Deleted files (permanently removed after grace period)

**Data Retention:**
- Log files: 30 days default (configurable)
- Soft-deleted files: 90-day grace period
- Analysis results: Permanent (until manually deleted)
- Audit logs: Permanent

### Compliance

**GDPR Considerations:**
- User data export: Contact admin
- Right to deletion: Admin can remove user and all data
- Data processing: Logs for legitimate technical support

**Best Practices for Compliance:**
- Only upload logs necessary for analysis
- Delete analyses when investigation complete
- Don't include PII in session names
- Follow organizational data policies

---

## FAQs

### General Questions

**Q: How long does analysis take?**
A: Typically 30 seconds to 2 minutes, depending on file size and parse modes. Large files (>100MB) with `all` mode may take 5-10 minutes.

**Q: Can I analyze multiple files at once?**
A: Not in a single upload. Upload files one at a time, but you can select multiple parse modes per file.

**Q: How many parse modes can I select?**
A: As many as available. However, more modes = longer processing time.

**Q: What file formats are supported?**
A: `.tar.gz`, `.tgz`, `.tar`, `.zip`, `.log`

**Q: Is there a mobile app?**
A: No, but NGL works in mobile browsers. Desktop recommended for best experience.

### Account Questions

**Q: How do I reset my password?**
A: Currently requires admin assistance. Password reset flow not yet implemented. Contact your administrator.

**Q: Can I have multiple accounts?**
A: No, one account per user. Contact admin if you need a new account.

**Q: How do I increase my storage quota?**
A: Contact your administrator. They can adjust quotas in Admin Dashboard → Users tab.

### File and Analysis Questions

**Q: Why can't I see certain parse modes?**
A: Admins control parser availability and permissions. Contact admin to request access.

**Q: Can I re-run an analysis with different settings?**
A: Yes, upload the same file again with new parse modes or date range.

**Q: How do I download results?**
A: Use the "Raw Output" tab and copy/paste, or take screenshots of charts.

**Q: What happens to my files after upload?**
A: Stored for 30 days (default), then auto-deleted unless pinned by admin.

**Q: Can I share my analysis with others?**
A: Not directly. Export results manually and share screenshots/raw output.

### Technical Questions

**Q: What timezone should I use?**
A: The timezone where the LiveU device was operating, not your current location.

**Q: Why are session durations showing wrong?**
A: Check timezone setting. Incorrect timezone causes timestamp misinterpretation.

**Q: What's the difference between `error` and `known`?**
A: `known` = documented error patterns (faster, focused). `error` = all error messages (comprehensive, slower).

**Q: Can I upload files from older LiveU firmware?**
A: Yes, parser supports multiple firmware versions. If issues occur, contact support.

**Q: Why is my bandwidth chart empty?**
A: Log file may not contain bandwidth data, or date range excludes streaming periods.

---

## Getting Help

### Support Resources

**Documentation:**
- User Manual (this document)
- README.md - Feature overview
- TROUBLESHOOTING.md - Common issues

**Contact Support:**
- System Administrator (for account issues)
- Technical Support (for analysis questions)
- DevOps Team (for system errors)

### Reporting Issues

**Include This Information:**
1. Username
2. Analysis ID (from history)
3. Error message (exact text)
4. Steps to reproduce
5. Browser and version
6. Screenshot if applicable

### Feature Requests

Contact your administrator with:
- Detailed description of feature
- Use case / business justification
- Priority level

---

## Appendix

### Parse Mode Quick Reference

| Mode | Category | Speed | Output Type | Best For |
|------|----------|-------|-------------|----------|
| `known` | Error | Fast | List | Quick checks |
| `error` | Error | Medium | List | General troubleshooting |
| `v` | Error | Slow | List | Deep debugging |
| `all` | Error | Slowest | List | Comprehensive audit |
| `bw` | Bandwidth | Fast | Chart | Stream performance |
| `md-bw` | Bandwidth | Fast | Chart | Modem comparison |
| `md-db-bw` | Bandwidth | Fast | Chart | Data bridge analysis |
| `md` | Modem | Medium | Chart+Table | Modem health |
| `grading` | Modem | Medium | Chart | Quality trends |
| `sessions` | Session | Fast | Table | Session tracking |
| `memory` | System | Medium | Chart | Memory analysis |
| `cpu` | System | Medium | Chart | CPU analysis |
| `id` | Info | Fast | Text | Device identification |

### Glossary

**Terms:**

- **Analysis**: A processing job that runs parser(s) on a log file
- **Archive**: Compressed file containing multiple log files (tar.gz, zip)
- **Audit Log**: Record of all user actions in the system
- **Bandwidth**: Data throughput (usually Mbps or Kbps)
- **Bonding**: Combining multiple modems for aggregate bandwidth
- **Grace Period**: 90 days before soft-deleted files are permanently removed
- **JWT**: JSON Web Token, used for authentication
- **Modem**: Cellular connection module (4G, 5G, LTE)
- **Parse Mode**: Type of analysis to perform on log file
- **Pinned File**: File exempt from auto-deletion
- **Quota**: Storage limit per user
- **Retention Period**: How long files are kept before auto-deletion (30 days default)
- **Session**: Streaming session with start/end time
- **Soft Delete**: Marked for deletion but recoverable during grace period
- **Hard Delete**: Permanent, unrecoverable deletion
- **Timezone**: Geographic time zone affecting timestamp interpretation

### Keyboard Shortcuts

**Browser Shortcuts:**
- `Ctrl+F` / `Cmd+F`: Search in raw output
- `F5`: Refresh page
- `Ctrl+F5` / `Cmd+Shift+R`: Hard refresh (clear cache)
- `F12`: Open browser developer tools (for debugging)

---

## Changelog

**Version 4.0.0 (October 2025):**
- Added complete database system
- Implemented JWT authentication
- Added user management & admin dashboard
- Implemented file lifecycle management
- Added analysis history tracking

**Version 3.0.0 (October 2025):**
- Refactored to modular parser architecture
- All parsers use LulaWrapperParser pattern

---

**For additional assistance, contact your system administrator.**

---

*End of User Manual*
