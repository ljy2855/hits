from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, HTMLResponse
import uuid
import base64
from server.models.widget import WidgetStyle, WidgetConfig
from server.services.widget_service import get_visitor_count, save_widget_data, get_user_widgets, get_widget_without_counting, delete_widget
from server.services.svg_generator import generate_github_style_svg
from server.utils.decorators import log_widget_access
from fastapi.templating import Jinja2Templates
from server.services.log_service import get_widget_stats, logs_collection
from server.config.database import widgets_collection
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter()
templates = Jinja2Templates(directory="server/templates")

@router.post("/create-widget")
async def create_widget(request: Request, style: WidgetStyle = None):
    # 세션에서 GitHub 사용자 ID 가져오기
    github_user = request.cookies.get("github_user")
    
    widget_id = str(uuid.uuid4())
    config = WidgetConfig(style=style or WidgetStyle(), user_id=github_user)
    await save_widget_data(widget_id, 0, config)
    
    # Get server host from request
    host = request.headers.get("host", "your-server-address")
    base_url = f"https://{host}"
    
    # Use a path-based approach without file extension
    widget_url = f"/widget/profile/{widget_id}"
    
    return {
        "widget_id": widget_id,
        "widget_url": widget_url,
        "markdown_code": f"![Visitor Count]({base_url}{widget_url})",
        "config": config.model_dump()
    }

@router.get("/widget/{widget_id}/count")
@log_widget_access()
async def get_widget_count(widget_id: str, request: Request):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return data

@router.get("/widget/profile/{widget_id}")
@log_widget_access()
async def get_widget_svg(widget_id: str, request: Request):
    # 요청 URL에서 /my-widgets가 포함되어 있는지 확인
    referer = request.headers.get("referer", "")
    if "/my-widgets" in referer:
        # 내 위젯 페이지에서 조회하는 경우 카운트 증가하지 않음
        data = await get_widget_without_counting(widget_id)
    else:
        # 일반 조회의 경우 카운트 증가
        data = await get_visitor_count(widget_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    config = WidgetConfig(**data.get("config", {}))
    style = config.style
    
    # 항상 GitHub 스타일 SVG 생성
    svg = await generate_github_style_svg(data, style)
    
    # 캐시 컨트롤 헤더 추가
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    return Response(content=svg, media_type="image/svg+xml", headers=headers)

@router.put("/widget/{widget_id}/style")
@log_widget_access()
async def update_widget_style(widget_id: str, style: WidgetStyle, request: Request):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    config = WidgetConfig(**data.get("config", {}))
    config.style = style
    await save_widget_data(widget_id, data["count"], config)
    
    return {
        "widget_id": widget_id,
        "config": config.model_dump()
    }

@router.get("/user/{user_id}/widgets")
async def list_user_widgets(user_id: str):
    """사용자의 모든 위젯을 조회합니다."""
    widgets = await get_user_widgets(user_id)
    return {
        "user_id": user_id,
        "widgets": widgets
    }

@router.get("/widget/{widget_id}/config")
async def get_widget_config(widget_id: str):
    """위젯 ID로 위젯 설정을 조회합니다."""
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    config = WidgetConfig(**data.get("config", {}))
    return {
        "widget_id": widget_id,
        "count": data["count"],
        "config": config.model_dump()
    }

@router.get("/my-widgets", response_class=HTMLResponse)
async def my_widgets_page(request: Request):
    """내 위젯 페이지를 렌더링합니다."""
    return templates.TemplateResponse("my_widgets.html", {"request": request})

@router.delete("/widget/{widget_id}")
async def delete_widget_endpoint(widget_id: str, request: Request):
    """위젯을 삭제합니다."""
    # 세션에서 GitHub 사용자 ID 가져오기
    github_user = request.cookies.get("github_user")
    if not github_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 위젯 데이터 가져오기
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # 위젯 소유자 확인
    config = WidgetConfig(**data.get("config", {}))
    if config.user_id != github_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 위젯 삭제
    success = await delete_widget(widget_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete widget")
    
    return {"status": "success", "message": "Widget deleted successfully"}

@router.get("/widget/{widget_id}/stats")
async def get_widget_stats_endpoint(widget_id: str, request: Request):
    """위젯의 방문자 수 통계를 반환합니다."""
    # 세션에서 GitHub 사용자 ID 가져오기
    github_user = request.cookies.get("github_user")
    if not github_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 위젯 데이터 가져오기
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # 위젯 소유자 확인
    config = WidgetConfig(**data.get("config", {}))
    if config.user_id != github_user:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 통계 데이터 가져오기
    stats = await get_widget_stats(widget_id)
    return stats

@router.get("/widget/{widget_id}/stats", response_class=HTMLResponse)
async def widget_stats_page(widget_id: str, request: Request):
    """위젯 통계 페이지를 렌더링합니다."""
    return templates.TemplateResponse("widget_stats.html", {
        "request": request,
        "widget_id": widget_id
    })

@router.get("/widget/leaderboard")
async def get_leaderboard():
    """상위 10개 유저의 총 방문자 수를 반환합니다."""
    # 최근 7일간의 로그 데이터를 기준으로 유저별 방문자 수 집계
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    # 위젯 ID로 유저 ID를 매핑하기 위한 딕셔너리 생성
    widget_to_user = {}
    widgets = await widgets_collection.find().to_list(length=None)
    for widget in widgets:
        # _id와 widget_id 모두 매핑
        widget_id = str(widget.get("_id"))
        custom_widget_id = widget.get("widget_id")
        user_id = widget.get("config", {}).get("user_id")
        if user_id:
            widget_to_user[widget_id] = user_id
            if custom_widget_id:
                widget_to_user[custom_widget_id] = user_id
    
    
    # 로그에서 위젯별 방문자 수 집계
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": seven_days_ago}
            }
        },
        {
            "$group": {
                "_id": "$widget_id",
                "count": {"$sum": 1}
            }
        }
    ]
    
    widget_stats = await logs_collection.aggregate(pipeline).to_list(length=None)
    print("Widget stats:", widget_stats)  # 디버깅용
    
    # 유저별 방문자 수 집계
    user_stats = {}
    for stat in widget_stats:
        widget_id = stat["_id"]
        user_id = widget_to_user.get(widget_id)
        if user_id:
            if user_id not in user_stats:
                user_stats[user_id] = 0
            user_stats[user_id] += stat["count"]
    
    print("User stats:", user_stats)  # 디버깅용
    
    # 상위 10개 유저 선택
    top_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "users": [{"user_id": user_id, "count": count} for user_id, count in top_users]
    } 