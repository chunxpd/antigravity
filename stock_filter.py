import FinanceDataReader as fdr
import pandas as pd
from tqdm import tqdm
import argparse
import datetime
import os
import sys

def get_krx_stocks():
    """KRX(코스피, 코스닥, 코넥스)에 상장된 모든 종목을 가져옵니다."""
    print("KRX 상장 종목을 가져오는 중...")
    stocks = fdr.StockListing('KRX')
    print(f"{len(stocks)}개의 종목을 찾았습니다.")
    return stocks

import concurrent.futures

import concurrent.futures
import multiprocessing

def fetch_worker(ticker, start_date, queue):
    """
    별도 프로세스에서 실행될 데이터 수집 함수
    """
    try:
        # fdr.DataReader가 내부적으로 requests를 쓰는데, 여기서도 타임아웃이 안 먹힐 수 있으므로
        # 프로세스 강제 종료가 가장 확실함
        df = fdr.DataReader(ticker, start=start_date)
        queue.put(df)
    except Exception:
        queue.put(pd.DataFrame())

def fetch_data_with_timeout(ticker, start_date, timeout=30):
    """
    multiprocessing을 사용하여 타임아웃을 강제합니다.
    """
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=fetch_worker, args=(ticker, start_date, queue))
    p.start()
    
    try:
        # 큐에서 데이터를 기다림 (타임아웃 적용)
        df = queue.get(timeout=timeout)
        
        # 데이터는 받았지만 프로세스가 아직 안 끝났을 수 있음
        p.join(timeout=1) 
        if p.is_alive():
            p.terminate()
            p.join()
            
        return df
    except multiprocessing.queues.Empty:
        # 타임아웃 (데이터가 안 옴)
        if p.is_alive():
            p.terminate()
            p.join()
        # 타임아웃 에러는 로그 없이 조용히 넘어가거나, 필요하면 로그 남김
        # 여기서는 빈 데이터프레임 반환으로 처리하여 진행 계속
        return pd.DataFrame()
    except Exception as e:
        if p.is_alive():
            p.terminate()
            p.join()
        return pd.DataFrame()

import re

def sanitize_filename(name):
    """파일명으로 사용할 수 없는 문자를 제거합니다."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_stock_data(ticker, name, start_date, update=False):
    """
    주가 데이터를 가져옵니다. 로컬 캐시가 있으면 사용하고,
    update가 True이거나 캐시가 없으면 다운로드합니다.
    파일명 형식: {ticker}_{name}.csv
    """
    data_dir = 'stock_data'
    os.makedirs(data_dir, exist_ok=True)
    
    safe_name = sanitize_filename(name)
    file_name = f"{ticker}_{safe_name}.csv"
    file_path = os.path.join(data_dir, file_name)
    
    # 구형 파일명(ticker.csv)이 존재하면 신규 형식으로 변경 시도
    old_file_path = os.path.join(data_dir, f'{ticker}.csv')
    if os.path.exists(old_file_path) and not os.path.exists(file_path):
        try:
            os.rename(old_file_path, file_path)
        except:
            pass 

    try:
        if os.path.exists(file_path):
            # 로컬 파일 로드
            df = pd.read_csv(file_path, parse_dates=['Date'], index_col='Date')
            
            # 데이터 시작일 확인 (요청한 start_date보다 데이터가 늦게 시작하면, 과거 데이터가 부족한 것임)
            # 여유를 조금 두기 위해 30일 정도 차이는 허용 (휴장일 등 고려)
            req_start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            if df.index[0] > req_start + datetime.timedelta(days=30):
                # 과거 데이터 부족 -> 새로 다운로드
                df = fetch_data_with_timeout(ticker, start_date, timeout=10)
                if not df.empty:
                    try:
                        df.to_csv(file_path)
                    except:
                        pass
                return df

            if update:
                # 마지막 날짜 확인 후 업데이트
                last_date = df.index[-1]
                # 오늘 날짜와 비교 (시간 제외)
                if last_date.date() < datetime.datetime.now().date():
                    new_start = (last_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                    try:
                        # 타임아웃 적용
                        new_df = fetch_data_with_timeout(ticker, new_start, timeout=30)
                        if not new_df.empty:
                            df = pd.concat([df, new_df])
                            df = df[~df.index.duplicated(keep='last')] # 중복 제거
                            df.to_csv(file_path)
                    except Exception as e:
                        pass # 업데이트 실패 시 기존 데이터 사용
            return df
        else:
            # 신규 다운로드 (타임아웃 적용)
            df = fetch_data_with_timeout(ticker, start_date, timeout=10)
            if not df.empty:
                try:
                    df.to_csv(file_path)
                except:
                    pass
            return df
    except Exception as e:
        # 오류 발생 시 다시 다운로드 시도
        try:
            df = fetch_data_with_timeout(ticker, start_date, timeout=30)
            if not df.empty:
                df.to_csv(file_path)
            return df
        except:
            return pd.DataFrame()

def process_stock(row, window, update, compare_days=None):
    """개별 종목 처리 함수 (병렬 실행용)"""
    ticker = row['Code']
    name = row['Name']
    
    try:
        # 이동평균 계산을 위해 충분한 데이터(약 2년 + 여유)를 가져옵니다.
        # 비교 기간이 있으면 그만큼 더 필요할 수 있음
        needed_days = max(window, compare_days if compare_days else 0)
        start_date = (datetime.datetime.now() - datetime.timedelta(days=needed_days*2 + 365)).strftime('%Y-%m-%d')
        
        # 캐싱된 데이터 가져오기 함수 사용
        df = get_stock_data(ticker, name, start_date, update=update)
        
        if len(df) < window:
            return None

        # N일 단순 이동평균(SMA) 계산
        ma_col = f'MA{window}'
        df[ma_col] = df['Close'].rolling(window=window).mean()
        
        # 최근 2개의 데이터 포인트 가져오기
        if len(df) < 2:
            return None
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        latest_close = latest['Close']
        latest_ma = latest[ma_col]
        prev_close = prev['Close']
        prev_ma = prev[ma_col]
        

        
        # 가격 비교 필터 (이동평균 필터와 별개로 동작하거나 함께 동작)
        # 여기서는 이동평균 조건이 만족되지 않아도, 가격 비교 조건이 있으면 체크하도록 로직을 수정해야 함
        # 하지만 사용자가 "이평선 말고"라고 했으므로, 이평선 조건은 무시하고 가격 비교만 할 수도 있어야 함.
        # 구조상 MA 필터가 메인이므로, compare_days가 설정되면 MA 조건 대신(혹은 추가로) 이걸 체크하는 식으로 변경
        
        result = {}
        ma_condition = False
        
        # MA 조건 체크
        if (pd.notna(latest_ma) and pd.notna(prev_ma) and
            prev_close <= prev_ma and latest_close > latest_ma):
            ma_condition = True
            
        compare_condition = False
        compare_price = 0
        
        if compare_days:
            # 데이터 충분한지 확인
            if len(df) >= compare_days + 2:
                # N일 전 종가 (T-N)
                # iloc[-1]이 오늘, iloc[-2]가 어제(T-1)
                # T-N은 iloc[-(N+1)]
                past_data = df.iloc[-(compare_days + 1)]
                past_close = past_data['Close']
                compare_price = past_close
                
                # 조건: 전날 종가가 N일 전 종가를 돌파 (Prev_Close > Past_Close)
                if prev_close > past_close:
                    compare_condition = True
        
        # 결과 반환 로직
        # 1. compare_days가 없으면 기존 MA 조건만 본다.
        # 2. compare_days가 있으면 MA 조건 무시하고(또는 AND/OR?) 사용자의 요청은 "이평선 말고" 였으므로
        #    compare_days가 있으면 그것만 만족해도 리턴하도록 함.
        
        if (compare_days and compare_condition) or (not compare_days and ma_condition):
             return {
                'Code': ticker,
                'Name': name,
                'Close': latest_close,
                f'MA{window}': round(latest_ma, 2) if pd.notna(latest_ma) else 0,
                'Prev_Close': prev_close,
                f'Prev_MA{window}': round(prev_ma, 2) if pd.notna(prev_ma) else 0,
                'Ratio': round((latest_close / latest_ma - 1) * 100, 2) if pd.notna(latest_ma) and latest_ma != 0 else 0,
                'Compare_Price': compare_price if compare_days else 0
            }
            
    except Exception as e:
        return None
    return None

def calculate_ma_and_filter(stocks, window=300, limit=None, update=False, compare_days=None):
    """
    병렬 처리를 이용하여 주가 데이터를 가져오고 필터링합니다.
    """
    results = []
    
    if limit:
        print(f"테스트를 위해 상위 {limit}개 종목만 분석합니다.")
        stocks = stocks.head(limit)
        
    total = len(stocks)
    print(f"병렬 처리 시작 (Workers: 4)...")
    
    # 병렬 처리 (ProcessPoolExecutor 대신 ThreadPoolExecutor 사용 + 내부에서 multiprocessing.Process)
    # 이유: ThreadPool이 가볍고, 내부에서 개별적으로 Process를 띄워 타임아웃 제어하는 구조가 더 안정적일 수 있음
    # 다만 너무 많은 프로세스 생성 부하를 줄이기 위해 workers 수를 조절
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # 각 종목에 대해 process_stock 함수 실행 예약
        future_to_stock = {executor.submit(process_stock, row, window, update, compare_days): row['Code'] for _, row in stocks.iterrows()}
        
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_stock):
            completed_count += 1
            
            # 진행 상황 출력 (10개 단위로)
            if completed_count % 10 == 0 or completed_count == total:
                sys.stdout.write(f"\rPROGRESS:{completed_count}/{total}")
                sys.stdout.flush()
                
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                pass

    print() # 줄바꿈
    return results

def main():
    parser = argparse.ArgumentParser(description="이동평균선을 상향 돌파한 KRX 종목 필터링")
    parser.add_argument('--window', type=int, default=300, help="이동평균선 기간 (기본값: 300)")
    parser.add_argument('--limit', type=int, help="분석할 종목 수 제한 (테스트용)")
    parser.add_argument('--output', type=str, help="결과를 저장할 CSV 파일명 (미지정 시 자동 생성)")
    parser.add_argument('--update', action='store_true', help="기존 데이터가 있어도 최신 데이터로 업데이트 시도")
    parser.add_argument('--compare-days', type=int, help="N일 전 종가와 비교하여 필터링 (N일 전 종가 > 전일 종가)")
    args = parser.parse_args()

    window = args.window
    output_file = args.output if args.output else f'stocks_above_{window}ma.csv'

    stocks = get_krx_stocks()
    
    # update 인자 전달
    filtered_stocks = calculate_ma_and_filter(stocks, window=window, limit=args.limit, update=args.update, compare_days=args.compare_days)
    
    if filtered_stocks:
        df_result = pd.DataFrame(filtered_stocks)
        cols = ['Code', 'Name', 'Close', f'MA{window}', 'Ratio', 'Prev_Close', f'Prev_MA{window}']
        if args.compare_days:
            cols.append('Compare_Price')
        df_result = df_result[cols]
        df_result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n분석 완료! 결과가 '{output_file}'에 저장되었습니다. (총 {len(df_result)}개 종목)")
        print(df_result.head())
    else:
        print(f"\n조건({window}일 이동평균 돌파)에 맞는 종목을 찾지 못했습니다.")

if __name__ == "__main__":
    # Windows에서 multiprocessing 사용 시 필요
    multiprocessing.freeze_support()
    main()
