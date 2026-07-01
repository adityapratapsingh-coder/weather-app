# 🚀 Deploying Skyline (Weather App) to Render

This FastAPI app can be hosted free on Render.com.

## One-time file (already included)
`render.yaml` tells Render how to build and run the app:
- Build:  `pip install -r requirements.txt`
- Start:  `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Steps
1. Make sure `render.yaml` is committed and pushed to the `weather-app` repo.
2. Go to https://render.com and sign up / log in with GitHub (free).
3. Click **New +** → **Web Service**.
4. Connect and select the **weather-app** repository.
5. Render auto-detects the settings from `render.yaml`. If asked, confirm:
   - Runtime: **Python**
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance type: **Free**
6. Click **Create Web Service**. Render builds and deploys (about 5–10 minutes).
7. When it finishes you get a live URL like `https://weather-app-xxxx.onrender.com`.

## Notes
- No code changes are needed — the app reads the port from `$PORT`.
- No API keys are required (Open-Meteo is used).
- On the free plan the service sleeps after ~15 minutes idle; the next visit
  takes ~30–50 seconds to wake up, then it's fast again.
