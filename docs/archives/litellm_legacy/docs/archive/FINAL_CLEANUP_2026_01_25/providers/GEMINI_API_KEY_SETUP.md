# Add Gemini API Key (Final Step to 18/18)

**Status:** 17/18 models working ✅  
**Remaining:** 2 Gemini models (gemini-1.5-flash, gemini-1.5-pro)  
**Time to complete:** 5 minutes

---

## Step 1: Get Gemini API Key

1. Go to: **https://aistudio.google.com/**
2. Click "Get API Key"
3. Copy the generated key (looks like: `AIza...`)

---

## Step 2: Add to .env

Edit `/LAB/@litellm/.env` and find the Gemini section:

```bash
# Google AI Studio (Gemini) - Uses OAuth (see ~/.007 for setup)
# GEMINI_API_KEY=your_gemini_key_here
```

Replace with your actual key:

```bash
GEMINI_API_KEY=AIzaSy...your_actual_key_here...
```

---

## Step 3: Restart Services

```bash
cd /LAB/@litellm
docker compose restart
sleep 30
```

---

## Step 4: Verify All 18/18 Working

```bash
python3 bin/probe_models.py
```

**Expected output:** ✨ All models operational

---

## That's It!

Once the API key is added and services restart, both Gemini models will work automatically.

**Current Score:** 17/18 (94%)  
**With this step:** 18/18 (100%) ✅
