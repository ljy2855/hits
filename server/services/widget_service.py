from ..config.database import widgets_collection
from ..models.widget import WidgetConfig
from bson import ObjectId

async def get_visitor_count(widget_id: str):
    widget = await widgets_collection.find_one({"widget_id": widget_id})
    if widget:
        return widget
    return None

async def get_widget_without_counting(widget_id: str):
    """방문자 수를 증가시키지 않고 위젯 정보를 조회합니다."""
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

async def get_user_widgets(user_id: str):
    """사용자의 모든 위젯을 조회합니다."""
    cursor = widgets_collection.find({"config.user_id": user_id})
    widgets = await cursor.to_list(length=None)
    
    # ObjectId를 문자열로 변환
    for widget in widgets:
        if "_id" in widget:
            widget["_id"] = str(widget["_id"])
    
    return widgets

async def delete_widget(widget_id: str) -> bool:
    """위젯을 삭제합니다."""
    try:
        # widget_id 필드로 삭제 시도
        result = await widgets_collection.delete_one({"widget_id": widget_id})
        if result.deleted_count > 0:
            return True
            
        # _id 필드로도 시도
        result = await widgets_collection.delete_one({"_id": widget_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting widget: {str(e)}")
        return False 