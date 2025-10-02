# Parser Development Quick Reference

## TL;DR

**Adding a new parse mode = 3 steps, ~30 minutes**

1. Add parser class to `lula_wrapper.py`
2. Register in `__init__.py`
3. Add to `PARSE_MODES` in `app.py`

---

## Architecture Summary

```
Upload → Backend → LulaWrapperParser → lula2.py → Raw output → parse_output() → JSON
```

**Key Points:**
- ✅ Archive file passed directly to lula2.py (NOT extracted first)
- ✅ lula2.py handles extraction, date filtering, timezone conversion
- ✅ Wrapper parses lula2.py's text/CSV output into structured JSON
- ✅ Modular structure + Proven parsing = Best of both worlds

---

## Quick Start: Add a New Parser

### 1. Add Parser to `lula_wrapper.py`

```python
class NetworkParser(LulaWrapperParser):
    """Parser for network statistics (example)"""

    def parse_output(self, output):
        """
        Parse lula2.py output into structured data

        Args:
            output: String output from lula2.py

        Returns:
            List or dict with structured data
        """
        lines = output.strip().split('\n')
        data = []

        for line in lines:
            # Your parsing logic here
            if line.strip():
                data.append({'line': line})

        return data
```

### 2. Register Parser in `parsers/__init__.py`

```python
from .lula_wrapper import (
    ...
    NetworkParser  # Add this
)

PARSERS = {
    ...
    'network': NetworkParser,  # Add this
}
```

### 3. Add to Frontend in `app.py`

```python
PARSE_MODES = [
    ...
    {'value': 'network', 'label': 'Network Stats', 'description': 'Network statistics'},
]
```

### 4. Test

```bash
# Test parser loads
docker-compose exec backend python3 /app/test_parsers.py

# Restart backend
docker-compose restart backend

# Test with file upload at http://localhost:3000
```

---

## Parser Examples

### CSV Parser (like Bandwidth)

```python
class BandwidthParser(LulaWrapperParser):
    def parse_output(self, output):
        """Parse CSV bandwidth data"""
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return []

        data = []
        for line in lines[1:]:  # Skip header
            if not line.strip() or line.startswith('0,0,0'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                data.append({
                    'datetime': parts[0],
                    'total bitrate': parts[1],
                    'video bitrate': parts[2],
                    'notes': parts[3] if len(parts) > 3 else ''
                })
        return data
```

### Text Parser (like Errors)

```python
class ErrorParser(LulaWrapperParser):
    def parse_output(self, output):
        """Parse error output"""
        lines = output.strip().split('\n')
        return {
            'total_lines': len(lines),
            'lines': lines[:1000]  # Limit for performance
        }
```

### Structured Parser (like Modem Stats)

```python
class ModemStatsParser(LulaWrapperParser):
    def parse_output(self, output):
        """Parse modem statistics"""
        modems = []
        lines = output.split('\n')
        current_modem = None

        for line in lines:
            if line.startswith('Modem '):
                if current_modem:
                    modems.append(current_modem)
                modem_match = re.search(r'Modem (\d+)', line)
                if modem_match:
                    current_modem = {
                        'modem_id': modem_match.group(1),
                        'stats': {}
                    }
            elif current_modem and '\t' in line:
                # Parse stats lines
                if 'Bandwidth' in line:
                    # Extract bandwidth data
                    pass

        if current_modem:
            modems.append(current_modem)
        return modems
```

---

## Common Patterns

### Pattern 1: CSV Data

```python
def parse_output(self, output):
    lines = output.strip().split('\n')
    data = []
    for line in lines[1:]:  # Skip header
        parts = line.split(',')
        data.append({
            'field1': parts[0],
            'field2': parts[1]
        })
    return data
```

### Pattern 2: Line-by-Line

```python
def parse_output(self, output):
    lines = output.strip().split('\n')
    return [line for line in lines if line.strip()]
```

### Pattern 3: Multi-Line Records

```python
def parse_output(self, output):
    records = []
    current = None

    for line in output.split('\n'):
        if line.startswith('START:'):
            current = {'data': []}
        elif current and line.strip():
            current['data'].append(line)
        elif line.startswith('END:'):
            if current:
                records.append(current)
            current = None

    return records
```

### Pattern 4: Key-Value Extraction

```python
def parse_output(self, output):
    import re

    data = {}
    for line in output.split('\n'):
        match = re.search(r'(\w+):\s*(.+)', line)
        if match:
            data[match.group(1)] = match.group(2)

    return data
```

---

## Important Notes

### ✅ DO

- Override `parse_output()` to parse lula2.py's output
- Return structured data (list or dict)
- Handle empty output gracefully
- Strip whitespace from parsed values
- Use regex for complex parsing
- Test with real log files

### ❌ DON'T

- Override `parse()` - it's not used in wrappers
- Try to extract archives - lula2.py handles this
- Implement date filtering - lula2.py handles this
- Implement timezone conversion - lula2.py handles this
- Assume output format - check lula2.py's actual output first

---

## Testing Checklist

- [ ] Parser class created in `lula_wrapper.py`
- [ ] Registered in `parsers/__init__.py`
- [ ] Added to `PARSE_MODES` in `app.py`
- [ ] `test_parsers.py` passes
- [ ] Backend restarts without errors
- [ ] Mode appears in frontend dropdown
- [ ] File upload works
- [ ] Output displayed correctly (check both tabs)
- [ ] Date filtering works (if applicable)
- [ ] Timezone conversion works (if applicable)

---

## Debugging

### Parser doesn't appear in dropdown

Check:
1. Registered in `PARSERS` dict?
2. Added to `PARSE_MODES` list?
3. Backend restarted?

```bash
docker-compose restart backend
```

### "No output available"

Check:
1. `parse_output()` returns data (not None)?
2. lula2.py mode exists?
3. Check backend logs:

```bash
docker-compose logs backend --tail=50
```

### lula2.py error

Check:
1. Mode name matches lula2.py's mode?
2. Archive file is valid .bz2 or .tar.bz2?
3. Check error in backend logs

---

## Performance Tips

1. **Limit output size**: For large datasets, return first N items
   ```python
   return data[:1000]  # First 1000 items
   ```

2. **Skip empty lines**: Always filter out empty lines
   ```python
   lines = [line for line in output.split('\n') if line.strip()]
   ```

3. **Use efficient parsing**: Regex is slower than string methods
   ```python
   # Fast
   if line.startswith('ERROR:'):
       ...

   # Slower
   if re.match(r'^ERROR:', line):
       ...
   ```

---

## File Structure

```
backend/
├── app.py                      # Add to PARSE_MODES here
├── lula2.py                    # Original parser (don't modify)
├── parsers/
│   ├── __init__.py            # Register parser here
│   ├── base.py                # Base class (for future native parsers)
│   ├── lula_wrapper.py        # Add new parser class here ⭐
│   ├── bandwidth.py           # [Legacy] Example native parser
│   └── ...
└── test_parsers.py            # Tests parser registry
```

---

## Resources

- **Architecture**: [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Release Notes**: [V3_RELEASE_NOTES.md](V3_RELEASE_NOTES.md)
- **lula2.py modes**: Run `python3 lula2.py --help` in container

---

## Example: Complete New Parser

**Scenario**: Add "cpu" mode for CPU usage statistics

**Step 1**: Add to `lula_wrapper.py`:
```python
class CPUParser(LulaWrapperParser):
    """Parser for CPU usage"""

    def parse_output(self, output):
        lines = output.strip().split('\n')
        data = []
        for line in lines:
            if '%' in line:  # Lines with CPU percentages
                data.append({'line': line.strip()})
        return data
```

**Step 2**: Register in `__init__.py`:
```python
from .lula_wrapper import (..., CPUParser)

PARSERS = {
    ...
    'cpu': CPUParser,
}
```

**Step 3**: Add to `app.py`:
```python
PARSE_MODES = [
    ...
    {'value': 'cpu', 'label': 'CPU Usage', 'description': 'CPU idle/usage statistics'},
]
```

**Step 4**: Test:
```bash
docker-compose restart backend
# Upload file with mode "CPU Usage"
```

**Done!** ✅

---

**Questions?** Check the documentation or backend logs for errors.
