# 주식 필터링 대시보드 설치 및 실행 가이드

이 프로젝트를 다른 PC(또는 서버)에서 실행하기 위한 방법입니다.

## 1. 필수 프로그램 설치
먼저 **Python(파이썬)**이 설치되어 있어야 합니다.
- [Python 다운로드](https://www.python.org/downloads/) (3.9 버전 이상 권장)
- 설치 시 **"Add Python to PATH"** 옵션을 반드시 체크해주세요.

## 2. 프로젝트 파일 복사
다음 파일들을 새 PC의 원하는 폴더(예: `C:\stock_project`)로 복사합니다.
- `stock_filter.py`
- `dashboard.py`
- `requirements.txt`
- (선택) `stock_data` 폴더 (기존 데이터를 가져가려면 복사, 아니면 새로 받아짐)

## 3. 라이브러리 설치
1. **명령 프롬프트(cmd)** 또는 **터미널**을 엽니다.
2. 프로젝트 폴더로 이동합니다.
   ```bash
   cd C:\stock_project
   ```
3. 필요한 라이브러리를 한 번에 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```

## 4. 실행 방법
설치가 완료되면 다음 명령어로 대시보드를 실행합니다.
```bash
streamlit run dashboard.py
```
잠시 후 브라우저가 열리며 대시보드가 실행됩니다.

## 5. 서버(VPS)에서 실행 시 팁
서버에서 실행할 때는 백그라운드에서 계속 돌아가게 하기 위해 `nohup`을 사용하거나 `tmux`를 쓰는 것이 좋습니다.
```bash
# 예시: 백그라운드 실행
nohup streamlit run dashboard.py &
```
