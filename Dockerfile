FROM ghcr.io/invoke-ai/invokeai:latest

# Clear the base image entrypoint so our handler runs instead of invokeai-web.
ENTRYPOINT []

ENV PYTHONUNBUFFERED=1
ENV INVOKEAI_ROOT=/runpod-volume/invokeai
ENV INVOKEAI_HOST=127.0.0.1
ENV INVOKEAI_PORT=9090

# Add the serverless deps into the same python env that runs invokeai-web.
RUN python -m pip install --no-cache-dir runpod requests

WORKDIR /workspace
COPY handler.py /workspace/handler.py

CMD ["python", "-u", "/workspace/handler.py"]
