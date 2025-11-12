import json
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

# Constants
DEFAULT_HTML_FILE = 'y'
DEFAULT_OLD_FILE = 'latest.txt'
DEFAULT_NEW_FILE = 'new.txt'
DEFAULT_CONFIG_FILE = 'config.json'
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_CONNECT_TIMEOUT = 10
TELEGRAM_READ_TIMEOUT = 30
TELEGRAM_MAX_RETRIES = 3


def convert_date_format(date_str: str) -> str:
    if not date_str:
        return ""
    
    parts = date_str.strip().split('-')
    if len(parts) >= 2:
        day = parts[0].strip()
        month = parts[1].strip()
        return f"[{day}/{month}]"
    
    return date_str


def extract_news_from_html(html_content: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html_content, 'html.parser')
    news_list = []
    
    # Tìm tất cả các div có class="newsContent"
    news_content_divs = soup.find_all('div', class_='newsContent')
    
    for div in news_content_divs:
        title_link = div.find('h3')
        if not title_link:
            continue
        
        title_a = title_link.find('a', class_='title')
        if not title_a:
            title_a = title_link.find('a')
            if not title_a:
                continue
        
        title = title_a.get_text(strip=True)
        url = title_a.get('href', '')
        
        time_span = div.find('span', class_='time')
        date_raw = time_span.get_text(strip=True) if time_span else ""
        date = convert_date_format(date_raw)
        
        news_list.append({
            'date': date,
            'title': title,
            'url': url,
            'date_raw': date_raw
        })
    
    return news_list


def format_news_output(news_list: List[Dict[str, str]]) -> List[str]:
    return [news['title'].strip() for news in news_list if news.get('title', '').strip()]


def read_old_file(filepath: str) -> Set[str]:
    if not os.path.exists(filepath):
        return set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return set(lines)
    except (IOError, OSError):
        return set()


def load_config(config_file: str = DEFAULT_CONFIG_FILE) -> Optional[Dict[str, str]]:
    if not os.path.exists(config_file):
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"Lỗi khi đọc file config: JSON không hợp lệ - {e}")
        return None
    except (IOError, OSError) as e:
        print(f"Lỗi khi đọc file config: {e}")
        return None


def _truncate_telegram_message(message: str, total_items: int) -> str:
    if len(message) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        return message
    
    header = f"🔔 *Có {total_items} tin mới:*\n\n"
    remaining_chars = TELEGRAM_MAX_MESSAGE_LENGTH - len(header) - 50
    displayed_items = []
    current_length = len(header)
    
    lines = message.split('\n')
    header_lines = 2
    
    for i, line in enumerate(lines[header_lines:], 1):
        if not line.strip():
            continue
        if current_length + len(line) + 1 > remaining_chars:
            break
        displayed_items.append(line)
        current_length += len(line) + 1  # +1 cho newline
    
    message = header + '\n'.join(displayed_items)
    remaining_count = total_items - len(displayed_items)
    if remaining_count > 0:
        message += f"\n\n... và {remaining_count} tin khác"
    
    return message


def send_telegram_notification(
    bot_token: str,
    chat_id: str,
    new_items: List[str],
    max_retries: int = TELEGRAM_MAX_RETRIES
) -> bool:
    if not bot_token or not chat_id or not new_items:
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Tạo nội dung message
    message = f"🔔 *Có {len(new_items)} tin mới:*\n\n"
    for i, item in enumerate(new_items, 1):
        message += f"{i}. {item}\n"
    
    # Telegram giới hạn 4096 ký tự, cắt bớt nếu cần
    message = _truncate_telegram_message(message, len(new_items))
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=(TELEGRAM_CONNECT_TIMEOUT, TELEGRAM_READ_TIMEOUT)
            )
            response.raise_for_status()
            return True
            
        except requests.exceptions.Timeout as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Timeout khi gửi Telegram (lần thử {attempt + 1}/{max_retries}), "
                      f"thử lại sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Lỗi timeout khi gửi Telegram notification sau {max_retries} lần thử: {e}")
                return False
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Lỗi khi gửi Telegram (lần thử {attempt + 1}/{max_retries}): {e}, "
                      f"thử lại sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Lỗi khi gửi Telegram notification sau {max_retries} lần thử: {e}")
                return False
                
        except Exception as e:
            print(f"Lỗi không mong đợi khi gửi Telegram notification: {e}")
            return False
    
    return False


def _write_file(filepath: str, content: List[str]) -> bool:
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for line in content:
                f.write(f"{line}\n")
        return True
    except (IOError, OSError) as e:
        print(f"Lỗi khi ghi file {filepath}: {e}")
        return False


def compare_and_update(
    new_titles: List[str],
    old_filepath: str,
    new_filepath: Optional[str] = None,
    telegram_bot_token: Optional[str] = None,
    telegram_chat_id: Optional[str] = None
) -> Tuple[bool, List[str]]:
    old_titles = read_old_file(old_filepath)
    
    new_titles_set = set(new_titles)
    
    new_items = list(new_titles_set - old_titles)
    
    has_changes = (new_titles_set != old_titles)
    
    if has_changes:
        if new_items and new_filepath:
            if _write_file(new_filepath, new_items):
                print(f"Đã tạo file tin mới: {new_filepath} ({len(new_items)} tin mới)")
        elif new_filepath and os.path.exists(new_filepath):
            try:
                os.remove(new_filepath)
            except (IOError, OSError) as e:
                print(f"Lỗi khi xóa file tin mới: {e}")
        
        # Gửi thông báo Telegram nếu có tin mới
        if new_items and telegram_bot_token and telegram_chat_id:
            if send_telegram_notification(telegram_bot_token, telegram_chat_id, new_items):
                print(f"Đã gửi thông báo Telegram ({len(new_items)} tin mới)")
        
        # Update file cũ bằng nội dung mới
        if _write_file(old_filepath, new_titles):
            print(f"Đã cập nhật file cũ: {old_filepath}")
    else:
        print("Không có thay đổi, file giữ nguyên")
        # Nếu không có thay đổi và file new tồn tại, xóa nó
        if new_filepath and os.path.exists(new_filepath):
            try:
                os.remove(new_filepath)
                print(f"Đã xóa file tin mới (không có thay đổi): {new_filepath}")
            except (IOError, OSError):
                pass 
    
    return has_changes, new_items


def get_telegram_credentials() -> Tuple[Optional[str], Optional[str]]:
    bot_token = None
    chat_id = None
    
    is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_ci:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
    else:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            config = load_config(DEFAULT_CONFIG_FILE)
            if config:
                if not bot_token:
                    bot_token = config.get('telegram_bot_token')
                if not chat_id:
                    chat_id = config.get('telegram_chat_id')
    
    if len(sys.argv) >= 6:
        bot_token = sys.argv[4]
        chat_id = sys.argv[5]
    
    return bot_token, chat_id


def parse_arguments() -> Tuple[str, str, str]:
    html_file = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_HTML_FILE
    old_file = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_OLD_FILE
    new_file = sys.argv[3] if len(sys.argv) >= 4 else DEFAULT_NEW_FILE
    
    return html_file, old_file, new_file


def main() -> None:
    html_file, old_file, new_file = parse_arguments()
    
    if html_file == DEFAULT_HTML_FILE:
        print(f"Sử dụng file mặc định: {html_file}")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"Đã đọc file: {html_file}\n")
        
        news_list = extract_news_from_html(html_content)
        formatted = format_news_output(news_list)
        
        for title in formatted:
            print(title)
        
        bot_token, chat_id = get_telegram_credentials()
        
        has_changes, new_items = compare_and_update(
            formatted,
            old_file,
            new_file,
            telegram_bot_token=bot_token,
            telegram_chat_id=chat_id
        )
        
        if new_items:
            for item in new_items:
                print(f"  - {item}")
    
    except FileNotFoundError:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"✗ Lỗi: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
