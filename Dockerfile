# ── Base image ─────────────────────────────────────────────────────
FROM python:3.11-slim

# HF Spaces runs as user 1000 — set up early
RUN useradd -m -u 1000 appuser

# System deps for sentence-transformers + chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App source ─────────────────────────────────────────────────────
COPY . .

# Pre-download sentence-transformer model so first request isn't slow
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Seed ChromaDB at build time so the vector store is ready immediately
RUN python seed_vectorstore.py

# Fix permissions for HF Spaces user
RUN chown -R appuser:appuser /app
USER appuser

# ── Ports ──────────────────────────────────────────────────────────
# HF Spaces exposes port 7860 publicly — we route everything there via Streamlit
EXPOSE 7860

# ── Supervisord — runs FastAPI + Streamlit together ────────────────
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
