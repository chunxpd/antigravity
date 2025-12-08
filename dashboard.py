import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import plotly.graph_objects as go
import datetime
import subprocess
import os

# 페이지 설정
st.set_page_config(layout="wide", page_title="이동평균선 돌파 종목 분석")

# 제목
st.title("📈 이동평균선 돌파 종목 분석 made by Genius.")

# 사이드바 설정
st.sidebar.header("설정")
window_size = st.sidebar.number_input("이동평균선 기간 (일)", min_value=5, max_value=3000, value=300, step=10)
update_data = st.sidebar.checkbox("최신 데이터 채우기 (기존 데이터 활용)", value=False, help="체크하면 기존 파일에 없는 최신 날짜 데이터만 추가로 받아옵니다. (전체 다운로드보다 훨씬 빠름)")

# 분석 실행 버튼
if st.sidebar.button("분석 시작 (데이터 갱신)"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner(f"{window_size}일 이동평균선 기준으로 분석 중입니다... (시간이 다소 소요됩니다)"):
        try:
            # 명령어 구성
            import sys
            cmd = [sys.executable, "stock_filter.py", "--window", str(window_size)]
            if update_data:
                cmd.append("--update")

            # OS에 따른 인코딩 설정
            encoding_type = 'cp949' if os.name == 'nt' else 'utf-8'

            # stock_filter.py 실행 (Popen으로 실시간 출력 캡처)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding=encoding_type,
                bufsize=1 # Line buffered
            )
            
            # 초기 상태 표시
            status_text.text("데이터 준비 중... (KRX 종목 리스트 다운로드)")
            
            # 실시간 출력 읽기
            while True:
                # 한 줄씩 읽기
                line = process.stdout.readline()
                
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    # 진행률 파싱 (PROGRESS:현재/전체)
                    if line.startswith("PROGRESS:"):
                        try:
                            parts = line.split(":")[1].split("/")
                            current = int(parts[0])
                            total = int(parts[1])
                            progress = current / total
                            progress_bar.progress(progress)
                            status_text.text(f"진행 중: {current}/{total} ({progress*100:.1f}%)")
                        except:
                            pass
                    elif "KRX" in line:
                         status_text.text(line) # KRX 다운로드 메시지 표시
                    # else:
                        # print(f"DEBUG: {line}") # 디버깅용

            return_code = process.poll()
            
            if return_code == 0:
                progress_bar.progress(1.0)
                status_text.text("분석 완료!")
                st.success("분석이 완료되었습니다!")
            else:
                stderr = process.stderr.read()
                st.error(f"오류가 발생했습니다:\n{stderr}")
                
        except Exception as e:
            st.error(f"실행 중 오류 발생: {e}")

st.sidebar.markdown("---")
st.sidebar.header("과거 가격 비교 설정")
compare_days = st.sidebar.number_input("과거 비교 기간 (일)", min_value=1, max_value=1000, value=5, help="N일 전 종가가 전일 종가보다 높은 종목을 찾습니다.")

if st.sidebar.button("분석 시작 (가격 비교)"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with st.spinner(f"{compare_days}일 전 종가와 비교 분석 중입니다..."):
        try:
            import sys
            # MA 윈도우도 함께 전달하여 파일명이 일치하도록 함
            cmd = [sys.executable, "stock_filter.py", "--window", str(window_size), "--compare-days", str(compare_days)]
            if update_data:
                cmd.append("--update")

            # OS에 따른 인코딩 설정
            encoding_type = 'cp949' if os.name == 'nt' else 'utf-8'

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding=encoding_type,
                bufsize=1
            )
            
            status_text.text("데이터 준비 및 분석 중...")
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    if line.startswith("PROGRESS:"):
                        try:
                            parts = line.split(":")[1].split("/")
                            current = int(parts[0])
                            total = int(parts[1])
                            progress_bar.progress(current / total)
                            status_text.text(f"진행 중: {current}/{total}")
                        except:
                            pass
                    elif "KRX" in line:
                         status_text.text(line)

            return_code = process.poll()
            
            if return_code == 0:
                progress_bar.progress(1.0)
                status_text.text("분석 완료!")
                st.success("가격 비교 분석이 완료되었습니다!")
                # 결과 파일이 덮어씌워졌으므로 페이지 리로드 효과를 위해 rerun (또는 아래에서 로드)
                st.rerun()
            else:
                stderr = process.stderr.read()
                st.error(f"오류가 발생했습니다:\n{stderr}")
                
        except Exception as e:
            st.error(f"실행 중 오류 발생: {e}")

# 데이터 파일명 (window size에 따라 다름)
csv_file = f'stocks_above_{window_size}ma.csv'

# 데이터 로드 함수
# 데이터 로드 함수
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        # Code 컬럼을 문자열로 변환하고 6자리로 맞춤
        df['Code'] = df['Code'].astype(str).str.zfill(6)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

import re

def sanitize_filename(name):
    """파일명으로 사용할 수 없는 문자를 제거합니다."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

# 주가 데이터 로드 함수
@st.cache_data
def load_stock_data(ticker, name, window):
    # 로컬 캐시 확인 ({ticker}_{name}.csv)
    safe_name = sanitize_filename(name)
    file_name = f"{ticker}_{safe_name}.csv"
    cache_path = f'stock_data/{file_name}'
    
    # 구형 파일명 호환성 체크
    old_cache_path = f'stock_data/{ticker}.csv'
    
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=['Date'], index_col='Date')
    elif os.path.exists(old_cache_path):
        df = pd.read_csv(old_cache_path, parse_dates=['Date'], index_col='Date')
    else:
        # 캐시 없으면 다운로드 (혹시 모르니)
        start_date = (datetime.datetime.now() - datetime.timedelta(days=window*2 + 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start=start_date)
    
    df[f'MA{window}'] = df['Close'].rolling(window=window).mean()
    return df

# 메인 로직
df_stocks = load_data(csv_file)

if df_stocks.empty:
    st.info(f"아직 {window_size}일 기준 분석 결과가 없습니다. 사이드바의 '분석 시작' 버튼을 눌러주세요.")
else:
    st.sidebar.markdown("---")
    st.sidebar.header("종목 선택")
    
    # 종목 리스트 생성
    stock_options = df_stocks.apply(lambda x: f"{x['Name']} ({x['Code']}) - Ratio: {x['Ratio']}%", axis=1)
    selected_option = st.sidebar.selectbox("종목을 선택하세요", stock_options)
    
    if selected_option:
        # 선택된 종목 정보 추출
        selected_index = stock_options[stock_options == selected_option].index[0]
        selected_stock = df_stocks.iloc[selected_index]
        ticker = selected_stock['Code']
        name = selected_stock['Name']
        
        # 상세 정보 표시
        st.header(f"{name} ({ticker})")
        
        ma_col = f'MA{window_size}'
        prev_ma_col = f'Prev_MA{window_size}'
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("현재가", f"{selected_stock['Close']:,}원")
        col2.metric(f"{window_size}일 이동평균", f"{selected_stock[ma_col]:,}원")
        col3.metric(f"이격도 (현재가/{window_size}MA)", f"{selected_stock['Ratio']}%")
        col4.metric("전일 종가", f"{selected_stock['Prev_Close']:,}원", delta=f"{selected_stock['Close'] - selected_stock['Prev_Close']:,}원")

        # 차트 그리기
        st.subheader(f"주가 및 {window_size}일 이동평균선 차트")
        
        with st.spinner('차트 데이터를 불러오는 중...'):
            # 이름도 함께 전달
            df_chart = load_stock_data(ticker, name, window_size)
            


            if not df_chart.empty:
                # N일 전 주가 (비교용) - tail 자르기 전에 미리 계산해야 함
                shifted_col = None
                if compare_days > 0:
                     shifted_col = f'Close_{compare_days}d_ago'
                     df_chart[shifted_col] = df_chart['Close'].shift(compare_days)

                # 최근 400일 데이터만 표시 (혹은 window에 비례해서)
                display_days = max(400, window_size + 100)
                df_chart = df_chart.tail(display_days)
                
                fig = go.Figure()
                
                # 캔들스틱 차트
                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name='주가'
                ))
                
                # 이동평균선
                fig.add_trace(go.Scatter(
                    x=df_chart.index,
                    y=df_chart[f'MA{window_size}'],
                    line=dict(color='orange', width=2),
                    name=f'{window_size}일 이동평균선'
                ))

                # N일 전 주가 (비교용)
                if shifted_col and shifted_col in df_chart.columns:
                     fig.add_trace(go.Scatter(
                        x=df_chart.index,
                        y=df_chart[shifted_col],
                        line=dict(color='cyan', width=1, dash='dot'),
                        name=f'{compare_days}일 전 주가'
                    ))
                
                fig.update_layout(
                    height=600,
                    xaxis_rangeslider_visible=False,
                    title=f"{name} 주가 흐름",
                    yaxis_title="가격 (원)",
                    xaxis_title="날짜",
                    template="plotly_dark"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("차트 데이터를 불러올 수 없습니다.")

        # 데이터 테이블 표시
        st.subheader("전체 필터링 결과")
        
        # 정수형으로 변환 (원화 표기 위해 소수점 제거)
        numeric_cols = ['Close', f'MA{window_size}', 'Prev_Close', f'Prev_MA{window_size}', 'Compare_Price']
        for col in numeric_cols:
            if col in df_stocks.columns:
                df_stocks[col] = df_stocks[col].fillna(0).round(0).astype('int64')

        # 숫자 포맷 설정
        column_config = {
            "Close": st.column_config.NumberColumn("Close", format="localized"),
            f"MA{window_size}": st.column_config.NumberColumn(f"MA{window_size}", format="localized"),
            "Prev_Close": st.column_config.NumberColumn("Prev_Close", format="localized"),
            f"Prev_MA{window_size}": st.column_config.NumberColumn(f"Prev_MA{window_size}", format="localized"),
            "Ratio": st.column_config.NumberColumn("Ratio", format="%.2f%%"),
        }
        
        if 'Compare_Price' in df_stocks.columns:
            column_config['Compare_Price'] = st.column_config.NumberColumn(f"{compare_days}일 전 종가", format="localized")

        st.dataframe(
            df_stocks,
            column_config=column_config,
            hide_index=True
        )
