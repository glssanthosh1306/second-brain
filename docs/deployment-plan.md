# SecondSelf — Streamlit Deployment Plan

This guide details the step-by-step procedure to deploy the **SecondSelf** personal AI second brain app to **Streamlit Community Cloud** (primary) and provides alternative hosting configurations.

---

## 📋 Pre-Deployment Checklist

Before triggering deployment, ensure your local repository state meets all requirement checks:

### 1. Secrets & Privacy Audit
- [ ] Confirm `.env` is listed in `.gitignore` (never commit API keys to Git).
- [ ] Verify no hardcoded API keys exist in code files (`ask.py`, `classify.py`, `app.py`).
- [ ] Ensure personal notes inside `raw/` and `wiki/` are sanitized if deploying to a **public** repository.

### 2. Pre-Computed Index & Artifacts
To ensure fast cold starts (< 5 seconds) on Streamlit Cloud:
- [ ] Run `python pipeline.py` locally to generate up-to-date versions of:
  - `wiki/.index/embeddings.pkl`
  - `wiki/.index/note_registry.json`
  - `data/graph.json`
  - `static/graph.html`
- [ ] Commit these index and visualization artifacts to Git so Streamlit Cloud does not need to build embeddings from scratch on launch.

### 3. Dependencies Check (`requirements.txt`)
Confirm `requirements.txt` includes all necessary packages:
```text
python-dotenv>=1.0
requests>=2.31
pypdf>=3.0
groq>=0.4
sentence-transformers>=2.2
numpy>=1.24
scikit-learn>=1.3
python-frontmatter>=1.0
streamlit>=1.28
```

---

## 🚀 Option 1: Streamlit Community Cloud (Recommended)

Streamlit Community Cloud provides free, instant hosting directly integrated with your GitHub repository.

### Step 1: Push Repository to GitHub
Ensure all latest code and artifacts are committed and pushed to your remote GitHub repository:
```bash
git add .
git commit -m "Prepare Phase 4 for Streamlit Cloud deployment"
git push origin main
```

### Step 2: Connect to Streamlit Cloud
1. Navigate to **[share.streamlit.io](https://share.streamlit.io/)**.
2. Sign in with your **GitHub account**.
3. Click the **"New app"** button.

### Step 3: Configure App Settings
Fill in the deployment form:
- **Repository**: `your-username/secondself` (or your repo name)
- **Branch**: `main`
- **Main file path**: `app.py`
- **App URL**: Customize your preferred subdomain slug (e.g., `secondself-brain.streamlit.app`)

### Step 4: Set Environment Secrets
1. Click **"Advanced settings..."** at the bottom of the deployment form (or go to **Settings > Secrets** in the app dashboard).
2. Add your Groq API Key in TOML format:
   ```toml
   GROQ_API_KEY = "gsk_your_actual_groq_api_key_here"
   ```
3. Click **Save**.

### Step 5: Deploy
Click **Deploy!**. Streamlit Cloud will build the environment, install `requirements.txt`, and launch `app.py`.

---

## 🤗 Option 2: Hugging Face Spaces (Alternative)

If you prefer hosting on Hugging Face:

1. Create a new Space on **[huggingface.co/new-space](https://huggingface.co/new-space)**.
2. Select **Streamlit** as the Space SDK.
3. Clone the HF Space repository or link it to GitHub.
4. Add `GROQ_API_KEY` under **Settings > Variables and Secrets > Repository Secrets**.
5. Push the project files to the HF Space `main` branch.

---

## 🧪 Post-Deployment Verification Checklist

Once the public deployment URL is live, perform these tests:

- [ ] **App Load**: Public URL loads without errors or blank screens.
- [ ] **RAG Q&A**: Submit a question in the *"Ask Your Brain"* tab (e.g., *"What is my name?"* or *"What do I know about RAG?"*) and verify the synthesized answer displays with cited note badges.
- [ ] **Interactive Graph**: Switch to the *"Interactive Brain Graph"* tab and verify nodes and edges render smoothly via `vis-network`.
- [ ] **Sidebar Stats**: Confirm total note counts, auto-link metrics, and PARA breakdowns match expected counts.

---

## ⚠️ Troubleshooting & Edge Cases

| Issue | Root Cause | Solution |
|-------|------------|----------|
| **`RuntimeError: GROQ_API_KEY not set`** | Secrets not configured in Streamlit Cloud | Go to App Settings > Secrets and add `GROQ_API_KEY = "gsk_..."`. |
| **High Memory / Cold Start Timeout** | Downloading sentence transformer models on launch | `embeddings.pkl` is pre-computed; ensure `wiki/.index/embeddings.pkl` is committed to Git. |
| **Missing Notes / Empty Answers** | `note_registry.json` path mismatch | Re-run `python pipeline.py` locally and commit `wiki/.index/note_registry.json`. |
