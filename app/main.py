import yfinance as yf
from fastapi import FastAPI
from app.endpoints.stocks import router as stocks_router
from app.middleware import Middleware
from app.config import get_settings
import os

settings = get_settings()

# Apply yfinance config
yf.config.network.proxy = settings.yf_proxy
yf.config.network.retries = settings.yf_retries

yf.config.debug.hide_exceptions = settings.yf_debug_hide_exceptions
yf.config.debug.logging = settings.yf_debug_logging

yf.config.locale.lang = settings.yf_locale_lang
yf.config.locale.region = settings.yf_locale_region

yf.set_tz_cache_location("/tmp/yfinance-cache")




app = FastAPI(title="Stock API", version="1.0.0")

# Add middleware
app.add_middleware(Middleware)


app.include_router(stocks_router, prefix="/api")

