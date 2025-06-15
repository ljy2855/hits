from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import base64
from server.routes.widget import router as widget_router
from server.services.widget_service import get_visitor_count, save_widget_data
from server.models.widget import WidgetConfig
from .routes import auth

app = FastAPI()

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="server/static"), name="static")
templates = Jinja2Templates(directory="server/templates")

# 라우터 등록
app.include_router(widget_router)
app.include_router(auth.router, prefix="/auth")

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

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # GitHub 로고 이미지를 Base64로 인코딩
    light_logo_path = os.path.join("server/static", "images", "github-logo-light.png")
    dark_logo_path = os.path.join("server/static", "images", "github-logo-dark.png")
    
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

