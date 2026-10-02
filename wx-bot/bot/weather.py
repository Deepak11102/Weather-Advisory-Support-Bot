import requests
GEO = "https://geocoding-api.open-meteo.com/v1/search"
FC = "https://api.open-meteo.com/v1/forecast"
class WeatherError(Exception): pass

def geocode(name):
    try:
        r = requests.get(GEO, params={"name": name, "count": 1}, timeout=8); r.raise_for_status()
        res = r.json().get("results")
    except Exception as e: raise WeatherError(f"geocoding failed: {e}")
    if not res: raise WeatherError(f"could not resolve location '{name}'")
    x = res[0]   # first candidate; the resolved label is always shown to the user
    return {"lat": x["latitude"], "lon": x["longitude"], "label": ", ".join(filter(None, [x["name"], x.get("admin1"), x.get("country")]))}

def fetch(loc, variables):
    try:
        r = requests.get(FC, params={"latitude": loc["lat"], "longitude": loc["lon"], "hourly": ",".join(variables),
                         "current": "temperature_2m", "timezone": "auto", "forecast_days": 2}, timeout=10)
        r.raise_for_status(); j = r.json()
        assert "hourly" in j and "current" in j
        return j
    except Exception as e: raise WeatherError(f"weather API failed: {e}")

def build_facts(p, when="now"):
    """Flatten hourly payload into facts like 'precipitation.window_sum'. Every number comes from the payload."""
    h, units, times = p["hourly"], p.get("hourly_units", {}), p["hourly"]["time"]
    now = p["current"]["time"][:13]
    i = next(k for k, t in enumerate(times) if t[:13] >= now)
    today = times[i][:10]; tomorrow = next(t[:10] for t in times if t[:10] > today)
    day = tomorrow if when == "tomorrow" else today
    didx = [k for k, t in enumerate(times) if t[:10] == day]
    hr = lambda k: int(times[k][11:13])
    if when == "tomorrow": win, label = [k for k in didx if 6 <= hr(k) <= 22], "tomorrow 06:00-22:00"
    elif when == "evening": win, label = [k for k in didx if 17 <= hr(k) <= 21 and k >= i], "this evening 17:00-21:00"
    elif when == "today": win, label = [k for k in didx if k >= i], "rest of today"
    else: win, label = list(range(i, min(i + 12, len(times)))), "next 12 hours"
    if not win: win, label = list(range(i, min(i + 12, len(times)))), "next 12 hours"
    facts = {}
    for v, arr in h.items():
        if v == "time": continue
        w = [arr[k] for k in win if arr[k] is not None]; d = [arr[k] for k in didx if arr[k] is not None]
        if arr[i] is not None: facts[f"{v}.current"] = arr[i]
        if w: facts.update({f"{v}.window_max": max(w), f"{v}.window_min": min(w), f"{v}.window_sum": round(sum(w), 1)})
        if d: facts.update({f"{v}.day_max": max(d), f"{v}.day_sum": round(sum(d), 1)})
    return facts, units, {"observed_at": p["current"]["time"], "window": label}