# MaxOS Configuration

This directory contains configuration files for MaxOS.

## Quick Start

1. **Copy the example file:**
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   ```

2. **Edit your settings:**
   ```bash
   nano config/settings.yaml
   # or
   vim config/settings.yaml
   ```

3. **Update the API keys:**
   - Replace `"set-me"` in `llm.google_api_key` with your actual Google API key

## Configuration Files

- **`settings.example.yaml`** - Template configuration file (committed to git)
- **`settings.yaml`** - Your actual configuration (gitignored, not committed)
- **`*.local.yaml`** - Local override files (gitignored, not committed)

## Using Environment Variables

You can also configure MaxOS using environment variables instead of YAML files:

```bash
export GOOGLE_API_KEY="your-key-here"
```

Or use a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env and add your keys
```

Environment variables take precedence over settings in YAML files.

## Configuration Priority

MaxOS loads configuration in this order (later sources override earlier ones):

1. `config/settings.example.yaml` - Default settings
2. `config/settings.yaml` - Your custom settings (if exists)
3. Environment variables - Override any YAML setting
4. `.env` file - Loaded automatically if present

## Detailed Documentation

For detailed information about obtaining and configuring tokens, see:
- **[docs/TOKEN_SETUP.md](../docs/TOKEN_SETUP.md)** - Complete guide to obtaining API keys

## Security

**Important:** Never commit `settings.yaml` or `.env` files to git!

These files are already in `.gitignore` to prevent accidental commits.

If you accidentally commit secrets:
1. Immediately revoke the exposed keys
2. Generate new keys
3. Update your local configuration
4. Consider using tools like `git-secrets` to prevent future accidents
