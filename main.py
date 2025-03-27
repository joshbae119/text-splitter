from fastapi import FastAPI, HTTPException
import os
import re
from datetime import datetime, timedelta

app = FastAPI()
input_directory = './input'

def convert_time(date_str: str, period: str, hour: str, minute: str) -> datetime:
    # 날짜 객체 생성
    date_obj = datetime.strptime(date_str, '%Y년 %m월 %d일')
    
    # 시간 변환
    hour = int(hour)
    if period == '오후' and hour != 12:
        hour += 12
    elif period == '오전' and hour == 12:
        hour = 0
        
    return date_obj.replace(hour=hour, minute=int(minute))

def get_chat_dates(content: str):
    datetime_pattern = r'(\d{4}년 \d{1,2}월 \d{1,2}일) (오[전후]) (\d{1,2}):(\d{1,2})'
    dates = {}
    
    for line in content.splitlines():
        match = re.search(datetime_pattern, line)
        if match:
            date_str, period, hour, minute = match.groups()
            dt = convert_time(date_str, period, hour, minute)
            
            # 오전 4시 기준으로 날짜 조정
            if dt.hour < 4:
                base_date = (dt - timedelta(days=1)).strftime('%Y년 %m월 %d일')
            else:
                base_date = dt.strftime('%Y년 %m월 %d일')
            
            dates[base_date] = True
    
    return sorted(dates.keys())

@app.get("/")
def read_root():
    return {"Hello": "World"}

def process_kakao_chat(content: str):
    title_pattern = r"(.*?) 님과 카카오톡 대화\s*\n\s*저장한 날짜 : (.*?)\n"
    title_match = re.search(title_pattern, content)
    
    if title_match:
        chat_title = title_match.group(1)
        saved_date = title_match.group(2)
        chat_content = content.split(title_match.group(0))[-1].strip()
        
        return {
            "title": chat_title,
            "saved_date": saved_date,
            "content": chat_content
        }
    return None

@app.get("/items/{item_name}")
def read_item(item_name: str, page: int = 1):
    file_path = os.path.join(input_directory, item_name)
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    chat_data = process_kakao_chat(content)
    if not chat_data:
        raise HTTPException(status_code=422, detail="Invalid chat format")

    # 모든 고유한 날짜 추출
    dates = get_chat_dates(chat_data["content"])
    if not dates:
        raise HTTPException(status_code=422, detail="No dates found in content")

    # 페이지 번호가 유효한지 확인
    if page < 1 or page > len(dates):
        raise HTTPException(status_code=400, detail="Invalid page number")

    # 페이지 번호에 해당하는 날짜 선택
    current_date = dates[page - 1]
    
    # 선택된 날짜의 대화만 필터링 (오전 4시 기준)
    filtered_lines = []
    date_obj = datetime.strptime(current_date, '%Y년 %m월 %d일')
    next_date = date_obj + timedelta(days=1)
    
    datetime_pattern = r'(\d{4}년 \d{1,2}월 \d{1,2}일) (오[전후]) (\d{1,2}):(\d{1,2})'
    
    # 제외할 메시지 패턴 정의
    exclude_patterns = ['오픈채팅봇', '님이 나갔습니다.', '님이 들어왔습니다.']
    
    for line in chat_data["content"].splitlines():
        # 제외할 메시지가 포함된 라인 건너뛰기
        if any(pattern in line for pattern in exclude_patterns):
            continue
            
        match = re.search(datetime_pattern, line)
        if match:
            date_str, period, hour, minute = match.groups()
            dt = convert_time(date_str, period, hour, minute)
            
            # 현재 날짜의 오전 4시부터 다음날 오전 3:59까지의 메시지만 포함
            start_time = date_obj.replace(hour=4, minute=0)
            end_time = next_date.replace(hour=3, minute=59)
            
            if start_time <= dt <= end_time:
                filtered_lines.append(line)

    total_items = len(filtered_lines)

    return {
        "korean_title": chat_data["title"],
        "file_save_date": chat_data["saved_date"],
        "date": current_date,
        "total_items": total_items,
        "page": page,
        "total_pages": len(dates),
        "content": "\n".join(filtered_lines)
    }
