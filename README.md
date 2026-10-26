# evo-x2

Ansible for the GMKtec EVO-X2 (`homelab-pro`, Ryzen AI Max+ 395, 128 GB unified memory):
llama.cpp behind [llama-swap](https://github.com/mostlygeek/llama-swap) for LLMs, and ComfyUI
for image generation, both in Docker and reachable only over Tailscale.

| Service | URL |
|---|---|
| llama-swap (OpenAI-compatible API + UI) | `http://homelab-pro:8080` |
| ComfyUI | `http://homelab-pro:8188` |

## Usage

```sh
uv tool install ansible-core          # needs >= 2.20 for the host's Python 3.14
ansible-galaxy collection install -r requirements.yml
ansible homelab-pro -b -K -m command -a id   # preflight: should print uid=0(root)
ansible-playbook site.yml -K          # -K prompts for the sudo password
```

Run one part with `--tags host|docker|llama_swap|comfyui`. For gated Hugging Face repos, set
`HF_TOKEN` on the machine you run Ansible from; it is read there and sent as a header.

## Adding models

The model list is kept out of git. On a fresh clone, start from the example:

```sh
cp inventory/models.example.yml inventory/host_vars/homelab-pro/models.yml
```

Edit `inventory/host_vars/homelab-pro/models.yml` and re-run with `--tags llama_swap` or
`--tags comfyui`. Ansible downloads missing files (verifying `sha256` when given) and, for
LLMs, regenerates the llama-swap config and recreates its container. Removing an entry does
not delete its files from `/srv/models`.

## What the roles do

- **host**: removes AMD's `amdgpu-dkms` in favour of the kernel's in-box driver, raises the
  GPU's GTT limit to `gpu_gtt_gib` (default 112 GiB) via `ttm.pages_limit`, boots headless,
  sets the power profile, exempts `tailscaled` from the OOM killer, and reboots when the
  running kernel doesn't match.
- **docker**: Docker Engine and the compose plugin from Docker's apt repo, plus a firewall
  rule that only lets tailnet traffic reach the published ports.
- **llama_swap**: the `unified-vulkan` image, which bundles llama-server built for Vulkan.
  Models load on first request, one at a time, and unload after `ttl` idle seconds. Each run
  ends by loading every model in turn and generating one token, then fails listing any that
  didn't work. Set `llama_swap_smoke_test: false` to skip this.
- **comfyui**: a locally built image with PyTorch from AMD's gfx1151 wheel index
  (ROCm bundled in the wheels). Models live in `/srv/models/comfyui`; custom nodes, inputs,
  outputs and user data in `/srv/comfyui/data`. Workflows in `roles/comfyui/files/workflows`
  appear in ComfyUI's Workflows panel. Since a workflow names the models it loads, only those
  allowed in `.gitignore` are committed; the rest stay local. They're copied only when
  missing, so edits saved there are kept; delete the file on the host to get the repo's
  version back. Custom nodes (`comfyui_custom_nodes` in `models.yml`) are single files
  pinned to a commit and a SHA-256; they run as root in the container, so read one before
  adding or bumping it.
