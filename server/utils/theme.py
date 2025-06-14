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