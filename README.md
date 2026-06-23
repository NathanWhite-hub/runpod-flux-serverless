# InvokeAI Serverless

InvokeAI on Runpod Serverless. The worker boots `invokeai-web` headless inside the container and proxies its session queue over localhost. You send an InvokeAI graph as the job payload, the worker enqueues it, waits for the run, and returns the rendered image as base64. It idles to zero between requests, so you pay only while a job runs.

[![Runpod](https://api.runpod.io/badge/NathanWhite-hub/runpod-invokeai-serverless)](https://console.runpod.io/hub/NathanWhite-hub/runpod-invokeai-serverless)

## What this is and is not

This runs InvokeAI's generation engine, not its interface. There is no canvas, no gallery, no workflow editor. Those need a live server, which is a GPU Pod that bills the whole time it stays up. Serverless is request in, image out. If you want the canvas, run InvokeAI as a Pod instead.

The worker speaks InvokeAI's graph format, the same structure the app sends when you click Invoke. It is the InvokeAI counterpart to a ComfyUI serverless worker: the worker is thin, the graph carries the work.

## Models live on a network volume

The container ships InvokeAI with no models. Generation needs at least one model installed under `INVOKEAI_ROOT`, and a serverless container has no persistent disk of its own. So models belong on a Runpod network volume.

One time setup:

1. Create a network volume in the Runpod console.
2. Attach it to a temporary GPU Pod running the same InvokeAI image, with `INVOKEAI_ROOT=/workspace/invokeai` pointed at the volume mount.
3. Open the InvokeAI UI on that Pod and install your models through the Model Manager. They write to the volume and register in the model DB.
4. Stop the Pod.
5. Attach the same volume to this serverless endpoint. `INVOKEAI_ROOT` defaults to `/runpod-volume/invokeai`, which is where serverless mounts a network volume. Point both at the same data directory.

After that, every cold worker reads the models straight from the volume.

## Getting a graph

A graph names its models by the key they were given at install time. The reliable way to get a correct graph:

1. In the InvokeAI UI on your Pod, set up the generation you want.
2. Open the browser developer tools, Network tab.
3. Click Invoke. Find the request to `enqueue_batch`.
4. Copy the JSON request body. The `batch` object inside it is what you send here.

Because that graph was built against the same `INVOKEAI_ROOT` your endpoint uses, the model keys match.

## API

### Ping

Send no graph to confirm the worker booted:

```json
{ "input": { "ping": true } }
```

Returns the running InvokeAI version.

### Generate

Send a graph:

```json
{
  "input": {
    "graph": {
      "nodes": { "...": "..." },
      "edges": [ "..." ]
    }
  }
}
```

Or send a full batch for iterations and seeds:

```json
{
  "input": {
    "batch": {
      "graph": { "nodes": {}, "edges": [] },
      "runs": 1
    }
  }
}
```

### Response

```json
{
  "status": "completed",
  "item_ids": [1],
  "image_names": ["a1b2c3.png"],
  "images": ["<base64 PNG>"]
}
```

A failed run returns `error`, `error_type`, and `error_message` from the queue item.

## Environment variables

| Key | Default | Purpose |
|-----|---------|---------|
| `INVOKEAI_ROOT` | `/runpod-volume/invokeai` | data directory with the model DB and models |
| `INVOKEAI_HOST` | `127.0.0.1` | host invokeai-web binds inside the container |
| `INVOKEAI_PORT` | `9090` | port invokeai-web binds inside the container |
| `INVOKEAI_QUEUE_ID` | `default` | queue id used for enqueue and polling |
| `INVOKEAI_BOOT_TIMEOUT` | `600` | seconds a cold worker waits for the API |
| `INVOKEAI_JOB_TIMEOUT` | `600` | seconds to wait for one generation |
| `INVOKEAI_POLL_INTERVAL` | `1.0` | seconds between queue status checks |

## Deploy through the Hub

1. Push this repo and cut a GitHub Release. The Hub indexes releases, not commits.
2. In the Runpod console open the Hub, Get Started under Add your repo, paste the URL.
3. The validator sends a ping, so the build passes by booting InvokeAI on an empty `/tmp/invokeai`. It does not generate, since the validator has no volume.
4. After approval, deploy, attach your prepared network volume, and set `INVOKEAI_ROOT` to the volume path.

To skip the validator entirely, rename `.runpod/tests.json` to `.runpod/tests_.json` before the release.

## Deploy without the Hub

```bash
docker build -t YOUR_DOCKERHUB_USER/invokeai-serverless:1.0.0 .
docker push YOUR_DOCKERHUB_USER/invokeai-serverless:1.0.0
```

Create a Serverless endpoint on that image, attach the network volume, set `INVOKEAI_ROOT`.

## Known rough edges

Cold starts are slow. The InvokeAI image is large and the app boots a DB and scans models before the first request. Keep an active worker warm if latency matters.

The official image may install InvokeAI into a virtual environment. The Dockerfile installs runpod with `python -m pip`, which targets whatever `python` resolves to on the image PATH. If a build cannot import runpod, install into the same environment that owns `invokeai-web`.

First boot against an empty `INVOKEAI_ROOT` creates the directory and DB with no models. Ping works. Generation returns a model error until models are installed on the volume.

## License

Worker code is MIT. InvokeAI is Apache 2.0. Models carry their own licenses.
