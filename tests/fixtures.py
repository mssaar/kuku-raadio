SHOWS_PAGE = {
    "results": [
        {"id": 209, "name": "Digitund", "description_short": "Tehnoloogiasaade",
         "thumbnail": {"square_250_x1": "https://img/209.png"}},
        {"id": 246, "name": "Olukorrast ajakirjanduses", "description_short": None, "thumbnail": None},
    ],
    "current_page": 1,
    "total_pages": 1,
}


def episode(id, published_at, premium=0, playable=True, duration=2796.5, title=None):
    return {"id": id, "title": title or f"Osa {id}", "published_at": published_at,
            "is_premium": premium, "is_playable": playable, "duration_seconds": duration}


def episodes_page(results, page=1, total=1):
    return {"show": {"id": 209, "name": "Digitund"},
            "episodes": {"results": results, "current_page": page, "total_pages": total}}
