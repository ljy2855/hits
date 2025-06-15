from datetime import datetime, timedelta
from typing import Optional, Dict, List
from urllib.parse import urlparse
from ..config.database import db
from ..models.log import AccessLog

logs_collection = db.access_logs

def parse_referer(referer: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not referer:
        return None, None, None
    
    try:
        parsed = urlparse(referer)
        domain = parsed.netloc
        path = parsed.path
        return domain, path, referer
    except:
        return None, None, referer

async def save_access_log(widget_id: str, request_info: dict):
    referer = request_info.get("referer")
    domain, path, full_url = parse_referer(referer)
    
    log = AccessLog(
        widget_id=widget_id,
        timestamp=datetime.utcnow(),
        referer_domain=domain,
        referer_path=path,
        referer_full=full_url,
        user_agent=request_info.get("user_agent"),
        url=request_info.get("url", "")
    )
    
    await logs_collection.insert_one(log.model_dump())

async def get_widget_stats(widget_id: str) -> Dict:
    """위젯의 방문자 수 통계를 가져옵니다."""
    now = datetime.utcnow()
    
    # 최근 7일간의 일별 방문자 수
    daily_stats = []
    for i in range(7):
        date = now - timedelta(days=i)
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)
        
        count = await logs_collection.count_documents({
            "widget_id": widget_id,
            "timestamp": {
                "$gte": start_of_day,
                "$lt": end_of_day
            }
        })
        
        daily_stats.append({
            "date": start_of_day.strftime("%Y-%m-%d"),
            "count": count
        })
    
    # 최근 24시간의 시간별 방문자 수
    hourly_stats = []
    for i in range(24):
        hour = now - timedelta(hours=i)
        start_of_hour = datetime(hour.year, hour.month, hour.day, hour.hour)
        end_of_hour = start_of_hour + timedelta(hours=1)
        
        count = await logs_collection.count_documents({
            "widget_id": widget_id,
            "timestamp": {
                "$gte": start_of_hour,
                "$lt": end_of_hour
            }
        })
        
        hourly_stats.append({
            "hour": start_of_hour.strftime("%H:00"),
            "count": count
        })
    
    # 도메인별 방문자 수
    domain_stats = await logs_collection.aggregate([
        {"$match": {"widget_id": widget_id}},
        {"$group": {
            "_id": "$referer_domain",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(length=10)
    
    return {
        "daily_stats": list(reversed(daily_stats)),
        "hourly_stats": list(reversed(hourly_stats)),
        "domain_stats": [
            {"domain": stat["_id"] or "Direct", "count": stat["count"]}
            for stat in domain_stats
        ]
    } 