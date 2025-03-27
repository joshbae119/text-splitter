from fastapi import FastAPI, HTTPException
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiofiles
from collections import defaultdict

app = FastAPI()
input_directory = './input'  # dev

# 정규식 미리 컴파일
DATETIME_PATTERN = re.compile(r'(\d{4}년 \d{1,2}월 \d{1,2}일) (오[전후]) (\d{1,2}):(\d{1,2})')
TITLE_PATTERN = re.compile(r"(.*?) 님과 카카오톡 대화\s*\n\s*저장한 날짜 : (.*?)\n")
EXCLUDE_PATTERNS = ['오픈채팅봇', '님이 나갔습니다.', '님이 들어왔습니다.']

def convert_time(date_str: str, period: str, hour: str, minute: str) -> datetime:
    """날짜와 시간을 datetime 객체로 변환"""
    date_obj = datetime.strptime(date_str, '%Y년 %m월 %d일')
    hour = int(hour)
    if period == '오후' and hour != 12:
        hour += 12
    elif period == '오전' and hour == 12:
        hour = 0
    return date_obj.replace(hour=hour, minute=int(minute))

async def index_chat_file(file_path: str) -> Dict[str, List[int]]:
    """파일을 한 번 스캔하며 날짜별 오프셋 인덱스 생성"""
    offsets = defaultdict(list)
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        offset = 0
        async for line in file:
            match = DATETIME_PATTERN.search(line)
            if match:
                date_str, period, hour, minute = match.groups()
                dt = convert_time(date_str, period, hour, minute)
                base_date = (dt - timedelta(days=1)).strftime('%Y년 %m월 %d일') if dt.hour < 4 else dt.strftime('%Y년 %m월 %d일')
                offsets[base_date].append(offset)
            offset += len(line.encode('utf-8'))
    return dict(offsets)

def process_kakao_chat(file_path: str) -> Optional[Dict[str, str]]:
    """파일 헤더에서 제목, 저장 날짜, 콘텐츠 시작 위치 추출 (동기 함수 유지)"""
    with open(file_path, 'r', encoding='utf-8') as file:
        header = ''
        offset = 0
        while True:
            line = file.readline()
            if not line:  # EOF
                break
            header += line
            offset += len(line.encode('utf-8'))
            match = TITLE_PATTERN.search(header)
            if match:
                return {
                    "title": match.group(1),
                    "saved_date": match.group(2),
                    "content_start": offset
                }
    return None

async def get_filtered_lines(file_path: str, start_time: datetime, end_time: datetime, content_start: int) -> List[str]:
    """특정 날짜 범위의 대화 내용을 리스트로 반환"""
    filtered_lines = []
    first_message_time = None
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        await file.seek(content_start)
        async for line in file:
            if any(pattern in line for pattern in EXCLUDE_PATTERNS):
                continue
            match = DATETIME_PATTERN.search(line)
            if match:
                dt = convert_time(*match.groups())
                if start_time <= dt <= end_time:
                    if first_message_time is None:
                        first_message_time = dt
                    filtered_lines.append(line.strip())
    return filtered_lines, first_message_time

@app.get("/items/{item_name}")
async def read_item(item_name: str, page: int = 1):
    """특정 파일의 대화 내용을 페이지 단위로 JSON 형태로 반환"""
    file_path = os.path.join(input_directory, item_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 헤더 파싱 (동기)
    chat_data = process_kakao_chat(file_path)
    if not chat_data:
        raise HTTPException(status_code=422, detail="Invalid chat format")

    # 날짜 인덱싱 (비동기)
    offsets = await index_chat_file(file_path)
    dates = sorted(offsets.keys())
    if not dates:
        raise HTTPException(status_code=422, detail="No dates found in content")
    if page < 1 or page > len(dates):
        raise HTTPException(status_code=400, detail="Invalid page number")

    # 현재 페이지의 날짜 범위 설정
    current_date = dates[page - 1]
    date_obj = datetime.strptime(current_date, '%Y년 %m월 %d일')
    start_time = date_obj.replace(hour=4, minute=0)
    end_time = (date_obj + timedelta(days=1)).replace(hour=3, minute=59)

    # 필터링된 대화 내용과 첫 메시지 시간 가져오기
    filtered_lines, first_message_time = await get_filtered_lines(file_path, start_time, end_time, chat_data["content_start"])

    # 날짜 포맷팅
    if first_message_time:
        date_with_time = f"{date_obj.strftime('%Y-%m-%d')}_{first_message_time.strftime('%H:%M:%S')}"
    else:
        date_with_time = date_obj.strftime('%Y-%m-%d')

    # 영어 제목 및 고유 제목 생성
    english_title = None
    if "피부과 안티에이징" in chat_data["title"]:
        english_title = "skin-anti-aging"
    unique_title = f"{english_title}_{date_with_time}" if english_title else None

    # 원래 JSON 포맷 유지
    return {
        "korean_title": chat_data["title"],
        "english_title": english_title,
        "unique_title": unique_title,
        "file_save_date": chat_data["saved_date"],
        "date": date_with_time,
        "total_items": len(filtered_lines),
        "page": page,
        "total_pages": len(dates),
        "content": "\n".join(filtered_lines)
    }