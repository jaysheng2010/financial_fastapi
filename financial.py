import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import FastAPI, Response, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import uvicorn
import requests as re
import io 
import base64
import datetime as d
from fastapi.middleware.cors import CORSMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler

apikey = "8f7cc74778c6437c9fb12d63272f80c8"

def fetch_data(symbol,interval,outputsize):
    url =  "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": apikey
    }

    res = re.get(url,params=params)
    data = dict(res.json())
    print(data)
    points = []
    date = []
    for x in data["values"]:
        points.append(float(x["close"]))
        date_str = x["datetime"].split(" ")[0] 
        date.append(d.datetime.strptime(date_str, "%Y-%m-%d"))
    points.reverse()
    date.reverse()
    return points, date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://financial-graph-app-html.onrender.com"],          # Allow all origins (good for development)
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@limiter.limit("20/minute")
@app.post("/", response_class=JSONResponse)
async def plot(request: Request):
    json_data = await request.json()
    years = json_data["years"]
    points, date = fetch_data(json_data["symbol"], "1month", str(years*12))
    fig, ax = plt.subplots(figsize=(12,5))
    ax.plot(date, points)
    plt.grid(True)
    fig.tight_layout()
    #fig.autofmt_xdate()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    print(img)
    print(json_data["symbol"])
    return {"img_string": str(img), "title": str(json_data["symbol"]), "csrf": json_data["csrf"]}

#uvicorn main:app --host 0.0.0.0 --port $PORT
