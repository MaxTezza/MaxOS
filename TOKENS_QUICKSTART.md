# Token Setup - Summary

This document summarizes the token configuration support added to MaxOS.

## What Was Added

### 1. Files Created

- **`.env.example`** - Template for environment variables with all required tokens
- **`docs/TOKEN_SETUP.md`** - Comprehensive guide for obtaining and configuring tokens
- **`config/README.md`** - Quick reference guide for configuration
- **`max_os/utils/analytics.py`** - Google Analytics integration module
- **`test_token_config.py`** - Test script to verify configuration

### 2. Files Modified

- **`README.md`** - Updated with token setup instructions
- **`config/settings.example.yaml`** - Added Google Analytics configuration
- **`max_os/utils/config.py`** - Added automatic .env file loading
- **`pyproject.toml`** - Added python-dotenv and aiohttp dependencies

## Quick Start

### Step 1: Get Your API Keys

#### Anthropic API Key (Required)
1. Visit https://console.anthropic.com/
2. Create account or sign in
3. Go to API Keys section
4. Create new key
5. Copy the key (starts with `sk-ant-`)

#### OpenAI API Key (Optional)
1. Visit https://platform.openai.com/
2. Create account or sign in
3. Go to https://platform.openai.com/api-keys
4. Create new secret key
5. Copy the key (starts with `sk-proj-` or `sk-`)

#### Google Analytics (Optional)
1. Visit https://analytics.google.com/
2. Create GA4 property
3. Get Measurement ID (format: `G-XXXXXXXXXX`)
4. Create Measurement Protocol API Secret

### Step 2: Configure MaxOS

Choose **ONE** of these methods:

#### Option A: Using .env file (Recommended)
```bash
# Copy the example file
cp .env.example .env

# Edit and add your keys
nano .env
```

Edit `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
OPENAI_API_KEY=sk-proj-your-actual-key-here
GA_MEASUREMENT_ID=G-XXXXXXXXXX
GA_API_SECRET=your_ga_api_secret_here
```

#### Option B: Using config/settings.yaml
```bash
# Copy the example file
cp config/settings.example.yaml config/settings.yaml

# Edit and add your keys
nano config/settings.yaml
```

Edit the `llm` section:
```yaml
llm:
  anthropic_api_key: "sk-ant-api03-your-actual-key-here"
  openai_api_key: "sk-proj-your-actual-key-here"
```

Edit the `telemetry` section:
```yaml
telemetry:
  enabled: true  # Set to true if using GA
  google_analytics:
    measurement_id: "G-XXXXXXXXXX"
    api_secret: "your_ga_api_secret_here"
```

#### Option C: Using Environment Variables
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-actual-key-here"
export OPENAI_API_KEY="sk-proj-your-actual-key-here"
export GA_MEASUREMENT_ID="G-XXXXXXXXXX"
export GA_API_SECRET="your_ga_api_secret_here"
```

### Step 3: Verify Configuration

```bash
# Test that everything is configured correctly
python test_token_config.py
```

You should see:
- ✓ Set for ANTHROPIC_API_KEY (required)
- ✓ Set for other keys if you configured them

### Step 4: Run MaxOS

```bash
# Activate virtual environment
source .venv/bin/activate

# Test with a simple command
python -m max_os.interfaces.cli.main "show system health"
```

## Token Priority

MaxOS loads configuration in this order (later overrides earlier):

1. `config/settings.example.yaml` (defaults)
2. `config/settings.yaml` (your settings)
3. Environment variables (from shell or `.env`)

## Security

**IMPORTANT:**
- Never commit `.env` or `config/settings.yaml` to git
- These files are already in `.gitignore`
- Never share your API keys publicly
- Rotate keys every 90 days
- Use separate keys for development and production

## Features Enabled by Tokens

### With ANTHROPIC_API_KEY:
- Natural language understanding
- Intent parsing and routing
- Agent orchestration
- Personality learning
- Predictive agent spawning

### With OPENAI_API_KEY:
- Fallback LLM when Anthropic is unavailable
- Alternative model options

### With Google Analytics:
- Usage tracking (privacy-focused)
- Agent execution metrics
- Performance monitoring
- User behavior insights

## Troubleshooting

### "No LLM client available"
**Solution:** Set ANTHROPIC_API_KEY in .env or config/settings.yaml

### "Authentication failed"
**Solution:** Check that your API key is correct and active

### Configuration not loading
**Solution:** Run `python test_token_config.py` to diagnose

### GA telemetry not working
**Solution:** 
1. Set `telemetry.enabled: true` in settings.yaml
2. Verify GA tokens are correct
3. Check logs for errors

## Next Steps

1. **Read the full guide:** `docs/TOKEN_SETUP.md`
2. **Configure tokens:** Follow Step 2 above
3. **Test configuration:** `python test_token_config.py`
4. **Try MaxOS:** `python -m max_os.interfaces.cli.main "your command"`
5. **Review examples:** See README.md for command examples

## Getting Help

- Full documentation: `docs/TOKEN_SETUP.md`
- Config reference: `config/README.md`
- Main README: `README.md`
- GitHub Issues: https://github.com/MaxTezza/MaxOS/issues

---

**Remember:** Your tokens are credentials - keep them secret and secure!
