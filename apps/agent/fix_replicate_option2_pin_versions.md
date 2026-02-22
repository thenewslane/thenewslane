# Option 2: Pin Compatible Library Versions

## Overview
Force install specific versions of Replicate and Pydantic that are known to work together, even on Python 3.14.

## Steps

### 1. Research Compatible Versions
```bash
# Check which Replicate versions support newer Pydantic
pip index versions replicate
```

### 2. Update pyproject.toml with Pinned Versions
```toml
[project]
dependencies = [
    # ... other dependencies ...
    
    # Pin specific versions that work together
    "pydantic>=2.0,<3.0",           # Force Pydantic v2
    "replicate>=0.28.0",            # Use newer Replicate that might support Pydantic v2
    
    # Alternative: Try development/beta versions
    # "replicate>=0.30.0b1",         # Beta version with Pydantic v2 support
]
```

### 3. Force Reinstall
```bash
cd /Users/admin/Desktop/platform/apps/agent

# Uninstall conflicting packages
pip uninstall replicate pydantic -y

# Clear pip cache
pip cache purge

# Reinstall with pinned versions
pip install --no-cache-dir pydantic==2.9.2
pip install --no-cache-dir replicate==0.28.0

# Or install all at once
pip install -e . --force-reinstall --no-deps
pip install -e .
```

### 4. Test Installation
```bash
python -c "
import replicate
import pydantic
print(f'Replicate version: {replicate.__version__}')
print(f'Pydantic version: {pydantic.__version__}')
print('Testing Replicate client...')
client = replicate.Client(api_token='dummy')
print('✅ Success!')
"
```

## Alternative: Try Pre-release Versions
```bash
# Install beta/development versions that might have fixes
pip install --pre replicate
pip install --upgrade replicate
```

## Pros:
- ✅ Keep Python 3.14
- ✅ Minimal code changes
- ✅ May work if newer Replicate versions support Pydantic v2

## Cons:
- ❌ May not work - compatibility still uncertain
- ❌ Might introduce other breaking changes
- ❌ Beta versions may be unstable

## Success Criteria:
No warnings or errors when importing and using Replicate with Python 3.14.