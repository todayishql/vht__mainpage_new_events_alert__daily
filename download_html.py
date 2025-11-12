import sys
import requests
from typing import Optional


def download_html(url: str, output_file: str, timeout: int = 30) -> bool:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        return True
        
    except requests.exceptions.RequestException as e:
        return False
    except Exception as e:
        return False


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2]
    
    if not download_html(url, output_file):
        sys.exit(1)


if __name__ == "__main__":
    main()

