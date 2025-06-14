from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
import uuid
import base64
from server.models.widget import WidgetStyle, WidgetConfig
from server.services.widget_service import get_visitor_count, save_widget_data
from server.services.svg_generator import generate_github_style_svg

router = APIRouter()

@router.post("/create-widget")
async def create_widget(request: Request, style: WidgetStyle = None):
    widget_id = str(uuid.uuid4())
    config = WidgetConfig(style=style or WidgetStyle())
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
async def get_widget_count(widget_id: str):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return data

@router.get("/widget/profile/{widget_id}")
async def get_widget_svg(widget_id: str):
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
async def update_widget_style(widget_id: str, style: WidgetStyle):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    config = WidgetConfig(style=style)
    await save_widget_data(widget_id, data["count"], config)
    
    return {
        "widget_id": widget_id,
        "config": config.model_dump()
    } 