FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

ENV PYTHONUNBUFFERED=1
ENV HF_HUB_ENABLE_HF_TRANSFER=1
# Point the Hugging Face cache at the network volume so the FLUX weights
# persist across cold workers instead of redownloading every time.
ENV HF_HOME=/runpod-volume/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir hf_transfer -r requirements.txt

COPY handler.py .

CMD ["python", "-u", "handler.py"]
