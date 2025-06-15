from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AccessLog(BaseModel):
    widget_id: str
    timestamp: datetime
    referer_domain: Optional[str] = None  # referer의 도메인 정보
    referer_path: Optional[str] = None    # referer의 경로 정보
    referer_full: Optional[str] = None    # 전체 referer URL
    user_agent: Optional[str] = None
    url: str 