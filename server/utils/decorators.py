from functools import wraps
from fastapi import Request
from server.services.log_service import save_access_log

def log_widget_access():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Request 객체 찾기
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                request = next((arg for arg in kwargs.values() if isinstance(arg, Request)), None)
            # widget_id 찾기
            widget_id = kwargs.get('widget_id')
            
            if request and widget_id:
                # 로그 정보 수집
                request_info = {
                    "referer": request.headers.get("referer"),
                    "user_agent": request.headers.get("user-agent"),
                    "url": str(request.url)
                }
                
                # 로그 저장
                await save_access_log(widget_id, request_info)
            
            # 원래 함수 실행
            return await func(*args, **kwargs)
        return wrapper
    return decorator 