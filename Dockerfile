FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Ensure playwright chromium is available
RUN playwright install chromium

# Copy application files
COPY . .

# Use built-in pwuser (UID 1000) provided by the Playwright base image
RUN mkdir -p /ms-playwright && chown -R pwuser:pwuser /app /ms-playwright
USER pwuser

# Hugging Face Spaces uses 7860; Render/others can override with PORT env var
ENV PORT=7860
EXPOSE 7860 8501

CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-7860} --server.address=0.0.0.0 --server.headless=true"]
