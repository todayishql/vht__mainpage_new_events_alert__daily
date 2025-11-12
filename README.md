# RSS News Extractor with Telegram Notification

A Python script that extracts news from HTML and sends Telegram notifications when new items are detected.

## Installation

```bash
pip install -r requirements.txt
```

### For GitHub Actions

Configure secrets in your repository:
- Go to: Settings → Secrets and variables → Actions
- Add the following secrets:
  - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
  - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
  - `NEWS_URL`: URL of the website to monitor

## Usage

### Command Line

```bash
python extract_news.py <html_file> <latest_file> <new_file>
```

**Parameters:**
- `html_file`: HTML file to parse (default: `y`)
- `latest_file`: File to store/compare previous news list (default: `latest.txt`)
- `new_file`: File to store new items (default: `new.txt`)

### Credential Priority

1. Environment variables (for GitHub Actions)
2. `config.json` file (for local development)
3. Command line arguments (overrides all)

## How It Works

1. Extracts news titles from HTML by finding elements with class `newsContent`
2. Compares with previous list stored in `latest.txt`
3. If new items are found:
   - Creates `new.txt` with new items
   - Sends Telegram notification
   - Updates `latest.txt` with current list
4. If no changes: Does nothing

## GitHub Actions Workflow

The workflow runs automatically on a schedule:
- **Schedule**: Every hour from 9:05 to 15:05 (Vietnam time, GMT+7)
- **Days**: Monday to Friday
- **Cron**: `5 2-8 * * 1-5` (UTC)

### Workflow Steps

1. Checkout repository
2. Setup Python environment
3. Install dependencies
4. Download HTML from URL (if `NEWS_URL` is configured)
5. Run extraction script
6. Commit and push `latest.txt` if changes are detected

The script automatically detects CI/CD environment and uses secrets from environment variables instead of `config.json`.

## Getting Telegram Credentials

**Bot Token:**
1. Find `@BotFather` on Telegram
2. Send `/newbot` and follow instructions
3. Copy the provided token

**Chat ID:**
1. Find `@userinfobot` on Telegram
2. Send any message
3. Copy your Chat ID from the response

## Notes

- `latest.txt` is committed to preserve state between workflow runs
- The script supports retry mechanism for Telegram API calls with exponential backoff
- Messages are automatically truncated if they exceed Telegram's 4096 character limit
