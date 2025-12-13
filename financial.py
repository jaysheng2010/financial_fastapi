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

def fetch_data(symbol,interval,outputsize, pattern):
    url =  "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": apikey
    }

    res = re.get(url,params=params)
    data = dict(res.json())
    points = []
    date = []
    for x in data["values"]:
        points.append(float(x["close"]))
        date.append(d.datetime.strptime(x["datetime"], pattern))
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
    time_type = json_data["time_type"]
    number = json_data["number"]

    time_used = ""
    times = 0
    pattern = ""

    if (number < 2 and time_type == "year"):
        time_used = "1day"
        times = 365
        pattern = "%Y-%m-%d"
    elif (number >= 2 and time_type == "year"):
        time_used = "1month"
        times = 12
        pattern = "%Y-%m"
    elif (number >= 9 and time_type == "month"):
        time_used = "1week"
        times = 4
        pattern = "%Y-%m-%d"
    elif (number < 9 and time_type == "month"):
        time_used = "1day"
        times = 30
        pattern = "%Y-%m-%d"
    elif (time_type == "day"):
        time_used = "1h"
        times = 24
        pattern = "%Y-%m-%d %H:%M:%S"
    elif (time_type == "hour"):
        time_used = "1min"
        times = 60
        pattern = "%Y-%m-%d %H:%M:%S"
    else: 
        time_used = None
        return {"interval":time_used}

    points, date = fetch_data(json_data["symbol"], time_used, str(number*times), pattern)
    
    fig, ax = plt.subplots(figsize=(14,5))
    ax.plot(date, points)
    plt .grid(True)
    fig.tight_layout()
    #fig.autofmt_xdate()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    print(img)

    plt.close(fig)
    del fig, ax
    gc.collect()
    return {"img_string": str(img), "title": f'{str(json_data["symbol"])} {str(number)}{time_type}', "interval":time_used}
#uvicorn main:app --host 0.0.0.0 --port $PORT
