# Token Configuration Guide

This guide explains how to obtain and configure the required API tokens for MaxOS.

## Required Tokens

### 1. Google API Key (Required)

MaxOS uses Google's Gemini models for natural language understanding and agent orchestration.

**How to get your token:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign up or log in with your Google account
3. Click "Create API Key" and select a Google Cloud project (or create a new one)
4. Copy your API key
5. Add it to your `.env` file or `config/settings.yaml`

**Usage in MaxOS:**
```bash
# In .env file:
GOOGLE_API_KEY=AIza...

# OR in config/settings.yaml:
llm:
  google_api_key: "AIza..."
```

**Pricing:** 
- Gemini 1.5 Flash: Free tier available (15 RPM, 1M TPM)
- For higher usage, check pricing at https://ai.google.dev/pricing

**Models Available:**
- `gemini-1.5-flash`: Fast, cost-effective (recommended for most use cases)
- `gemini-1.5-pro`: More capable for complex tasks
- `gemini-1.0-pro`: Legacy model

---

## Optional Tokens

### 2. Google Analytics (GA) Token

If you want to track usage analytics for your MaxOS instance, you can configure Google Analytics.

**What you need:**
- **GA4 Measurement ID**: Identifies your property (format: `G-XXXXXXXXXX`)
- **Measurement Protocol API Secret**: Authenticates server-side events

**How to get your tokens:**

1. **Create GA4 Property:**
   - Visit [Google Analytics](https://analytics.google.com/)
   - Click "Admin" (gear icon)
   - Under Property column, click "Create Property"
   - Follow the setup wizard
   - Copy your **Measurement ID** (e.g., `G-XXXXXXXXXX`)

2. **Create API Secret:**
   - In your GA4 property, go to Admin > Data Streams
   - Click on your data stream
   - Scroll to "Measurement Protocol API secrets"
   - Click "Create"
   - Give it a nickname (e.g., "MaxOS")
   - Copy the **Secret value**

**Usage in MaxOS:**
```bash
# In .env file:
GA_MEASUREMENT_ID=G-XXXXXXXXXX
GA_API_SECRET=your_api_secret_here

# OR in config/settings.yaml:
telemetry:
  enabled: true
  google_analytics:
    measurement_id: "G-XXXXXXXXXX"
    api_secret: "your_api_secret_here"
```

**Note:** Telemetry is disabled by default. Set `telemetry.enabled: true` to activate.

---

## Setup Instructions

### Method 1: Using .env file (Recommended)

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your tokens:
   ```bash
   nano .env
   # or
   vim .env
   ```

3. The application will automatically load environment variables from `.env`

### Method 2: Using config/settings.yaml

1. Copy the example configuration:
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   ```

2. Edit `config/settings.yaml` and replace placeholder values:
   ```bash
   nano config/settings.yaml
   ```

3. Update the `llm` section with your API keys:
   ```yaml
   llm:
     anthropic_api_key: "your-actual-key-here"
     openai_api_key: "your-actual-key-here"  # optional
   ```

### Method 3: Using Environment Variables Directly

You can also set environment variables in your shell:

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export OPENAI_API_KEY="sk-proj-..."
export GA_MEASUREMENT_ID="G-XXXXXXXXXX"
export GA_API_SECRET="your_api_secret_here"
```

Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

---

## Security Best Practices

1. **Never commit tokens to git:**
   - `.env` and `config/settings.yaml` are in `.gitignore`
   - Only commit `.env.example` and `config/settings.example.yaml`

2. **Rotate keys regularly:**
   - Change your API keys every 90 days
   - Revoke old keys after rotation

3. **Use separate keys for development and production:**
   - Create different API keys for different environments
   - Use more restrictive permissions for production

4. **Protect your .env file:**
   ```bash
   chmod 600 .env
   chmod 600 config/settings.yaml
   ```

5. **Monitor usage:**
   - Check your API usage dashboards regularly
   - Set up billing alerts to avoid unexpected charges

---

## Verifying Your Configuration

After setting up your tokens, verify they work:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Test with a simple command
python -m max_os.interfaces.cli.main "show system health"
```

If you see a meaningful response, your tokens are configured correctly!

---

## Troubleshooting

### "No LLM client available"
- **Cause:** API keys not set or invalid
- **Solution:** Double-check your `.env` file or `config/settings.yaml`

### "Authentication failed"
- **Cause:** Invalid or expired API key
- **Solution:** Generate a new key from the provider's dashboard

### "Rate limit exceeded"
- **Cause:** Too many API requests
- **Solution:** Implement retry logic or upgrade your API plan

### "Telemetry not working"
- **Cause:** Telemetry disabled or GA tokens not set
- **Solution:** Set `telemetry.enabled: true` and verify GA tokens

---

## Cost Optimization Tips

1. **Use local models when possible:**
   - Configure `local_model_path` in settings.yaml
   - Fallback to cloud APIs only when needed

2. **Monitor token usage:**
   - Enable logging to track API calls
   - Review `logs/maxos.log` for usage patterns

3. **Implement caching:**
   - Use Redis memory backend to cache responses
   - Reduce redundant API calls

4. **Choose the right model:**
   - Use cheaper models for simple tasks
   - Reserve advanced models for complex reasoning

---

## Support

If you encounter issues with token configuration:
1. Check the [GitHub Issues](https://github.com/MaxTezza/MaxOS/issues)
2. Review the logs in `logs/maxos.log`
3. Ensure you're using the latest version of MaxOS

**Remember:** Never share your API tokens publicly or commit them to version control!
