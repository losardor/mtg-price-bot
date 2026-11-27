#!/usr/bin/env bash
# Deploy mtg-price-bot on makerfaire-nuc: pull committed code, sync the venv, restart.
# Never edit code on the NUC: commit on the Mac, push, then run this.
set -euo pipefail
cd "$HOME/bots/mtg-price-bot"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "refusing to deploy: local changes in $(pwd); commit them on the Mac instead" >&2
  exit 1
fi
git pull --ff-only
"$HOME/.local/bin/uv" pip install -q --python .venv/bin/python -r requirements.txt
mkdir -p "$HOME/.local/share/tgbots/mtg-price-bot"
systemctl --user restart mtg-price-bot
sleep 5
systemctl --user --no-pager status mtg-price-bot | head -5
journalctl --user -u mtg-price-bot -n 15 --no-pager -o cat
