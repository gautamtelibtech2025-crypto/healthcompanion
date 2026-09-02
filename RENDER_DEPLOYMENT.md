# Deploy Health Companion to Render

## Steps to Deploy

### 1. **Push to GitHub**

Create a new GitHub repository and push this project:

```bash
cd health-companion
git init
git add .
git commit -m "Initial commit: Health Companion app ready for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/health-companion.git
git push -u origin main
```

### 2. **Set Up on Render**

1. Go to [render.com](https://render.com) and sign in with your GitHub account
2. Click **New +** → **Web Service**
3. Select your `health-companion` repository
4. Configure the service:
   - **Name**: `health-companion`
   - **Runtime**: Python 3.12
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Instance Type**: Free (for testing) or Starter (for production)

### 3. **Add Environment Variables**

In the Render dashboard, go to your service's **Environment** tab and add:

```
GEMINI_API_KEY=<your-actual-api-key>
```

Copy the value from your `.env` file.

### 4. **Deploy**

Click **Create Web Service** and Render will automatically:
- Build your app
- Deploy it
- Give you a live URL (e.g., `https://health-companion.onrender.com`)

## What's Been Updated

✅ **render.yaml** - Render service configuration
✅ **Procfile** - Process file for Render  
✅ **app.py** - Updated to:
  - Listen on `0.0.0.0` (accessible from the internet)
  - Use `PORT` environment variable (Render assigns a dynamic port)
  - Fall back to port 8080 for local development

## Local Testing

The app still works locally:
```bash
python app.py
# Visit http://127.0.0.1:8080
```

## .env File Security

⚠️ **Important**: Never commit `.env` to git. It's already in `.gitignore`, but always set sensitive values like `GEMINI_API_KEY` in Render's Environment dashboard, not in your repository.

## Live App URL

After deployment, you'll get a URL like:
```
https://health-companion.onrender.com
```

Share this link to use the app live!
