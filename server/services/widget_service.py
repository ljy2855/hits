from ..config.database import widgets_collection
from ..models.widget import WidgetConfig

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