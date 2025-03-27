from fastapi import FastAPI, HTTPException
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

app = FastAPI()
input_directory = './input'  # dev

# 정규식 미리 컴파일
DATETIME_PATTERN = re.compile(r'(\d{4}년 \d{1,2}월 \d{1,2}일) (오[전후]) (\d{1,2}):(\d{1,2})')
TITLE_PATTERN = re.compile(r"(.*?) 님과 카카오톡 대화\s*\n\s*저장한 날짜 : (.*?)\n")
EXCLUDE_PATTERNS = ['오픈채팅봇', '님이 나갔습니다.', '님이 들어왔습니다.']

def convert_time(date_str: str, period: str, hour: str, minute: str) -> datetime:
    date_obj = datetime.strptime(date_str, '%Y년 %m월 %d일')
    hour = int(hour)
    if period == '오후' and hour != 12:
        hour += 12
    elif period == '오전' and hour == 12:
        hour = 0
    return date_obj.replace(hour=hour, minute=int(minute))

def get_chat_dates(file_path: str) -> List[str]:
    dates: Dict[str, bool] = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = DATETIME_PATTERN.search(line)
            if match:
                date_str, period, hour, minute = match.groups()
                dt = convert_time(date_str, period, hour, minute)
                base_date = (dt - timedelta(days=1)).strftime('%Y년 %m월 %d일') if dt.hour < 4 else dt.strftime('%Y년 %m월 %d일')
                dates[base_date] = True
    return sorted(dates.keys())

def process_kakao_chat(file_path: str) -> Optional[Dict[str, str]]:
    with open(file_path, 'r', encoding='utf-8') as file:
        header = ''
        offset = 0
        while True:
            line = file.readline()
            if not line:  # EOF
                break
            header += line
            offset += len(line.encode('utf-8'))  # UTF-8 바이트 단위로 오프셋 계산
            match = TITLE_PATTERN.search(header)
            if match:
                return {
                    "title": match.group(1),
                    "saved_date": match.group(2),
                    "content_start": offset  # 헤더 끝나는 위치 반환
                }
    return None

@app.get("/items/{item_name}")
async def read_item(item_name: str, page: int = 1):
    file_path = os.path.join(input_directory, item_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    chat_data = process_kakao_chat(file_path)
    if not chat_data:
        raise HTTPException(status_code=422, detail="Invalid chat format")

    dates = get_chat_dates(file_path)
    if not dates:
        raise HTTPException(status_code=422, detail="No dates found in content")
    if page < 1 or page > len(dates):
        raise HTTPException(status_code=400, detail="Invalid page number")

    current_date = dates[page - 1]
    date_obj = datetime.strptime(current_date, '%Y년 %m월 %d일')
    start_time = date_obj.replace(hour=4, minute=0)
    end_time = (date_obj + timedelta(days=1)).replace(hour=3, minute=59)

    filtered_lines = []
    first_message_time = None  # 첫 번째 메시지의 시간 저장
    with open(file_path, 'r', encoding='utf-8') as file:
        file.seek(chat_data["content_start"])  # 대화 내용 시작 위치로 이동
        for line in file:
            if any(pattern in line for pattern in EXCLUDE_PATTERNS):
                continue
            match = DATETIME_PATTERN.search(line)
            if match:
                dt = convert_time(*match.groups())
                if start_time <= dt <= end_time:
                    if first_message_time is None:
                        first_message_time = dt  # 첫 번째 메시지의 시간 저장
                    filtered_lines.append(line.strip())

    # PostgreSQL timestamp 형식으로 수정된 date (언더스코어 추가)
    if first_message_time:
        date_with_time = f"{date_obj.strftime('%Y-%m-%d')}_{first_message_time.strftime('%H:%M:%S')}"
    else:
        date_with_time = date_obj.strftime('%Y-%m-%d')

    # 영어 제목 추가
    english_title = None
    if "피부과 안티에이징" in chat_data["title"]:
        english_title = "skin-anti-aging"

    # unique_title 추가
    unique_title = f"{english_title}_{date_with_time}" if english_title else None

    return {
        "korean_title": chat_data["title"],
        "english_title": english_title,  # 추가된 부분
        "unique_title": unique_title,  # 추가된 부분
        "file_save_date": chat_data["saved_date"],
        "date": date_with_time,  # 수정된 부분
        "total_items": len(filtered_lines),
        "page": page,
        "total_pages": len(dates),
        "content": "\n".join(filtered_lines)
    }
