import FinanceDataReader as fdr
import pandas as pd
import os

def main():
    print("KRX 종목 리스트 다운로드 중...")
    try:
        stocks = fdr.StockListing('KRX')
        print(f"다운로드 성공: {len(stocks)}개 종목")
        
        filename = "krx_stocks.csv"
        stocks.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"'{filename}' 파일 저장 완료.")
    except Exception as e:
        print(f"다운로드 실패: {e}")

if __name__ == "__main__":
    main()
