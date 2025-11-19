# GitHub Pages Workflow for ontario-environmental-data

This directory contains a GitHub Actions workflow that needs to be deployed to the `ontario-environmental-data` repository.

## What This Workflow Does

The `publish-data-to-pages.yml` workflow:

1. **Triggers on:**
   - Manual workflow dispatch (via Actions tab)
   - Automatically after "Data Collection" workflow completes

2. **Actions:**
   - Creates an index.html page for data directory navigation
   - Uploads the entire `data/` directory as a GitHub Pages artifact
   - Deploys to GitHub Pages at: `https://robertsoden.github.io/ontario-environmental-data/`

3. **Result:**
   - All data files become accessible via HTTPS
   - Files available at: `https://robertsoden.github.io/ontario-environmental-data/data/processed/...`

## How to Deploy This Workflow

### Step 1: Copy to Data Repository

```bash
# Navigate to your ontario-environmental-data repository
cd /path/to/ontario-environmental-data

# Create .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy the workflow file
cp /path/to/williams-treaties/.github-workflows-for-data-repo/publish-data-to-pages.yml \
   .github/workflows/publish-data-to-pages.yml

# Commit and push
git add .github/workflows/publish-data-to-pages.yml
git commit -m "Add GitHub Pages deployment workflow"
git push origin main
```

### Step 2: Enable GitHub Pages

1. Go to the **ontario-environmental-data** repository on GitHub
2. Click **Settings** → **Pages**
3. Under **Build and deployment**:
   - Source: Select **GitHub Actions**
4. Save

### Step 3: Run the Workflow

**Option A: Manual Run**
1. Go to **Actions** tab
2. Select **Publish Data to GitHub Pages**
3. Click **Run workflow**

**Option B: Automatic**
- Workflow automatically runs after "Data Collection" workflow completes

### Step 4: Verify

After workflow completes, visit:
```
https://robertsoden.github.io/ontario-environmental-data/
```

Test a data file:
```
https://robertsoden.github.io/ontario-environmental-data/data/processed/boundaries/williams_treaty.geojson
```

## Workflow Configuration

### Permissions

The workflow requires:
- `contents: read` - To checkout repository
- `pages: write` - To deploy to GitHub Pages
- `id-token: write` - For Pages deployment authentication

### Concurrency

Only one deployment runs at a time:
```yaml
concurrency:
  group: "pages"
  cancel-in-progress: false
```

This prevents conflicts when multiple data updates happen simultaneously.

### What Gets Published

The workflow publishes the entire `data/` directory, which typically contains:
```
data/
├── processed/
│   ├── boundaries/
│   ├── charities/
│   ├── communities/
│   ├── fire/
│   ├── fuel/
│   ├── ndvi/
│   ├── dem/
│   └── ...
├── raw/
└── boundaries/
```

## Workflow File Structure

```yaml
name: Publish Data to GitHub Pages

on:
  workflow_dispatch:                    # Manual trigger
  workflow_run:
    workflows: ["Data Collection"]      # Auto-trigger after data collection
    types: [completed]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    # Creates index.html and uploads artifact

  deploy:
    # Deploys to GitHub Pages
```

## Troubleshooting

### Workflow doesn't appear in Actions tab

- Make sure you pushed the file to `.github/workflows/` directory
- Check file has `.yml` or `.yaml` extension
- Refresh the Actions tab

### Deployment fails with permissions error

- Verify GitHub Pages is enabled in repository settings
- Check repository has Pages permissions enabled
- Ensure workflow has correct permissions in YAML file

### Data files return 404

- Verify workflow completed successfully
- Check GitHub Pages deployment status in Settings → Pages
- Allow 1-2 minutes for Pages to propagate changes
- Ensure data files exist in `data/` directory before deployment

### Index page doesn't show

- Workflow creates `data/index.html` automatically
- If you want to customize it, edit the workflow file
- Or create `data/index.html` in your repo before running workflow

## Customization

### Change what gets published

Edit the `upload-pages-artifact` step:
```yaml
- name: Upload artifact
  uses: actions/upload-pages-artifact@v3
  with:
    path: 'data'  # Change this to publish different directory
```

### Add custom index page

Remove or modify the "Create index.html" step to use your own index.html.

### Trigger on different events

Add more triggers:
```yaml
on:
  workflow_dispatch:
  workflow_run:
    workflows: ["Data Collection"]
    types: [completed]
  push:
    paths:
      - 'data/**'  # Trigger on any data file changes
```

## Related Files

- **In williams-treaties repo:**
  - `.github/workflows/deploy-render.yml` - Deploys map server to Render
  - `.github/workflows/verify-deployment.yml` - Verifies deployment configuration
  - `DEPLOYMENT_GUIDE.md` - Complete deployment guide
  - `web/config/data_source.production.yaml` - Points to GitHub Pages URL

## Next Steps

After deploying this workflow:

1. ✅ Data is now hosted on GitHub Pages
2. ✅ Available at stable HTTPS URL
3. ✅ Ready to be consumed by williams-treaties map
4. 🔜 Deploy williams-treaties app to Render
5. 🔜 Configure app to use GitHub Pages data URL

See `DEPLOYMENT_GUIDE.md` for complete setup instructions.
