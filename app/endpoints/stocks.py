from datetime import date
from fastapi import APIRouter, HTTPException, Query
import yfinance as yf
from app.schemas import HistoryResponse


router = APIRouter(tags=["api"])


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

    return HistoryResponse(ticker=ticker, start=start, end=end, results=results)
