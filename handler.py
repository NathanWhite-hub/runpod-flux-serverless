import base64
import io
import os
import time

import runpod
import torch
from diffusers import FluxPipeline

MODEL_ID = os.environ.get("MODEL_ID", "black-forest-labs/FLUX.1-dev")
QUANTIZE = os.environ.get("QUANTIZE", "false").lower() in ("true", "1", "yes")

DEFAULT_STEPS = int(os.environ.get("DEFAULT_STEPS", "28"))
DEFAULT_GUIDANCE = float(os.environ.get("DEFAULT_GUIDANCE", "3.5"))

DTYPE = torch.bfloat16
PIPE = None


def load_pipeline():
    """Load FLUX once and keep it warm for the life of the worker."""
    global PIPE
    if PIPE is not None:
        return PIPE

    pipe = FluxPipeline.from_pretrained(MODEL_ID, torch_dtype=DTYPE)

    if QUANTIZE:
        from optimum.quanto import freeze, qfloat8, quantize

        quantize(pipe.transformer, weights=qfloat8)
        freeze(pipe.transformer)
        quantize(pipe.text_encoder_2, weights=qfloat8)
        freeze(pipe.text_encoder_2)

    if torch.cuda.is_available():
        if QUANTIZE:
            pipe.to("cuda")
        else:
            pipe.enable_model_cpu_offload()
    else:
        pipe.to("cpu")

    PIPE = pipe
    return PIPE


def encode_png(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def handler(job):
    data = job.get("input") or {}

    prompt = data.get("prompt")
    if not prompt:
        return {"error": "Missing required field: prompt"}

    width = int(data.get("width", 1024))
    height = int(data.get("height", 1024))
    steps = int(data.get("num_inference_steps", DEFAULT_STEPS))
    guidance = float(data.get("guidance_scale", DEFAULT_GUIDANCE))
    images_per_prompt = int(data.get("num_images", 1))
    max_sequence_length = int(data.get("max_sequence_length", 512))

    seed = data.get("seed")
    if seed is None:
        seed = int.from_bytes(os.urandom(4), "big")
    seed = int(seed)
    generator = torch.Generator(device="cpu").manual_seed(seed)

    pipe = load_pipeline()

    start = time.time()
    output = pipe(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=guidance,
        num_images_per_prompt=images_per_prompt,
        max_sequence_length=max_sequence_length,
        generator=generator,
    )
    duration = round(time.time() - start, 2)

    return {
        "images": [encode_png(img) for img in output.images],
        "parameters": {
            "model": MODEL_ID,
            "seed": seed,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "width": width,
            "height": height,
            "quantized": QUANTIZE,
        },
        "seconds": duration,
    }


runpod.serverless.start({"handler": handler})
