import yfinance as yf
from fastapi import FastAPI
from app.routes.api import router as api_router
from app.middleware import Middleware
from app.config import get_settings

settings = get_settings()

# Apply yfinance config
yf.config.locale.lang = settings.yf_locale_lang # Language code — controls the translation of text fields returned
yf.config.locale.region = settings.yf_locale_region


app = FastAPI(title="Stock API", version="1.0.0")


# Add middleware
app.add_middleware(Middleware)


app.include_router(api_router, prefix="/api")

