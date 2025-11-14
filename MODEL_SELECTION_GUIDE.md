# Claude Model Selection Guide

## Overview
Your Fantasy Football AI Manager now supports **user-configurable Claude models**! You can choose from 5 different Claude models based on your needs for speed, intelligence, and cost.

## Available Models

| Model | API Name | Best For | Speed | Intelligence | Cost |
|-------|----------|----------|-------|--------------|------|
| **Claude Sonnet 4.5** | `sonnet-4.5` | Complex analysis, best overall | ⚡⚡⚡ | 🧠🧠🧠🧠🧠 | 💰💰💰 |
| **Claude Opus 4** | `opus-4` | Premium performance | ⚡⚡ | 🧠🧠🧠🧠🧠 | 💰💰💰💰 |
| **Claude 3.5 Sonnet** | `sonnet-3.5` | Previous flagship | ⚡⚡⚡ | 🧠🧠🧠🧠 | 💰💰 |
| **Claude Sonnet** | `sonnet` | Balanced performance | ⚡⚡⚡⚡ | 🧠🧠🧠 | 💰💰 |
| **Claude Haiku** | `haiku` | Fast responses | ⚡⚡⚡⚡⚡ | 🧠🧠 | 💰 |

## How to Configure

### Method 1: Environment Variable (Recommended)

Add to your `.env` file:

```bash
# Choose one of: sonnet-4.5, opus-4, sonnet-3.5, sonnet, haiku
ANTHROPIC_MODEL=sonnet-4.5
```

Then restart your Docker containers:

```bash
docker-compose down
docker-compose up -d
```

### Method 2: Settings Page (Runtime)

1. Navigate to **Settings** page in the app
2. Under **AI Model Configuration**, select your preferred model
3. Click **"Save Settings to Backend"**
4. Settings are applied immediately (no restart needed)

**Note:** Settings page changes are runtime-only and won't persist across container restarts. For permanent changes, use Method 1.

### Method 3: API (Programmatic)

```bash
curl -X POST http://localhost:8000/api/v1/settings \
  -H "Content-Type: application/json" \
  -d '{
    "anthropic_model": "sonnet-4.5",
    "llm_provider": "anthropic"
  }'
```

## Model Recommendations

### For Best Results (Default)
**Use: `sonnet-4.5`**
- Latest and most intelligent model
- Best for complex sit/start decisions
- Excellent at multi-factor analysis

### For Budget-Conscious Users
**Use: `haiku`**
- 5x cheaper than Sonnet 4.5
- Still very capable for most tasks
- Great for high-volume usage

### For Balanced Performance
**Use: `sonnet-3.5`**
- Previous generation flagship
- Good balance of cost and performance
- Proven reliability

## Technical Details

### Model ID Mapping

The system maps user-friendly names to actual Anthropic API model IDs:

```python
{
    "sonnet-4.5": "claude-sonnet-4-5-20250929",
    "opus-4": "claude-opus-4-20250514",
    "sonnet-3.5": "claude-3-5-sonnet-20241022",
    "sonnet": "claude-3-5-sonnet-20241022",
    "haiku": "claude-3-5-haiku-20241022",
}
```

### Files Modified

- **Backend:**
  - `backend/app/core/config.py` - Added `ANTHROPIC_MODEL` setting
  - `backend/app/agents/llm_client.py` - Added model mapping logic
  - `backend/app/api/settings.py` - New API endpoint for settings
  - `backend/main.py` - Registered settings router

- **Frontend:**
  - `frontend/store/slices/settingsSlice.ts` - Updated model types
  - `frontend/app/settings/page.tsx` - Updated UI with new models

### Testing

Run the model mapping test:

```bash
cd backend
python test_model_mapping.py
```

## Troubleshooting

### Model not changing?
- Make sure you saved settings via the Settings page
- Or restart Docker containers if using `.env` method

### Invalid model error?
- Check spelling - must be one of: `sonnet-4.5`, `opus-4`, `sonnet-3.5`, `sonnet`, `haiku`
- System will default to `sonnet-4.5` if invalid

### API key errors?
- Ensure `ANTHROPIC_API_KEY` is set in `.env`
- All models use the same API key

## Future Enhancements

- [ ] Per-agent model selection (e.g., use Haiku for simple tasks, Sonnet 4.5 for complex)
- [ ] Cost tracking and usage analytics
- [ ] A/B testing different models
- [ ] OpenAI and Gemini model selection

