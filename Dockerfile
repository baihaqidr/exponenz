FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose default Hugging Face Spaces / Web port
ENV PORT=7860
EXPOSE 7860

CMD ["python", "run_dashboard.py"]
