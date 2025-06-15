import os
import base64
import aiofiles
from server.utils.theme import get_theme_colors
from server.models.widget import WidgetStyle

async def generate_github_style_svg(data: dict, style: WidgetStyle) -> str:
    theme_colors = get_theme_colors(style.theme)
    count = data["count"]
    
    # Calculate logo size as 80% of height
    logo_size = int(style.height * 0.8)
    
    # Fixed font size
    font_size = 12
    
    # GitHub 로고 PNG 파일 읽기 및 Base64 인코딩
    logo_file_path = os.path.join("server/static", "images", f"github-logo-{theme_colors['logo']}.png")
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