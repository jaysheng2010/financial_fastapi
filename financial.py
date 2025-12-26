import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import FastAPI, Response, Request
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
#import yfinance as yf
import gc
import random

apikey = "8f7cc74778c6437c9fb12d63272f80c8"

color_dict = {
    "SGD": "#A34F00", # brown
    "MYR": "#FC1D00", # red
    "AUD": "#1D00FF",  # navy blue
    "NZD": "#00CF3A",  # green
    "CHF": "#6A00FF",  # purple
    "CAD": "#EA00FF", # pink
    "JPY": "#FF7B00", # orange
    "USD": "#1C1B1B", # black
    "HKD":"#27BBF5", # light bue
    "EUR": "#07749C"
}

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
    print(data)
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
    allow_origins=["*"],          # Allow all origins (good for development)
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def none_intersect(x,y):
    fig, ax = plt.subplots(figsize=(14,5))
    ax.plot(x, y)
    plt.grid(True)
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
    return img

def intersection_true(intersection, time_used, number, times, pattern):
    fig, ax = plt.subplots(figsize=(14,5))
    exchange_to = intersection[0]
    intersection.pop(0)
    for x in intersection:
        points, date = fetch_data(f"{x}/{exchange_to}", time_used, str(number*times), pattern)
        ax.plot(date, points, label=x, color=color_dict[x])

    plt.grid(True)
    plt.legend()
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
    return img


@limiter.limit("20/minute")
@app.post("/", response_class=JSONResponse)
async def plot(request: Request):
  try:
    json_data = await request.json()
    time_type = json_data["time_type"]
    number = json_data["number"]
    intersection = json_data["symbol"]
    exchange_to = intersection[0]

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
        pattern = "%Y-%m-%d"
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

    if type(intersection) == str:
     points, date = fetch_data(json_data["symbol"], time_used, str(number*times), pattern)   
     img = none_intersect(date, points)
     return {"img_string": str(img), "title": f'{str(json_data["symbol"])} {str(number)} {time_type}', "interval":time_used, "id": f"{''.join(map(str, random.sample(range(1, 50), 5)))}"}
    elif type(intersection) == list:
        img = intersection_true(intersection, time_used, number, times, pattern)
        symbols = ", ".join(json_data["symbol"])
        return {"img_string": str(img), "title": f'{symbols} to {exchange_to} in {str(number)} {time_type}', "interval":time_used, "id": f"{''.join(map(str, random.sample(range(1, 50), 5)))}"}
    else: 
        print("Error")
        return "Error on variable \"intersection\""
  except Exception as e:
      print(e)
      return str(e)
      
#uvicorn financial:app --host 0.0.0.0 --port $PORT
