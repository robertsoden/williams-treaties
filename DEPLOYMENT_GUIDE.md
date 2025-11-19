# Deployment Guide: GitHub Pages + Render

This guide walks through deploying the Williams Treaties mapping project using:
- **GitHub Pages** for hosting data (ontario-environmental-data repo)
- **Render** for hosting the Flask map server (williams-treaties repo)

## Architecture Overview

```
┌─────────────────────────────────────┐
│  ontario-environmental-data repo    │
│  ├── Data collection scripts        │
│  ├── GitHub Actions workflows       │
│  └── GitHub Pages hosting           │
│      └── https://robertsoden.       │
│          github.io/ontario-         │
│          environmental-data/        │
└─────────────────────────────────────┘
                 ▲
                 │ Data files
                 │ (GeoJSON, GeoTIFF)
                 │
┌────────────────┴────────────────────┐
│  williams-treaties repo             │
│  ├── Flask web server               │
│  ├── Map visualization (HTML/JS)    │
│  └── Deployed to Render             │
│      └── https://your-app.onrender. │
│          com                        │
└─────────────────────────────────────┘
```

---

## Part 1: Set Up GitHub Pages for Data Repository

### Step 1.1: Copy Workflow File to Data Repo

The workflow file has been created in this repository at:
```
.github-workflows-for-data-repo/publish-data-to-pages.yml
```

**To deploy it:**

```bash
# Navigate to your ontario-environmental-data repository
cd /path/to/ontario-environmental-data

# Create .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy the workflow file from williams-treaties repo
cp /home/user/williams-treaties/.github-workflows-for-data-repo/publish-data-to-pages.yml \
   .github/workflows/publish-data-to-pages.yml

# Commit and push
git add .github/workflows/publish-data-to-pages.yml
git commit -m "Add GitHub Pages deployment workflow"
git push origin main
```

### Step 1.2: Enable GitHub Pages in Repository Settings

1. Go to **ontario-environmental-data** repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under **Source**, select:
   - Source: **GitHub Actions**
4. Click **Save**

### Step 1.3: Trigger Data Publication

**Option A: Run Manually**
1. Go to **Actions** tab in ontario-environmental-data repo
2. Select **Publish Data to GitHub Pages** workflow
3. Click **Run workflow** → **Run workflow**

**Option B: Automatic (after data collection)**
- The workflow will automatically run after the "Data Collection" workflow completes
- Just run your data collection workflow, and publishing happens automatically

### Step 1.4: Verify Data is Published

After the workflow completes, visit:
```
https://robertsoden.io/ontario-environmental-data/
```

You should see an index page. Test data access:
```
https://robertsoden.io/ontario-environmental-data/data/processed/boundaries/williams_treaty.geojson
```

---

## Part 2: Deploy Map Server to Render

### Step 2.1: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account (recommended)
3. Authorize Render to access your GitHub repositories

### Step 2.2: Create New Web Service

1. In Render dashboard, click **New +** → **Web Service**
2. Connect your **williams-treaties** repository
3. Configure the service:

   **Basic Settings:**
   - Name: `williams-treaties` (or your preferred name)
   - Region: Choose closest to your users
   - Branch: `main`
   - Root Directory: (leave empty)
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python web/server.py --host 0.0.0.0 --port $PORT`

   **Environment Variables:**
   - Click **Add Environment Variable**
   - Add these variables:

   | Key | Value |
   |-----|-------|
   | `DATA_SOURCE_URL` | `https://robertsoden.io/ontario-environmental-data` |
   | `DATA_MODE` | `remote` |
   | `PYTHON_VERSION` | `3.11.0` |

   **Plan:**
   - Select **Free** plan (for testing) or **Starter** for production

4. Click **Create Web Service**

### Step 2.3: Wait for Deployment

- Render will build and deploy your application
- This takes 2-5 minutes on first deployment
- Watch the deployment logs for any errors

### Step 2.4: Verify Deployment

Once deployed, you'll get a URL like:
```
https://williams-treaties.onrender.com
```

Visit it in your browser to see your map!

---

## Part 3: Set Up Automatic Deployments (Optional)

### Option A: Use render.yaml (Recommended)

This repository already has a `render.yaml` file configured. To use it:

1. In Render dashboard, go to **Blueprint** → **New Blueprint Instance**
2. Connect your **williams-treaties** repository
3. Render will automatically detect `render.yaml`
4. Review settings and click **Apply**

Environment variables are already defined in `render.yaml`:
```yaml
envVars:
  - key: DATA_SOURCE_URL
    value: https://robertsoden.io/ontario-environmental-data
  - key: PYTHON_VERSION
    value: 3.11.0
```

### Option B: GitHub Actions Auto-Deploy

To enable automatic deployments via GitHub Actions:

**Step B.1: Get Render API Key**
1. In Render dashboard, go to **Account Settings** → **API Keys**
2. Create new API key
3. Copy the key

**Step B.2: Get Service ID**
1. Go to your web service in Render
2. URL will be: `https://dashboard.render.com/web/srv-XXXXX`
3. Copy the `srv-XXXXX` part (this is your service ID)

**Step B.3: Add GitHub Secrets**
1. Go to your **williams-treaties** repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

   | Name | Value |
   |------|-------|
   | `RENDER_API_KEY` | Your API key from Step B.1 |
   | `RENDER_SERVICE_ID` | Your service ID from Step B.2 |

**Step B.4: Enable Workflow**

The workflow is already created at `.github/workflows/deploy-render.yml`

Now, every push to `main` will automatically deploy to Render!

---

## Part 4: Testing and Verification

### Test 1: Verify Data Loading

1. Open your deployed map: `https://your-app.onrender.com`
2. Open browser DevTools (F12) → Network tab
3. Toggle map layers on/off
4. You should see requests to:
   ```
   https://robertsoden.io/ontario-environmental-data/data/processed/...
   ```
5. Verify they return 200 OK status

### Test 2: Check Configuration API

Visit your app's API endpoints:
```
https://your-app.onrender.com/api/data-source
https://your-app.onrender.com/api/layer-config
https://your-app.onrender.com/api/info
```

Verify `data_source.base_url` points to GitHub Pages URL.

### Test 3: Test All Layers

Go through each layer in the map:
- Williams Treaty boundary
- First Nations reserves
- Environmental organizations
- Fire perimeters
- NDVI vegetation
- DEM elevation

Verify they load without errors.

---

## Troubleshooting

### Issue: Data files return 404

**Cause:** GitHub Pages not set up or data not published

**Solution:**
1. Verify GitHub Pages is enabled in ontario-environmental-data repo
2. Check workflow ran successfully
3. Visit `https://robertsoden.io/ontario-environmental-data/` to verify

### Issue: Map shows but layers don't load

**Cause:** CORS issues or wrong data URL

**Solution:**
1. Check environment variable `DATA_SOURCE_URL` in Render
2. Verify it matches GitHub Pages URL exactly (no trailing slash)
3. Check browser console for CORS errors

### Issue: Render deployment fails

**Cause:** Missing dependencies or configuration issues

**Solution:**
1. Check Render deployment logs
2. Verify `requirements.txt` includes all dependencies
3. Ensure `render.yaml` is properly formatted

### Issue: GitHub Actions workflow fails

**Cause:** Missing secrets or permissions

**Solution:**
1. Verify GitHub secrets are set correctly
2. Check workflow has proper permissions
3. Review workflow run logs in Actions tab

---

## Maintenance

### Updating Data

To update data files:

```bash
# In ontario-environmental-data repo
cd /path/to/ontario-environmental-data

# Run data collection
python scripts/run_all.py

# Commit new data
git add data/
git commit -m "Update environmental data"
git push origin main

# GitHub Actions will automatically publish to GitHub Pages
```

### Updating Map

To update the map application:

```bash
# In williams-treaties repo
cd /path/to/williams-treaties

# Make your changes
# ...

# Commit and push
git add .
git commit -m "Update map features"
git push origin main

# If using GitHub Actions, deployment happens automatically
# Otherwise, Render will auto-deploy from GitHub (if connected)
```

---

## Cost Breakdown

### Free Tier (Testing)

- **GitHub Pages**: Free (public repos)
- **Render Free Plan**: Free
  - 750 hours/month
  - Spins down after inactivity
  - Slower startup time
  - Good for testing/demos

### Production Setup

- **GitHub Pages**: Free (public repos)
- **Render Starter Plan**: $7/month
  - Always on
  - Faster performance
  - Better for production use

---

## Next Steps

- ✅ GitHub Pages workflow created
- ✅ Render deployment workflow created
- ✅ Configuration verified

**To deploy:**
1. Copy workflow to ontario-environmental-data repo
2. Enable GitHub Pages in data repo settings
3. Run data publication workflow
4. Create Render web service
5. Deploy williams-treaties to Render

**Need help?** Check the [Render documentation](https://render.com/docs) or [GitHub Pages documentation](https://docs.github.com/en/pages).

---

## Alternative: Pure GitHub Pages (No Server)

If you want to avoid Render entirely and host everything on GitHub Pages, you would need to:

1. Convert Flask server to static site
2. Pre-generate all configuration as JSON
3. Use client-side JavaScript to load everything
4. Host both repos on GitHub Pages

This is more complex but 100% free. Let me know if you want help with this approach!
