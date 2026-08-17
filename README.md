# 🎩 J.A.R.V.I.S. 24/7 Cloud Bot & Local PC Bridge

A hybrid AI assistant architecture bridging **Telegram**, **Google Gemini 3.7 Flash**, and your **Windows PC**:
- ☁️ **Railway Cloud Server**: Runs 24/7 in the cloud, handling Telegram messages, voice notes, British voice synthesis, and vision analysis.
- 💻 **Local PC Bridge**: Runs silently in the background on your Windows PC. When your PC is on, Jarvis has full remote control (screenshots, volume, apps, files). When your PC is off/sleeping, Jarvis politely informs you that the PC is offline and continues assisting you with general AI tasks.

---

## 🚀 Step 1: Deploy 24/7 Server to Railway

1. Push or upload this `jarvis-telegram` directory to a GitHub repository (or use the Railway CLI: `railway up`).
2. On **[Railway.app](https://railway.app)**:
   - Click **New Project** → **Deploy from GitHub repo**.
   - Select your repo. Railway will automatically detect the [`Dockerfile`](file:///C:/Users/ROG/jarvis-telegram/Dockerfile) and [`railway.json`](file:///C:/Users/ROG/jarvis-telegram/railway.json).
3. In your Railway Project Settings → **Variables**, add:
   - `TELEGRAM_BOT_TOKEN` = `8719669013:AAENOdEN0Z654r03temJP9qgKoiUSQcPxPo`
   - `GEMINI_API_KEY` = *your Gemini API key*
   - `GEMINI_MODEL` = `gemini-3.7-flash`
   - `BRIDGE_SECRET_KEY` = *any secret password of your choice (e.g. `my-secure-jarvis-key`)*
   - `ALLOWED_USER_IDS` = *your Telegram user ID*
   - `VOICE_REPLY_ENABLED` = `true`
   - `VOICE_NAME` = `en-GB-RyanNeural`
4. In Railway Settings → **Networking**, click **Generate Domain** (e.g., `jarvis-production.up.railway.app`).

---

## 💻 Step 2: Configure & Start Your Local PC Bridge

1. Open your local [`.env`](file:///C:/Users/ROG/jarvis-telegram/.env) file on your PC:
   - Set `BRIDGE_SECRET_KEY` = *(same secret key you put in Railway)*
   - Set `RAILWAY_URL` = `wss://your-railway-domain.up.railway.app/ws` (using `wss://` with `/ws` at the end)
2. Run [**`start_background.bat`**](file:///C:/Users/ROG/jarvis-telegram/start_background.bat) (or [`run_pc_bridge.bat`](file:///C:/Users/ROG/jarvis-telegram/run_pc_bridge.bat) for live logs).
3. To start automatically every time your PC turns on:
   - Double-click [**`enable_autostart.bat`**](file:///C:/Users/ROG/jarvis-telegram/enable_autostart.bat).

---

## 🛠️ Local PC Scripts

| Script | Purpose |
| :--- | :--- |
| [**`start_background.bat`**](file:///C:/Users/ROG/jarvis-telegram/start_background.bat) | Starts PC Bridge silently in background (no CMD window). |
| [**`run_pc_bridge.bat`**](file:///C:/Users/ROG/jarvis-telegram/run_pc_bridge.bat) | Starts PC Bridge with live terminal logs for debugging. |
| [**`status_jarvis.bat`**](file:///C:/Users/ROG/jarvis-telegram/status_jarvis.bat) | Checks if bridge is running and displays recent logs. |
| [**`stop_jarvis.bat`**](file:///C:/Users/ROG/jarvis-telegram/stop_jarvis.bat) | Stops the local PC Bridge. |
| [**`enable_autostart.bat`**](file:///C:/Users/ROG/jarvis-telegram/enable_autostart.bat) | Configures Windows to auto-connect bridge on PC startup. |

---

## 📱 Telegram Behavior

- **When PC is ON & Connected**:
  - *"Take a screenshot"* → Jarvis takes a screenshot on your PC and sends it to chat.
  - *"Turn up the volume"* → Jarvis turns up your PC speakers.
  - *"Send me report.docx from Documents"* → Transferred to Telegram.
- **When PC is OFF / Disconnected**:
  - *"Take a screenshot"* → *"Your Windows workstation is currently offline, sir. Once powered on, I can execute that for you."*
  - *"Explain how black holes work"* → Jarvis answers in voice & text 24/7 without needing your PC!
