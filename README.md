# Reverse From SynthID

A Docker image built through Github Actions with Git commit version tag

[![Docker Image Build/Publish tag with commit](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/docker-image-tag-commit.yml/badge.svg)](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/docker-image-tag-commit.yml) [![](https://img.shields.io/docker/v/xiaoyao9184/reverse-from-synthid)](https://hub.docker.com/r/xiaoyao9184/reverse-from-synthid)

[![HuggingFace Space Sync](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/hf-space-sync.yml/badge.svg)](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/hf-space-sync.yml) [![](https://img.shields.io/badge/HuggingFace-space-ff9f44?logo=huggingface)](https://huggingface.co/spaces/xiaoyao9184/reverse-from-synthid)

[![ModelScope Studio Sync](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/ms-studio-sync.yml/badge.svg)](https://github.com/xiaoyao9184/reverse-from-synthid/actions/workflows/ms-studio-sync.yml) [![](https://img.shields.io/badge/ModelScope-sudio-644cfd?logo=modelscope)](https://modelscope.ai/studios/xiaoyao9184/reverse-from-synthid)

## Why

I found that Reverse-Engineering SynthID is useful as an image watermark research tool,
but the upstream project is source-oriented and does not provide a ready-to-run Docker image or hosted Gradio Space.

This project packages [reverse-SynthID](./reverse-SynthID) with a Gradio interface,
then uses GitHub Actions, Docker Hub, GitHub Container Registry, and Hugging Face Spaces to build and publish runnable artifacts,
aiming to keep the deployment process as clean as possible without custom release steps.

## Tags

The images of this project will be published to Docker Hub under the repository [xiaoyao9184/reverse-from-synthid](https://hub.docker.com/r/xiaoyao9184/reverse-from-synthid).

The same image is also published to GitHub Container Registry as `ghcr.io/xiaoyao9184/reverse-from-synthid`.

The default image name format is `${DOCKERHUB_USERNAME}/reverse-from-synthid`.

Currently, only the `linux/amd64` platform is supported.

When the source project, Gradio app, Docker build files, or workflow files are updated and pushed to this project,
the [docker-image-tag-commit](./.github/workflows/docker-image-tag-commit.yml) job builds an image for the current project commit.
The commit-based image tag is the short commit id of this project repository,
generated from the GitHub Actions checkout with `git rev-parse --short HEAD`.
For example, a project commit `0123456789abcdef` will publish `${DOCKERHUB_USERNAME}/reverse-from-synthid:0123456`.

The workflow also publishes `latest` for the most recent successful build on the configured branches.

## Model

The Docker image includes the codebooks and artifacts that are already committed in [reverse-SynthID/artifacts](./reverse-SynthID/artifacts).

The image does not include external Hugging Face model files such as `stabilityai/sd-vae-ft-mse`.
When running online, required model files will be downloaded automatically and cached under `/root/.cache`.

If you need to run offline, pre-download the model files into the local [cache](./cache) directory,
mount it to `/root/.cache`, and enable Hugging Face offline mode.
See [cache/README.md](./cache/README.md) for detailed instructions.

## Service

By default, the Docker container runs the Gradio App provided by this project.
The app wraps the `reverse-SynthID` detector and bypass pipelines, including V1, V2, V3, and V4 codebook-based workflows.

The source code for the Gradio App is located in the [gradio](./gradio) directory of this project.
A demo of this project is also available and auto-synced on Hugging Face Spaces: [xiaoyao9184/reverse-from-synthid](https://huggingface.co/spaces/xiaoyao9184/reverse-from-synthid)
A demo of this project is also available and auto-synced on Model Scope Studios: [xiaoyao9184/reverse-from-synthid](https://modelscope.ai/studios/xiaoyao9184/reverse-from-synthid)

To run the Gradio App with Docker Compose, choose the runtime that matches your machine:

```bash
# GPU runtime
docker compose -f docker/up.gradio@gpu/docker-compose.yml up

# CPU runtime
docker compose -f docker/up.gradio@cpu/docker-compose.yml up
```

The service listens on port `7860`.

The GPU compose file sets `TORCH_DEVICE=cuda` and requests an NVIDIA GPU.
The CPU compose file sets `TORCH_DEVICE=cpu`.
Both compose files mount [cache](./cache) into `/root/.cache` and set `HF_HUB_OFFLINE=true`,
so make sure the required model files are already available before using those compose files as-is.

## Change

You can fork this project and build your own image.
You will need to provide the following variables: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `HF_USERNAME`, `HF_TOKEN`, `MODELSCOPE_USERNAME`, `MODELSCOPE_TOKEN`.
GitHub Container Registry publishing uses the built-in `GITHUB_TOKEN`.

See [docker/login-action](https://github.com/docker/login-action#docker-hub) for Docker Hub login details.
