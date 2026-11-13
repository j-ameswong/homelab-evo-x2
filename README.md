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

Run one part with `--tags host|docker|llama_swap|comfyui|nix|agents`. For gated Hugging Face repos, set
`HF_TOKEN` on the machine you run Ansible from.

## Adding models

On a fresh clone, start from the example:

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
  ends by loading every model in turn and generating one token (or one embedding), then fails
  listing any that didn't work. Set `llama_swap_smoke_test: false` to skip this.
- **comfyui**: a locally built image with PyTorch from AMD's gfx1151 wheel index
  (ROCm bundled in the wheels). Models live in `/srv/models/comfyui`; custom nodes, inputs,
  outputs and user data in `/srv/comfyui/data`. Workflows in `roles/comfyui/files/workflows`
  appear in ComfyUI's Workflows panel.
- **nix**: multi-user Nix with flakes, and devenv's binary cache trusted.
- **agents**: makes the host a coding-agent server. Sets zsh as the login shell, enables
  lingering, makes the user Tailscale's operator (so T3 Code can use Tailscale Serve), clones
  [nix-config](https://github.com/j-ameswong/nix-config) to `~/nix-config` and applies its
  Home Manager config, then installs Claude Code, Codex, OpenCode, t3 and the T3 Code service.

## Coding agents

After the first `--tags nix,agents` run, finish setup over SSH. These logins are per machine
and not declarative:

```sh
gh auth login           # git pushes and PRs
claude                  # then /login
codex login
t3 pair --tailscale     # scan the QR code with the T3 Code app
```

Clone projects into `~/Projects`, where direnv loads each one's dev shell without asking.
Update the user config with `git -C ~/nix-config pull && home-manager switch --flake ~/nix-config`.
A timer updates the agent CLIs and t3 at 04:30 nightly, which restarts T3 Code.
