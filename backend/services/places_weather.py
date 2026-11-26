from typing import Any

import httpx

from config import get_settings

settings = get_settings()

CURATED_PLACES = [
    {"name": "Rift Valley View Lodge", "address": "Nakuru, Kenya", "rating": 4.4, "category": "Lodge"},
    {"name": "Maasai Oasis Camp", "address": "Kitengela, Kajiado", "rating": 4.8, "category": "Camp"},
    {"name": "Lakefront Homestay", "address": "Kisumu, Kenya", "rating": 4.5, "category": "Homestay"},
    {"name": "Swahili Coast Guest House", "address": "Mombasa, Kenya", "rating": 4.6, "category": "Guest House"},
    {"name": "Pinetree Boutique Hotel", "address": "Kilimani, Nairobi", "rating": 4.7, "category": "Hotel"},
]


async def search_places(query: str, city: str | None = None) -> list[dict[str, Any]]:
    if settings.google_places_api_key:
        text_query = f"{query} in {city or settings.default_city}, Kenya"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    "https://places.googleapis.com/v1/places:searchText",
                    headers={
                        "X-Goog-Api-Key": settings.google_places_api_key,
                        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating",
                        "Content-Type": "application/json",
                    },
                    json={"textQuery": text_query, "maxResultCount": 5},
                )
                response.raise_for_status()
                results = []
                for place in response.json().get("places", []):
                    results.append(
                        {
                            "name": place.get("displayName", {}).get("text", "Place"),
                            "address": place.get("formattedAddress", ""),
                            "rating": place.get("rating"),
                            "place_id": place.get("id"),
                        }
                    )
                if results:
                    return results
        except Exception:
            pass

    terms = [term.lower() for term in query.lower().replace(",", " ").split() if len(term) > 3]
    matched = [p for p in CURATED_PLACES if any(term in (p["name"] + " " + p["address"] + " " + p["category"]).lower() for term in terms)]
    return (matched or CURATED_PLACES)[:5]


async def current_weather(city: str | None = None) -> dict[str, Any]:
    location = city or settings.default_city
    if settings.openweather_api_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": location, "appid": settings.openweather_api_key, "units": "metric"},
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "city": data.get("name", location),
                    "description": data["weather"][0]["description"] if data.get("weather") else "clear",
                    "temperature": data.get("main", {}).get("temp"),
                    "humidity": data.get("main", {}).get("humidity"),
                    "wind_speed": data.get("wind", {}).get("speed"),
                    "source": "openweather",
                }
        except Exception:
            pass

    return {
        "city": location,
        "description": "partly cloudy",
        "temperature": 24.0,
        "humidity": 62,
        "wind_speed": 3.4,
        "source": "demo",
    }


def safety_note(weather: dict[str, Any]) -> str:
    description = str(weather.get("description", "")).lower()
    if "rain" in description or "storm" in description:
        return "Heavy rain possible — allow extra travel time and confirm road conditions."
    if "haze" in description or "dust" in description:
        return "Hazy conditions — travelers with respiratory issues should take care."
    return "Conditions look fine for travel. Keep your emergency contact handy."
