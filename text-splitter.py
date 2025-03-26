import re
from datetime import datetime

def split_chat_by_date(chat_text):
    # 날짜 정규 표현식
    date_pattern = r'\d{4}년 \d{1,2}월 \d{1,2}일'
    
    # 날짜별로 대화 내용 저장
    chat_dict = {}
    
    # 대화 내용을 줄 단위로 나눕니다.
    lines = chat_text.strip().split('\n')
    
    current_date = None
    
    for line in lines:
        # 날짜가 포함된 줄을 찾습니다.
        date_match = re.search(date_pattern, line)
        if date_match:
            # 날짜를 추출하고 형식 변환
            current_date = date_match.group()
            if current_date not in chat_dict:
                chat_dict[current_date] = []
        # 현재 날짜가 설정되어 있으면 대화 내용을 추가합니다.
        if current_date:
            chat_dict[current_date].append(line)

    # 각 날짜별로 파일로 저장
    for date, messages in chat_dict.items():
        file_name = f'chat_{date.replace(" ", "_").replace("년", "").replace("월", "").replace("일", "")}.txt'
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(messages))
