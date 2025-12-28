# YouTube API Setup Guide

## 🎯 Why Your Own API Project?

The **YouTube Data API v3** has a daily quota limit of **10,000 units** per project. For a bot that interacts in chat, this is **not enough** if every user uses the same project.

### Quota Costs (Example):
- **Stream search** (`liveBroadcasts.list`): **1 unit**
- **Fetch chat** (`liveChatMessages.list`): **5 units** per poll
- **Send chat** (`liveChatMessages.insert`): **50 units**

**Problem**: An 8-hour stream with 5s polling uses ~**29,000 units** 💀

**Solution**: Each user creates their own Google Cloud Project and thus has their own 10k limit.

---

## 📋 Step-by-Step Guide

### 1. Open Google Cloud Console
- Go to: [https://console.cloud.google.com/](https://console.cloud.google.com/)
- Sign in with your Google account (preferably the one you stream with)

### 2. Create New Project
1. Click **"Create Project"** (or via dropdown menu)
2. **Project name**: e.g., `OpenStreamBot` (your choice)
3. **Organization**: Leave empty (or select your account)
4. Click **"Create"**

### 3. Enable YouTube Data API v3
1. In left menu: **"APIs & Services" → "Library"**
2. Search for: **"YouTube Data API v3"**
3. Click on result → **"Enable"**

### 4. Create OAuth Credentials
1. In left menu: **"APIs & Services" → "Credentials"**
2. Click **"+ Create Credentials" → "OAuth client ID"**
3. **If OAuth consent screen not yet configured**:
   - Click **"Configure consent screen"**
   - Choose **"External"** (or "Internal" if using G Suite)
   - **App name**: `OpenStreamBot` (your choice)
   - **User support email**: Your email
   - **Developer contact**: Your email
   - **Scopes**: Don't add anything (skip)
   - **Test users**: Add your email (important!)
   - **Save**
   
4. Back to **"Credentials"**:
   - **Application type**: **"Desktop app"**
   - **Name**: `OpenStreamBot Desktop` (your choice)
   - Click **"Create"**

5. **Download file**:
   - In popup click **"Download JSON"**
   - File downloads as `client_secret_XXXXXX.json`

### 5. Store File in Bot
1. **Rename**: Downloaded file to **`client_secret.json`**
2. **Move**: To **main folder** of OpenStreamBot (where `main.py` is located)

### 6. Adjust Config (optional)
Open `config.yaml` and ensure YouTube is enabled:

```yaml
youtube:
  enabled: true
  client_secret_file: client_secret.json
  token_file: token_youtube.json
```

### 7. Start Bot and Login
1. **Start launcher**: `python launcher.py`
2. Open **Accounts** tab
3. Click **"Login with Google"**
4. Browser opens → **Sign in with your Google account**
5. **Important**: "This app hasn't been verified by Google" will appear:
   - Click **"Advanced"**
   - Then **"Go to [App name] (unsafe)"**
   - This is normal because it's your own project!
6. **Grant permissions**
7. Done! Token saved as `token_youtube.json`

---

## 🔧 Optimize Quota

### Best Practices:
1. **Manual Connect**: Use **"Connect YouTube Stream"** button in dashboard only when streaming
2. **Don't run 24/7**: YouTube bot pauses automatically after 1h on quota errors
3. **Polling interval**: Bot uses YouTube's recommended interval (usually 5-10s)

### Check Quota Overview:
1. [Google Cloud Console](https://console.cloud.google.com/) → Your project
2. **"APIs & Services" → "Dashboard"**
3. Click **"YouTube Data API v3"**
4. Tab **"Quotas"** → Shows daily usage

---

## ❓ Common Issues

### "Quota Exceeded" Error
- **Cause**: Daily limit of 10,000 units exceeded
- **Solution**: 
  - Wait until midnight (Pacific Time, ~9:00 AM CET)
  - Or: Activate YouTube only when needed (button in dashboard)
  - Long-term: Request quota increase from Google (rarely needed)

### "Access blocked: This app's request is invalid"
- **Cause**: Redirect URI configured incorrectly
- **Solution**: Bot uses `localhost` automatically, so this shouldn't happen. If it does:
  - Cloud Console → Credentials → Edit OAuth client
  - Add **Authorized redirect URIs**: `http://localhost:8080/`

### "The OAuth Client ID has been deleted"
- **Cause**: Client was deleted, token is invalid
- **Solution**: 
  - Delete `token_youtube.json`
  - Create new OAuth credentials (see step 4)
  - Login again

---

## 🚀 Increase Quota (Optional, for Heavy Users)

If you regularly exceed 10k units/day:
1. [Request quota increase](https://support.google.com/youtube/contact/yt_api_form)
2. Provide justification (e.g., "Open source stream bot for personal channel")
3. Usually increased to **1,000,000 units/day**
4. Processing time: 1-2 weeks

---

## 📊 Cost?

**Completely free** for normal use! 🎉

Google provides the YouTube API for free. Only if you need **extremely high** quotas (> 1M/day), Google might ask you to upgrade to paid quota (very rare).

---

## 🛡️ Security

- **`client_secret.json`**: Don't share publicly! This file identifies your app
- **`token_youtube.json`**: **Never** share or commit! Contains access to your YouTube account
- Add both files to `.gitignore` (already default in project)

---

For questions or issues: Open [GitHub Issues](https://github.com/JanVanPommes/OpenStreamBot/issues)!
