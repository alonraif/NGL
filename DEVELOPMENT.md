# 🛠️ Development Guide

This guide is for developers who want to modify or extend the LiveU Log Analyzer.

## Development Setup

### Backend Development

Run Flask in development mode with hot reload:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The backend will run on `http://localhost:5000` with auto-reload enabled.

### Frontend Development

Run React development server:

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000` with hot module replacement.

**Note:** Update the API URL in frontend to point to backend:
```javascript
// In frontend/src/App.js or create .env file
REACT_APP_API_URL=http://localhost:5000
```

## Project Architecture

### Backend (Flask)

**File: `backend/app.py`**

Key components:
- `/api/parse-modes` - Returns available parsing modes
- `/api/upload` - Handles file upload and processing
- `/api/health` - Health check endpoint

**Adding a new parse mode:**

1. Add to `PARSE_MODES` array in `app.py`:
```python
{'value': 'newmode', 'label': 'New Mode', 'description': 'Description here'}
```

2. Add parsing logic in the parser function:
```python
elif parse_mode == 'newmode':
    parsed_data = parse_new_mode(output)
```

3. Update `lula2.py` if needed for the new mode

**Adding a new parser:**

Create a new function in `app.py`:
```python
def parse_new_mode(output):
    """Parse new mode output into structured data"""
    data = []
    # Your parsing logic here
    return data
```

### Frontend (React)

**Component Hierarchy:**
```
App
├── FileUpload
└── Results
    ├── ModemStats
    ├── BandwidthChart
    ├── SessionsTable
    └── RawOutput
```

**Adding a new visualization:**

1. Create new component in `frontend/src/components/`:
```javascript
// NewVisualization.js
import React from 'react';
import { LineChart, ... } from 'recharts';

function NewVisualization({ data }) {
  return (
    <div>
      {/* Your visualization */}
    </div>
  );
}

export default NewVisualization;
```

2. Import and use in `Results.js`:
```javascript
import NewVisualization from './NewVisualization';

// In renderVisualization():
if (data.parse_mode === 'newmode') {
  return <NewVisualization data={data.parsed_data} />;
}
```

## Styling Guide

The app uses a consistent design system:

**Colors:**
- Primary: `#667eea` (purple-blue)
- Secondary: `#764ba2` (purple)
- Success: `#82ca9d` (green)
- Error: `#ff6b6b` (red)
- Warning: `#ffd93d` (yellow)

**CSS Classes:**
- `.card` - White card with shadow
- `.stat-card` - Gradient statistics card
- `.btn-primary` - Primary button
- `.table-container` - Responsive table wrapper

## Adding New Chart Types

Using Recharts library:

```javascript
import {
  BarChart, LineChart, AreaChart, PieChart,
  Bar, Line, Area, Pie, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
  ResponsiveContainer
} from 'recharts';

// Example
<ResponsiveContainer width="100%" height={400}>
  <BarChart data={yourData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="name" />
    <YAxis />
    <Tooltip />
    <Legend />
    <Bar dataKey="value" fill="#667eea" />
  </BarChart>
</ResponsiveContainer>
```

## Testing

### Backend Testing

```bash
cd backend

# Test health endpoint
curl http://localhost:5000/api/health

# Test parse modes
curl http://localhost:5000/api/parse-modes

# Test upload (with file)
curl -X POST -F "file=@test.tar.bz2" \
     -F "parse_mode=md" \
     http://localhost:5000/api/upload
```

### Frontend Testing

```bash
cd frontend
npm test
```

## Docker Development

### Rebuild specific service:
```bash
docker-compose up --build backend
docker-compose up --build frontend
```

### View logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Access container shell:
```bash
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Clean everything:
```bash
docker-compose down -v
docker system prune -a
```

## Common Development Tasks

### Add a new dependency

**Backend:**
```bash
cd backend
pip install new-package
pip freeze > requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install new-package
```

### Update lula2.py

If you modify the original `lula2.py`:
```bash
cp lula2.py backend/lula2.py
docker-compose up --build backend
```

### Change port numbers

Edit `docker-compose.yml`:
```yaml
services:
  frontend:
    ports:
      - "3001:80"  # External:Internal
  backend:
    ports:
      - "5001:5000"
```

## Performance Optimization

### Backend
- Use streaming for large files
- Implement caching for repeated queries
- Add background task queue (Celery)
- Optimize regex patterns in lula2.py

### Frontend
- Lazy load components
- Virtualize long tables
- Memoize expensive computations
- Add pagination for large datasets

## Security Considerations

- File upload validation (size, type)
- Sanitize user inputs
- Rate limiting on API endpoints
- CORS configuration for production
- Environment variables for secrets

## Deployment

### Production Build

```bash
# Build optimized images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables

Create `.env` file:
```
FLASK_ENV=production
FLASK_DEBUG=0
MAX_CONTENT_LENGTH=524288000
REACT_APP_API_URL=https://your-domain.com
```

## Troubleshooting

### Backend won't start
- Check Python version (3.9+)
- Verify all dependencies installed
- Check port 5000 not in use
- Review logs: `docker-compose logs backend`

### Frontend won't build
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version (18+)
- Verify package.json syntax

### Charts not rendering
- Check browser console for errors
- Verify data format matches component expectations
- Ensure Recharts is installed

## Resources

- **React**: https://react.dev/
- **Flask**: https://flask.palletsprojects.com/
- **Recharts**: https://recharts.org/
- **Docker**: https://docs.docker.com/

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Happy Coding! 💻**
