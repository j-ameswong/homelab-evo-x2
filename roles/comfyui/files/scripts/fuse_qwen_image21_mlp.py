"""Fuse a Qwen-Image 2.1 checkpoint's split img_mlp.gate_layer/proj into img_mlp.gate_up.

ComfyUI builds the fused SwiGLU layout only when the checkpoint has gate_up, and LoRAs
trained on that layout (most kohya / ai-toolkit ones) cannot attach to the split weights.
Rows are concatenated as [gate_layer; proj], with their per-row scales, so it is lossless.

usage: python fuse_qwen_image21_mlp.py SRC DST
"""
import os
import sys

import torch
from safetensors import safe_open
from safetensors.torch import save_file

src, dst = sys.argv[1], sys.argv[2]
with safe_open(src, "pt") as f:
    metadata = f.metadata()
    sd = {k: f.get_tensor(k) for k in f.keys()}

out = {}
for k, v in sd.items():
    if ".img_mlp.proj." in k:
        continue
    if ".img_mlp.gate_layer." not in k:
        out[k] = v
        continue
    up = sd[k.replace(".gate_layer.", ".proj.")]
    fused = k.replace(".gate_layer.", ".gate_up.")
    if k.endswith(".comfy_quant"):
        if not torch.equal(v, up):
            sys.exit(f"{k}: gate_layer and proj are quantized differently, cannot fuse")
        out[fused] = v
    elif v.dim() == 2 and v.shape[1:] == up.shape[1:]:
        out[fused] = torch.cat([v, up])
    else:
        sys.exit(f"{k}: unexpected shape {tuple(v.shape)}, cannot fuse")

# Written aside and renamed, so an interrupted run never leaves a partial dst behind.
tmp = dst + ".partial"
save_file(out, tmp, metadata=metadata)
os.chmod(tmp, 0o644)
os.replace(tmp, dst)
print(f"fused {sum('.gate_up.' in k for k in out)} tensors: {len(sd)} -> {len(out)}")
