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

Ansible escalates with `sudo.ws` (classic sudo) rather than Ubuntu's default sudo-rs,
because sudo-rs rewrites the password prompt and Ansible stops recognising it.

## Adding models

Edit `inventory/host_vars/homelab-pro/models.yml` and re-run with `--tags llama_swap` or
`--tags comfyui`. Ansible downloads missing files (verifying `sha256` when given) and, for
LLMs, regenerates the llama-swap config and recreates its container. Removing an entry does
not delete its files from `/srv/models`.

## What the roles do

- **host**: removes AMD's `amdgpu-dkms` in favour of the kernel's in-box driver, raises the
  GPU's GTT limit to `gpu_gtt_gib` (default 112 GiB) via `ttm.pages_limit`, boots headless,
  sets the power profile, exempts `tailscaled` from the OOM killer, and reboots when the
  running kernel doesn't match. Every step checks real state, so a failed run is completed
  by the next one.
- **docker**: Docker Engine and the compose plugin from Docker's apt repo, plus a firewall
  rule that only lets tailnet traffic reach the published ports.
- **llama_swap**: the `unified-vulkan` image, which bundles llama-server built for Vulkan.
  Models load on first request, one at a time, and unload after `ttl` idle seconds. Each run
  ends by loading every model in turn and generating one token, then fails listing any that
  didn't work. Set `llama_swap_smoke_test: false` to skip this.
- **comfyui**: a locally built image with PyTorch from AMD's gfx1151 wheel index
  (ROCm bundled in the wheels). Models live in `/srv/models/comfyui`; custom nodes, inputs,
  outputs and user data in `/srv/comfyui/data`.

## Things to know

- **Shared memory.** The CPU, LLMs and ComfyUI all draw from the same 121 GiB. A large LLM
  and a large diffusion model will not both fit. llama-swap unloads idle LLMs after their
  `ttl`; ComfyUI keeps models resident until restarted or told to free memory. Both
  containers are the OOM killer's preferred targets.
- **Network exposure.** dockerd binds the published ports to the Tailscale IPv4 address
  only, and the `docker-tailnet-only` unit drops traffic for that address unless it
  arrives on `tailscale0`, since Docker's port rules bypass ufw. The ports are not bound on
  the Tailscale IPv6 address, so clients that try IPv6 first fall back to IPv4.
  `net.ipv4.ip_nonlocal_bind=1` lets dockerd bind the address at boot before tailscaled
  has brought it up. Neither service has authentication: anyone on the tailnet can use them.
- **What's kept.** Logs hold model loads and timings, not prompts. llama-swap's request
  capture is off (`captureBuffer: 0`). ComfyUI saves images without the embedded
  workflow (`comfyui_embed_metadata`), keeps job history in memory until restart, and a
  daily timer deletes inputs and outputs older than `comfyui_retention_days` (default 30).
  `/srv/comfyui/data` is root-only.
- **Remote access is Tailscale SSH only**; OpenSSH is not running.
- **Pinned versions** live in role defaults: `llama_swap_image` (dated tags, published
  nightly) and the ComfyUI/PyTorch versions in `roles/comfyui/defaults/main.yml`. The
  ComfyUI image tag is derived from those versions and the Dockerfile, so changing any of
  them builds a new image and removes the old one.

## Recovery

GRUB shows its menu for 3 seconds at boot; pick *Advanced options* for an older kernel or
recovery mode. With a keyboard and screen attached:

- **No GPU after a reboot** (`/sys/module/amdgpu` missing): restore the in-box module with
  `sudo apt-get install --reinstall linux-modules-$(uname -r) && sudo update-initramfs -u`.
- **Undo the kernel parameters**: `sudo rm /etc/default/grub.d/90-evo-x2.cfg && sudo update-grub`.
- **Get the desktop back**: `sudo systemctl set-default graphical.target`, then reboot,
  and set `headless: false` so the next run doesn't revert it.
