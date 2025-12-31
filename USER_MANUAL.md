# NGL User Manual

This guide covers day-to-day usage of the NGL LiveU Log Analyzer.

## 1) Accessing NGL

### Invite and account setup
- Admins create an invite using your email.
- Open the invite link and set your password.
- You will be logged in automatically.

### Sign in
- Go to the login page and enter your username and password.

## 2) Upload and Analyze Logs

1) Go to the Upload page.
2) Drag and drop a LiveU log archive (for example `.tar.bz2`) or click to browse.
3) Choose:
   - Parse mode (see list below)
   - Timezone
   - Optional date range (improves performance via archive pre-filtering)
4) Click **Analyze Log**.

## 3) Parse Modes (Common)

- `sessions`: Session summaries and duration analysis
- `md`: Modem statistics with charts
- `bw`: Stream bandwidth time series
- `md-bw`: Per-modem bandwidth with totals
- `memory`: Memory usage over time
- `grading`: Modem service level changes
- `known`, `error`, `v`, `all`: Log line filters

## 4) Viewing Results

Results have three tabs:

- Visualization: Charts, summary cards, and tables.
- Raw Output: Full text output with search and download.
- Errors: Any parsing errors or warnings.

## 5) Session Drill-Down

After running the `sessions` parser, you can run further parsers on a specific session. NGL automatically filters the archive to that session window for faster results.

## 6) Admin Functions (Admins Only)

### Invites
- Go to **Admin → Users → Invites**.
- Create invites by email (role and storage quota optional).
- Click **Regenerate Link** on active invites to create a new link.

### User management
- Go to **Admin → Users → Users**.
- Activate/deactivate accounts.
- Reset passwords.
- Change roles or delete users.

### Storage and SSL
- **Admin → S3** for storage settings and stats.
- **Admin → SSL** for HTTPS settings and certificates.

### Audit and Reports
- **Admin → Audit** for security and activity logs.
- **Admin → Reports** for usage and system statistics.

## 7) Troubleshooting

- If a link is expired, ask an admin to regenerate it.
- If uploads fail, verify archive format and file size.
- If the page appears stale, refresh the browser or clear cache.

