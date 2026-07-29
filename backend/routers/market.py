"""Прокси для рыночных данных (Yahoo Finance)"""
from fastapi import APIRouter, HTTPException
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/market/{symbol}")
async def get_market_data(symbol: str, range: str = "1mo", interval: str = "1d"):
    """Получить данные графика через Yahoo Finance"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": interval, "range": range}
        headers = {"User-Agent": "Mozilla/5.0"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(status_code=resp.status_code, detail="Yahoo Finance error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Market data error for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=str(e))
