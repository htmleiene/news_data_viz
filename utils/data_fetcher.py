from newsapi import NewsApiClient
from pytrends.request import TrendReq
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import logging
from requests.exceptions import RequestException as ResponseError

logger = logging.getLogger(__name__)

# Configuração das APIs
newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))

# PyTrends com configuração robusta
def get_pytrends():
    return TrendReq(
        hl='pt-BR',
        tz=180,
        timeout=(10, 25),
        retries=2,
        backoff_factor=0.1,
        requests_args={
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
    )

def fetch_news_data(query, days=7):
    """Busca notícias da NewsAPI com tratamento de erro"""
    try:
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        data = newsapi.get_everything(
            q=query,
            from_param=date_from,
            language='pt',
            sort_by='relevancy',
            page_size=100
        )
        logger.info(f"NewsAPI: {len(data.get('articles', []))} artigos encontrados")
        return data.get('articles', [])
    except Exception as e:
        logger.error(f"Erro NewsAPI: {str(e)}")
        return []

def fetch_trends_data(keywords, days=30):
    """Busca dados do PyTrends com tratamento robusto"""
    pytrends = get_pytrends()
    timeframe = convert_days_to_timeframe(days)
    
    try:
        # Tentativa 1
        pytrends.build_payload(
            kw_list=keywords,
            timeframe=timeframe,
            geo='BR'
        )
        time.sleep(1)
        df = pytrends.interest_over_time()
        
        if not df.empty:
            return df.drop(columns=['isPartial'])
        
        # Tentativa 2 se os dados estiverem vazios
        time.sleep(2)
        pytrends.build_payload(
            kw_list=keywords,
            timeframe=timeframe,
            geo=''
        )
        return pytrends.interest_over_time().drop(columns=['isPartial'])
        
    except Exception as e:
        logger.error(f"Erro PyTrends: {str(e)}")
        raise ResponseError(str(e))

def convert_days_to_timeframe(days):
    """Converte dias para formato do Google Trends"""
    if days <= 1:
        return 'now 1-H'
    elif days <= 7:
        return 'now 7-d'
    elif days <= 30:
        return 'today 1-m'
    elif days <= 90:
        return 'today 3-m'
    else:
        return 'today 12-m'