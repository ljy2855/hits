from pydantic import BaseModel

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
    user_id: str | None = None  # 위젯을 생성한 사용자의 ID (선택사항) 