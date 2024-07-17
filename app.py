import requests
from bs4 import BeautifulSoup
import schedule
import time
import logging
import os
import random
from datetime import datetime

# LINE Notify token
LINE_NOTIFY_TOKEN = "DERnEYFQrt5rIX1pGHQKuAbINRSkM1M9ohnBBYF8yJd"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Connection': 'keep-alive',
}

# 全局變量
MAX_REQUESTS_PER_HOUR = 1890
request_count = 0
start_time = time.time()

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_urls_from_file():
    url_file = 'jpvendome_url.txt'
    urls = []
    if os.path.exists(url_file):
        with open(url_file, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
    return urls

def send_line_notify(message, url=None):
    notify_url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    data = {
        "message": message
    }
    if url:
        data["message"] += f"\n商品網址: {url}"
    
    response = requests.post(notify_url, headers=headers, data=data)
    
    if "添加URL:" in message or "更新URL:" in message:
        new_url = message.split(":")[1].strip()
        with open('myfone_url.txt', 'w') as file:
            file.write(new_url)
        send_line_notify(f"URL已更新為: {new_url}")

def check_website(url):
    global request_count, start_time
    current_time = time.time()
    if current_time - start_time > 3600:
        request_count = 0
        start_time = current_time
    if request_count >= MAX_REQUESTS_PER_HOUR:
        logging.warning("已達到每小時最大請求次數")
        return

    try:
        logging.info(f"正在檢查網站: {url}")
        
        # 添加重試機制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                request_count += 1
                break
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # 指數退避

        
        soup = BeautifulSoup(response.text, 'html.parser')
        
       
        # 尋找 "已售完" 按鈕
        sold_out_button = soup.find('button', class_='single_add_to_cart_button', string='已售完')
        
        current_time = datetime.now()
        
        if sold_out_button:
            # 找到 "已售完" 按鈕，表示商品正在補貨中
            if current_time.minute == 0 and current_time.second in [1, 21, 41, 59]:
                # 整點報告 －－ 先不用

                # send_line_notify(f"=== 整點報告：產品仍在補貨中 === 時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}", url)
                print('整點-官方網站產品補貨中')
            else:
                print(f"產品仍在補貨中 時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')} URL: {url}")
        else:
            # 沒有找到 "已售完" 按鈕，可能表示商品已經可以購買
            send_line_notify("產品可能已經可以購買了！")
            send_line_notify("💎💎💎 官方網站產品狀態已更改，產品可能已經可以購買了！ 💎💎💎", url)
            # print('官方網站產品可能可以購買了')
        
        logging.info(f"當前請求次數：{request_count}")
        
    except requests.RequestException as e:
        if "403" in str(e):
            logging.error(f"可能被封禁，暫停檢查一段時間 URL: {url}")
            print(f"可能被封禁，暫停檢查一段時間 URL: {url}")
            time.sleep(3600)  # 暫停1小時
        else:
            logging.error(f"檢查網站時發生錯誤: {e} URL: {url}")
            print(f"檢查網站時發生錯誤: {e} URL: {url}")

def run_check():
    current_time = datetime.now()
    if current_time.second in [1, 31]:
        urls = get_urls_from_file()
        for url in urls:
            check_website(url)

# 設置每秒執行一次檢查
schedule.every(1).seconds.do(run_check)

def handle_line_input(message):
    print('接收到的文字：', message)
    if message.startswith("添加URL:"):
        new_url = message.split("添加URL:")[1].strip()
        with open('pchome_url.txt', 'a') as file:
            file.write(f"\n{new_url}")
        send_line_notify(f"新URL已添加: {new_url}")
    elif message.startswith("更新URL:"):
        new_url = message.split("更新URL:")[1].strip()
        with open('pchome_url.txt', 'w') as file:
            file.write(new_url)
        send_line_notify(f"URL已更新為: {new_url}")
    else:
        send_line_notify("無效的命令。使用'添加URL:新網址'來添加新的監控網址，或'更新URL:新網址'來更新現有網址。")

def get_line_input():
    # 這個函數需要您實現，用於獲取 LINE 的輸入
    # 這裡只是一個示例，實際實現可能需要使用 LINE API 或其他方法
    return None

# 主循環
if __name__ == "__main__":
    while True:
        schedule.run_pending()

        # 檢查是否有來自 LINE 的新輸入
        line_input = get_line_input()
        if line_input:
            handle_line_input(line_input)

        time.sleep(1)
