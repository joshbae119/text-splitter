import re
import os
import sys
from datetime import datetime, timedelta

def split_chat_by_date(input_file):
    output_dir = '/home/wsl2-lucky/projects/medi-bot/output'
    os.makedirs(output_dir, exist_ok=True)
    print(f"'{output_dir}' 디렉토리가 생성되었습니다.")

    date_pattern = r'\d{4}년 \d{1,2}월 \d{1,2}일'
    time_pattern = r'(오전|오후)\s*(\d{1,2}):(\d{1,2})'

    chat_dict = {}
    current_date = None

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 필요 없는 라인 제거
                if '오픈채팅봇' in line or '님이 나갔습니다.' in line or '님이 들어왔습니다.' in line:
                    continue
                
                date_match = re.search(date_pattern, line)
                if date_match:
                    date_str = date_match.group()
                    date_obj = datetime.strptime(date_str, '%Y년 %m월 %d일')

                    time_match = re.search(time_pattern, line)
                    if time_match:
                        period = time_match.group(1)
                        hour = int(time_match.group(2))
                        minute = int(time_match.group(3))

                        if period == '오전':
                            hour_24 = 0 if hour == 12 else hour
                        else:
                            hour_24 = 12 if hour == 12 else hour + 12

                        if hour_24 < 4:
                            date_obj -= timedelta(days=1)

                    current_date = date_obj.strftime('%Y년 %m월 %d일')
                    if current_date not in chat_dict:
                        chat_dict[current_date] = []
                    print(f"조정된 날짜 '{current_date}' | 원본 라인: {line.strip()}")

                if current_date:
                    chat_dict[current_date].append(line.strip())

    except Exception as e:
        print(f"파일 '{input_file}' 읽기 중 오류: {e}")
        return

    base_name = os.path.splitext(os.path.basename(input_file))[0]

    for date, messages in chat_dict.items():
        numbers = re.findall(r'\d+', date)
        year, month, day = numbers
        file_name = os.path.join(output_dir, f'{base_name}_{year}{month.zfill(2)}{day.zfill(2)}.txt')
        
        try:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('\n'.join(messages))
            print(f"'{file_name}' 파일이 생성되었습니다.")
        except Exception as e:
            print(f"파일 쓰기 오류: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python3 text-splitter.py <입력 파일 경로>")
        sys.exit(1)
    split_chat_by_date(sys.argv[1])
