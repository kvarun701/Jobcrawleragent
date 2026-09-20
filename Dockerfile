FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Setup non-root user for Hugging Face Spaces & security
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Ensure playwright chromium is available
RUN playwright install chromium

# Copy application files
COPY --chown=user:user . .

# Switch to non-root user
USER user

# Hugging Face Spaces uses 7860; Render/others can override with PORT env var
ENV PORT=7860
EXPOSE 7860 8501

CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-7860} --server.address=0.0.0.0 --server.headless=true"]
