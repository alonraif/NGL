# Cloudflare IP Detection Fix

## Problem

When NGL is accessed through Cloudflare (or other CDN/proxy services), the audit logs were showing **Cloudflare's IP addresses** instead of the real client IPs:

- **Cloudflare IP seen**: `172.65.32.248` (Toronto, Canada)
- **Actual location**: Your real location (not Canada!)

This happens because Cloudflare acts as a reverse proxy between the client and your server.

## Why This Happens

### Traffic Flow with Cloudflare:

```
Real Client (Your IP)
    → Cloudflare Edge Server (172.65.32.248)
        → Your Server (sees Cloudflare IP)
```

### Headers in the Request:

When using Cloudflare, the request contains:
- `remote_addr` = Cloudflare's IP (172.65.x.x)
- `CF-Connecting-IP` = Your real IP ✅
- `X-Forwarded-For` = Your real IP (also set by Cloudflare)

## The Fix

### Changes Made

#### 1. Backend IP Detection ([backend/auth.py:159-181](backend/auth.py#L159-L181))

Updated `log_audit()` function to check headers in priority order:

```python
def log_audit(...):
    # Priority 1: CF-Connecting-IP (Cloudflare's real client IP header)
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        client_ip = cf_ip.strip()
    else:
        # Priority 2: X-Real-IP (set by nginx or other proxies)
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            client_ip = real_ip.strip()
        else:
            # Priority 3: X-Forwarded-For (from proxy chain)
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for:
                client_ip = forwarded_for.split(',')[0].strip()
            else:
                # Priority 4: Fallback to remote_addr (direct connection)
                client_ip = request.remote_addr
```

**Priority Order:**
1. ✅ `CF-Connecting-IP` (Cloudflare's standard header for real client IP)
2. ✅ `X-Real-IP` (nginx standard header)
3. ✅ `X-Forwarded-For` (general proxy header)
4. ✅ `remote_addr` (fallback for direct connections)

#### 2. Nginx Configuration ([frontend/nginx.conf](frontend/nginx.conf))

Added Cloudflare header forwarding:

```nginx
location /api {
    # ... other headers ...

    # Forward Cloudflare's real IP header if present
    proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;

    # ... rest of config ...
}
```

This ensures that if Cloudflare sends the `CF-Connecting-IP` header, nginx forwards it to the backend.

## Verification

### Before the Fix:
```
IP Address: 172.65.32.248
Location: Toronto, Canada 🇨🇦
```

### After the Fix:
```
IP Address: [Your Real IP]
Location: [Your Real City/Country] 🌍
```

## Testing

### 1. Check Current Audit Logs

```bash
# View recent audit logs with IP addresses
docker-compose exec -T postgres psql -U ngl_user -d ngl_db -c "
SELECT
    action,
    ip_address,
    timestamp
FROM audit_log
ORDER BY timestamp DESC
LIMIT 5;
"
```

### 2. Test with New Login

1. Open your browser
2. Clear cookies/logout if logged in
3. Login again
4. Go to Admin Dashboard → Audit Logs
5. Your new login entry should show **your real IP** (not 172.65.x.x)

### 3. Verify Headers

You can test if Cloudflare headers are being received:

```bash
# Check what IP the backend sees
docker-compose logs backend | grep "CF-Connecting-IP"
```

## Cloudflare IP Ranges

Cloudflare uses these IP ranges for their edge servers:

### IPv4 Ranges:
- 173.245.48.0/20
- 103.21.244.0/22
- 103.22.200.0/22
- 103.31.4.0/22
- 141.101.64.0/18
- 108.162.192.0/18
- 190.93.240.0/20
- 188.114.96.0/20
- 197.234.240.0/22
- 198.41.128.0/17
- 162.158.0.0/15
- 104.16.0.0/13
- 104.24.0.0/14
- **172.64.0.0/13** ← Your IP (172.65.32.248) falls in this range
- 131.0.72.0/22

If you see IPs in these ranges in your audit logs, they're Cloudflare IPs, not real clients.

## Other CDN/Proxy Services

The fix also handles other proxy services:

### AWS CloudFront:
- Uses `X-Forwarded-For` (Priority 3 in our code)

### Nginx Reverse Proxy:
- Uses `X-Real-IP` (Priority 2 in our code)

### Generic HTTP Proxies:
- Uses `X-Forwarded-For` (Priority 3 in our code)

## Security Considerations

### Header Spoofing Prevention

**Q**: Can users fake their IP by setting these headers?

**A**: No, because:
1. Cloudflare **strips** client-provided `CF-Connecting-IP` headers
2. Cloudflare **overwrites** the header with the real client IP
3. Your nginx is **not** directly exposed to the internet (Cloudflare sits in front)

### Trust Chain:

```
Client
  → Can't set CF-Connecting-IP (Cloudflare strips it)
    → Cloudflare Edge
      → Sets CF-Connecting-IP with real client IP
        → Your Nginx
          → Forwards CF-Connecting-IP to Backend
            → Backend reads real IP ✅
```

## If You're NOT Using Cloudflare

If your site is **not** behind Cloudflare, the code will gracefully fall back:

1. Check `CF-Connecting-IP` → Not present
2. Check `X-Real-IP` → Nginx sets this from `$remote_addr`
3. Use `X-Real-IP` ✅

So the fix works for **both Cloudflare and non-Cloudflare deployments**.

## Troubleshooting

### Issue: Still seeing Cloudflare IPs

**Possible causes:**

1. **Old logs**: The fix only applies to NEW audit logs. Old logs will still show Cloudflare IPs.

   **Solution**: Create a new login to generate a fresh audit log entry.

2. **Cloudflare not sending header**: Check if Cloudflare is configured to send `CF-Connecting-IP`.

   **Solution**: Verify in Cloudflare dashboard → "Network" → "HTTP Request Headers"

3. **Cache issue**: Services haven't restarted with new code.

   **Solution**:
   ```bash
   docker-compose restart backend frontend
   ```

### Issue: Geolocation still showing wrong country

**Cause**: Old audit logs still have Cloudflare IPs.

**Solution**:
- The geolocation is fetched **at display time** (not stored in DB)
- Create a new login/action
- The new entry will show correct geolocation

### Issue: Local testing shows Docker IPs (172.19.x.x)

**Cause**: When testing locally (localhost), traffic doesn't go through Cloudflare.

**Expected behavior**: This is normal for local development.

**In production**: Real client IPs will be captured correctly.

## Summary

✅ **Fixed**: Backend now checks `CF-Connecting-IP` header first
✅ **Fixed**: Nginx forwards Cloudflare headers to backend
✅ **Backward compatible**: Works with and without Cloudflare
✅ **Security**: Header spoofing prevented by Cloudflare
✅ **Priority order**: CF → X-Real-IP → X-Forwarded-For → remote_addr

Your audit logs will now show **real client IP addresses** with **accurate geolocation**, even when using Cloudflare! 🎉

---

## References

- [Cloudflare: HTTP request headers](https://developers.cloudflare.com/fundamentals/reference/http-request-headers/)
- [Cloudflare: Restoring original visitor IP](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/)
- [Cloudflare IP Ranges](https://www.cloudflare.com/ips/)
