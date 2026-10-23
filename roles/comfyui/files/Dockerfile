FROM ubuntu:24.04

# libatomic1 (HIP runtime) and libgomp1 (torch) are not bundled in the ROCm wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git libgl1 libglib2.0-0 python3.12 python3.12-venv \
        libatomic1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# AMD's per-arch index ships torch with the ROCm runtime bundled as wheels,
# so the image needs no system ROCm install.
ARG TORCH_INDEX
ARG TORCH_VERSION
ARG TORCHVISION_VERSION
ARG TORCHAUDIO_VERSION
RUN pip install --no-cache-dir --index-url "$TORCH_INDEX" \
        "torch==$TORCH_VERSION" "torchvision==$TORCHVISION_VERSION" "torchaudio==$TORCHAUDIO_VERSION" \
    && pip freeze | grep -E '^torch(vision|audio)?==' > /opt/torch-constraints.txt

# Fail the build, not the container start, if a library the wheels need is missing.
RUN python -c "import torch, torchvision, torchaudio; assert torch.version.hip, 'torch built without ROCm'"

ARG COMFYUI_VERSION
RUN git clone --depth 1 --branch "$COMFYUI_VERSION" https://github.com/Comfy-Org/ComfyUI.git /opt/comfyui \
    && pip install --no-cache-dir -r /opt/comfyui/requirements.txt -c /opt/torch-constraints.txt

WORKDIR /opt/comfyui
EXPOSE 8188
ENTRYPOINT ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
