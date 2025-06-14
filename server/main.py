from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from pathlib import Path
import os
import uuid
import base64
import aiofiles
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import time

app = FastAPI()

# MongoDB 연결 설정
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.hits_db
widgets_collection = db.widgets

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class WidgetStyle(BaseModel):
    width: int = 120
    height: int = 20
    font_family: str = "Arial"
    label: str = "Visitors"
    border_radius: int = 3
    theme: str = "light"
    float_effect: int = 0

class WidgetConfig(BaseModel):
    style: WidgetStyle = WidgetStyle()

def get_theme_colors(theme: str) -> dict:
    themes = {
        "light": {
            "bg": "#f6f8fa",
            "text": "#24292f",
            "border": "#d0d7de",
            "logo": "light",
            "section_bg": "#f6f8fa",
            "label_bg": "#6e7681",
            "label_text": "#ffffff"
        },
        "dark": {
            "bg": "#0d1117",
            "text": "#c9d1d9",
            "border": "#30363d",
            "logo": "dark",
            "section_bg": "#161b22",
            "label_bg": "#ffffff",
            "label_text": "#24292f"
        }
    }
    return themes.get(theme, themes["light"])

async def _generate_github_style_svg(data: dict, style: WidgetStyle) -> str:
    theme_colors = get_theme_colors(style.theme)
    count = data["count"]
    
    # Calculate logo size as 80% of height
    logo_size = int(style.height * 0.8)
    
    # Fixed font size
    font_size = 12
    
    # GitHub 로고 PNG 파일 읽기 및 Base64 인코딩
    logo_file_path = os.path.join("static", "images", f"github-logo-{theme_colors['logo']}.png")
    encoded_logo = ""
    try:
        async with aiofiles.open(logo_file_path, mode="rb") as f:
            logo_data = await f.read()
            encoded_logo = base64.b64encode(logo_data).decode("utf-8")
    except FileNotFoundError:
        print(f"Warning: Logo file not found at {logo_file_path}")
    
    logo_src = f"data:image/png;base64,{encoded_logo}" if encoded_logo else ""
    
    # 좌측 로고 섹션의 너비 계산
    logo_section_width = logo_size + 15 # 로고 크기 + 좌우 패딩

    label_x = logo_section_width + 10 # 로고 섹션 끝 + 우측 섹션 내 좌측 패딩
    counter_x = style.width - 10

    # 그림자 효과를 위한 필터 정의
    shadow_filter = ""
    if style.float_effect > 0:
        shadow_filter = f"filter=\"drop-shadow(0px {style.float_effect}px {style.float_effect * 2}px rgba(0, 0, 0, 0.2))\""

    # border radius 값
    radius = style.border_radius

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{style.width}" height="{style.height}" {shadow_filter}>
        <defs>
            <clipPath id="widget-clip">
                <rect x="0" y="0" width="{style.width}" height="{style.height}" rx="{radius}" ry="{radius}"/>
            </clipPath>
        </defs>
        <style>
            .counter {{
                font-family: {style.font_family}, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: {font_size}px;
                font-weight: 600;
            }}
            .label {{
                font-family: {style.font_family}, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: {font_size}px;
                font-weight: 400;
            }}
        </style>
        <g clip-path="url(#widget-clip)">
            <!-- 전체 배경 -->
            <rect x="0" y="0" width="{style.width}" height="{style.height}" fill="{theme_colors['bg']}"/>
            
            <!-- 좌측 로고 섹션 -->
            <rect x="0" y="0" width="{logo_section_width}" height="{style.height}" fill="{theme_colors['section_bg']}"/>
            
            <!-- 우측 레이블 섹션 -->
            <rect x="{logo_section_width}" y="0" width="{style.width - logo_section_width}" height="{style.height}" fill="{theme_colors['label_bg']}"/>
            
            <!-- GitHub 로고 이미지 -->
            <image xlink:href="{logo_src}" x="5" y="{style.height/2 - logo_size/2}" width="{logo_size}" height="{logo_size}"/>
            <text x="{label_x}" y="{style.height/2 + font_size/3}" class="label" fill="{theme_colors['label_text']}">{style.label}:</text>
            <text x="{counter_x}" y="{style.height/2 + font_size/3}" class="counter" fill="{theme_colors['label_text']}" text-anchor="end">{count}</text>
        </g>
    </svg>"""
    return svg

async def get_visitor_count(widget_id: str):
    widget = await widgets_collection.find_one({"widget_id": widget_id})
    if widget:
        return widget
    return None

async def save_widget_data(widget_id: str, count: int, config: WidgetConfig):
    await widgets_collection.update_one(
        {"widget_id": widget_id},
        {
            "$set": {
                "count": count,
                "widget_id": widget_id,
                "config": config.model_dump()
            }
        },
        upsert=True
    )

@app.middleware("http")
async def count_visitors(request: Request, call_next):
    path = request.url.path
    if path.startswith("/widget/profile/"):
        widget_id = path.split("/")[3]
        data = await get_visitor_count(widget_id)
        if data:
            data["count"] += 1
            await save_widget_data(widget_id, data["count"], WidgetConfig(**data.get("config", {})))
    
    response = await call_next(request)
    return response

@app.post("/create-widget")
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

@app.get("/widget/{widget_id}/count")
async def get_widget_count(widget_id: str):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    return data

@app.get("/widget/profile/{widget_id}")
async def get_widget_svg(widget_id: str):
    data = await get_visitor_count(widget_id)
    if not data:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    config = WidgetConfig(**data.get("config", {}))
    style = config.style
    
    # 항상 GitHub 스타일 SVG 생성
    svg = await _generate_github_style_svg(data, style)
    
    # 캐시 컨트롤 헤더 추가
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    return Response(content=svg, media_type="image/svg+xml", headers=headers)

@app.put("/widget/{widget_id}/style")
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

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # GitHub 로고 이미지를 Base64로 인코딩
    light_logo_path = os.path.join("static", "images", "github-logo-light.png")
    dark_logo_path = os.path.join("static", "images", "github-logo-dark.png")
    
    light_logo_base64 = ""
    dark_logo_base64 = ""
    
    try:
        with open(light_logo_path, "rb") as f:
            light_logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        with open(dark_logo_path, "rb") as f:
            dark_logo_base64 = base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError as e:
        print(f"Warning: Logo file not found: {e}")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "light_logo_base64": light_logo_base64,
        "dark_logo_base64": dark_logo_base64
    })

