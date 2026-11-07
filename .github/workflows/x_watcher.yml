name: X Gibson Watcher

on:
  repository_dispatch:
    types: [cron_trigger]
  workflow_dispatch:

jobs:
  watch:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run X Watcher
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          X_TARGET_USERNAME: ${{ secrets.X_TARGET_USERNAME }}
        run: python x_watcher.py

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add watched_tweets.json
          # 変更がある場合のみコミット＆プッシュする（未コミットの競合を防ぐ）
          git diff --staged --quiet || (git commit -m "Update watched tweets state" && git push origin main)
