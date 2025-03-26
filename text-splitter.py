import re
import os
import sys
from datetime import datetime, timedelta

def split_chat_by_date(input_file):
    # output 디렉토리 경로 지정
    output_dir = '/home/wsl2-lucky/projects/medi-bot/output'
    os.makedirs(output_dir, exist_ok=True)
    print(f"'{output_dir}' 디렉토리가 생성되었습니다.")

    # 날짜 정규 표현식
    date_pattern = r'\d{4}년 \d{1,2}월 \d{1,2}일'
    
    # 날짜별로 대화 내용 저장
    chat_dict = {}

    # 입력 파일 읽기
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            chat_text = f.read()
            print(f"파일 '{input_file}'에서 대화 내용을 읽었습니다.")
    except Exception as e:
        print(f"파일 '{input_file}' 읽기 중 오류: {e}")
        return

    # 대화 내용을 줄 단위로 나눕니다.
    lines = chat_text.strip().split('\n')
    print(f"총 {len(lines)} 줄의 대화 내용이 있습니다.")

    current_date = None  # 초기화 추가
    
    for line in lines:
        # 날짜가 포함된 줄을 찾습니다.
        date_match = re.search(date_pattern, line)
        if date_match:
            # 날짜를 추출하고 형식 변환
            date_str = date_match.group()
            date_obj = datetime.strptime(date_str, '%Y년 %m월 %d일')

            # 메시지에서 시간 정보 추출
            time_match = re.search(r'(\d{1,2})시\s*(\d{1,2})분?', line)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                
                # 오전 4시 기준으로 날짜 결정
                if hour < 4 or (hour == 4 and minute == 0):
                    date_obj -= timedelta(days=1)

            current_date = date_obj.strftime('%Y년 %m월 %d일')
            if current_date not in chat_dict:
                chat_dict[current_date] = []
            print(f"날짜 '{current_date}' 발견: {line.strip()}")
        
        # 현재 날짜가 설정되어 있으면 대화 내용을 추가합니다.
        if current_date:
            chat_dict[current_date].append(line)

    # 입력 파일 이름에서 확장자를 제거하고 날짜를 붙여서 파일 이름 생성
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    # 각 날짜별로 파일로 저장
    for date, messages in chat_dict.items():
        # 날짜에서 숫자만 추출하여 YYYYMMDD 형식으로 변환
        numbers = re.findall(r'\d+', date)
        year, month, day = numbers
        
        # 출력 파일 이름 생성
        file_name = os.path.join(output_dir, f'{base_name}_{year}{month:>02}{day:>02}.txt')
        
        try:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('\n'.join(messages))
            print(f"'{file_name}' 파일이 생성되었습니다.")
        except Exception as e:
            print(f"파일 '{file_name}' 쓰기 중 오류: {e}")

# 명령행 인자에서 입력 파일 경로 받기
if len(sys.argv) != 2:
    print("사용법: python3 text-splitter.py <입력 파일 경로>")
    sys.exit(1)

input_file = sys.argv[1]

# 함수 실행
split_chat_by_date(input_file)
