from datetime import date
from fastapi import APIRouter, HTTPException, Query
import yfinance as yf


router = APIRouter(tags=["api"])


@router.get("/company")
async def get_company(
    ticker: str = Query(..., description="Stock ticker symbol")
):

    """
    Provides company metadata

    """

    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange"),
            "country": info.get("country"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
            "description": info.get("longBusinessSummary"),
        }

    except Exception as e:
        raise HTTPException(detail=str(e))



@router.get("/quote")
async def get_quote(
    ticker: str = Query(..., description="Stock ticker symbol")
):

    """
    Provides the latest market snapshot without downloading historical data.

    """
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        return {
            "ticker": ticker,
            "price": info.get("lastPrice"),
            "previousClose": info.get("previousClose"),
            "change": info.get("lastPrice") - info.get("previousClose"),
            "changePercent": (
                (info.get("lastPrice") - info.get("previousClose"))
                / info.get("previousClose")
            ) * 100,
            "dayHigh": info.get("dayHigh"),
            "dayLow": info.get("dayLow"),
            "volume": info.get("lastVolume"),
            "marketCap": info.get("marketCap"),
            "currency": info.get("currency")
        }
    except Exception as e:
        raise HTTPException(detail=str(e))


@router.get("/stats")
async def get_stock_data(
    ticker: str = Query(..., description="Stock ticker symbol"),
    start: date = Query(..., description="Start date"),
    end: date = Query(..., description="End date"),
):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(start=start, end=end)

        results = []
        for date_value, row in data.iterrows():
            date_str = date_value.strftime("%Y-%m-%d")
            results.append({
                "date": date_str,
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": int(row["Volume"]),
                "average": (row["Open"] + row["High"] + row["Low"] + row["Close"]) / 4
            })

    except Exception as e:
        raise HTTPException(detail=str(e))

    return {
        "ticker": ticker,
        "start": start,
        "end": end,
        "results": results,
    }
