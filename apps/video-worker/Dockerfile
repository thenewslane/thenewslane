# Self-hosted LTX-Video inference worker
# Target: Vast.ai RTX 4090 spot instance (~$0.40/hr)
#
# Build:  docker build -t newslane-video-worker .
# Run:    docker run --gpus all -p 5001:5001 newslane-video-worker
# Push:   docker push <registry>/newslane-video-worker

FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# Install ffmpeg and system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app.py generator.py ./

# Pre-download the model during build so the container starts fast
# Comment this out if you want a smaller image and are happy to wait
# for the first-request download (~5 GB).
RUN python -c "from diffusers import LTXPipeline; import torch; LTXPipeline.from_pretrained('Lightricks/LTX-Video', torch_dtype=torch.bfloat16)" || true

EXPOSE 5001

CMD ["python", "app.py"]
