import FinanceDataReader as fdr
import pandas as pd
import os
import datetime
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import re

# 설정
DATA_DIR = 'stock_data'
MAX_WORKERS = 4  # 병렬 작업 수
DEFAULT_DAYS = 3000 # 약 12년

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def fetch_data(ticker, start_date):
    try:
        return fdr.DataReader(ticker, start=start_date)
    except Exception as e:
        return pd.DataFrame()

def process_stock(ticker, name):
    safe_name = sanitize_filename(name)
    file_path = os.path.join(DATA_DIR, f"{ticker}_{safe_name}.csv")
    old_file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    
    # 구형 파일 이름 변경
    if os.path.exists(old_file_path) and not os.path.exists(file_path):
        os.rename(old_file_path, file_path)
    
    today = datetime.datetime.now().date()
    # 어제 날짜까지의 데이터를 확보하는 것이 목표 (장 중이면 오늘거 포함)
    
    try:
        if os.path.exists(file_path):
            # 기존 파일 업데이트
            try:
                df = pd.read_csv(file_path, parse_dates=['Date'], index_col='Date')
                if df.empty:
                    raise ValueError("Empty file")
                
                last_date = df.index[-1].date()
                
                if last_date < today:
                    # 업데이트 필요
                    next_day = last_date + datetime.timedelta(days=1)
                    new_df = fetch_data(ticker, next_day.strftime('%Y-%m-%d'))
                    
                    if not new_df.empty:
                        df = pd.concat([df, new_df])
                        df = df[~df.index.duplicated(keep='last')] # 중복 제거
                        df.to_csv(file_path)
                        return f"Updated: {name} ({len(new_df)} rows added)"
                    else:
                         return f"No new data: {name}"
                else:
                    return f"Up to date: {name}"
            except Exception:
                # 파일 깨짐 등 문제 발생 시 새로 받기
                pass

        # 신규 다운로드 (또는 재다운로드)
        start_date = (datetime.datetime.now() - datetime.timedelta(days=DEFAULT_DAYS)).strftime('%Y-%m-%d')
        df = fetch_data(ticker, start_date)
        if not df.empty:
            df.to_csv(file_path)
            return f"Downloaded: {name} ({len(df)} rows)"
        else:
            return f"Failed to download: {name}"
            
    except Exception as e:
        return f"Error {name}: {str(e)}"

def main():
    ensure_dir(DATA_DIR)
    
    print(f"[{datetime.datetime.now()}] Starting daily stock update...")
    
    # KRX 전 종목 가져오기
    try:
        stocks = fdr.StockListing('KRX')
        print(f"Found {len(stocks)} stocks.")
    except Exception as e:
        print(f"Failed to fetch stock list: {e}")
        return

    # 종목 리스트 변환
    stock_list = []
    for _, row in stocks.iterrows():
        stock_list.append((row['Code'], row['Name']))

    # 병렬 처리
    total = len(stock_list)
    completed = 0
    
    print("Updating stocks...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_stock, ticker, name): (ticker, name) for ticker, name in stock_list}
        
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            
            # 진행률 표시 (한 줄로 업데이트하거나 100개마다 출력)
            if completed % 50 == 0 or completed == total:
                print(f"[{completed}/{total}] {result}")

    print(f"[{datetime.datetime.now()}] Update finished.")

if __name__ == "__main__":
    main()
