from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError
import pandas as pd
import time
import logging
import random
from typing import List, Union

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendsFetcher:
    def __init__(self):
        self.pytrends = TrendReq(
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
        self.max_retries = 3
        self.retry_delay = 2

    def fetch_trends(
        self,
        keywords: Union[str, List[str]],
        timeframe: str = 'today 3-m',
        geo: str = 'BR',
        retry_count: int = 0
    ) -> pd.DataFrame:
        """
        Busca dados de tendências do Google Trends
        
        Args:
            keywords: Termo ou lista de termos (max 5)
            timeframe: Período de tempo no formato do Google Trends
            geo: Código do país
            retry_count: Contador interno para tentativas
            
        Returns:
            DataFrame com os dados ou vazio em caso de erro
        """
        try:
            if isinstance(keywords, str):
                keywords = [keywords]
                
            if len(keywords) > 5:
                logger.warning("Máximo de 5 keywords permitido. Usando as primeiras 5.")
                keywords = keywords[:5]
                
            self.pytrends.build_payload(
                kw_list=keywords,
                timeframe=timeframe,
                geo=geo
            )
            
            time.sleep(self.retry_delay)
            df = self.pytrends.interest_over_time()
            
            if not df.empty:
                return df.drop(columns=['isPartial'])
                
            logger.warning("Dados vazios retornados do Google Trends")
            return pd.DataFrame()
            
        except ResponseError as e:
            if retry_count < self.max_retries:
                logger.warning(f"Tentativa {retry_count + 1} falhou. Tentando novamente...")
                time.sleep(self.retry_delay * (retry_count + 1))
                return self.fetch_trends(keywords, timeframe, geo, retry_count + 1)
                
            logger.error(f"Erro no Google Trends após {self.max_retries} tentativas: {str(e)}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            return pd.DataFrame()

    def fetch_trends_safe(self, keywords: Union[str, List[str]], **kwargs) -> pd.DataFrame:
        """Versão com fallback para dados simulados"""
        try:
            trends = self.fetch_trends(keywords, **kwargs)
            if trends.empty:
                return self._generate_fallback_trends(keywords)
            return trends
        except Exception as e:
            logger.error(f"Erro crítico: {str(e)}")
            return self._generate_fallback_trends(keywords)

    def _generate_fallback_trends(self, keywords: Union[str, List[str]]) -> pd.DataFrame:
        """Gera dados de tendências simulados"""
        logger.info(f"Gerando dados simulados para: {keywords}")
        
        if isinstance(keywords, str):
            keywords = [keywords]
            
        date_range = pd.date_range(end=pd.Timestamp.today(), periods=90)
        data = {'date': date_range}
        
        for kw in keywords:
            # Padrão mais realista com variação
            base = [random.randint(20, 80) for _ in range(90)]
            smoothed = pd.Series(base).rolling(window=7).mean().fillna(method='bfill').tolist()
            data[kw] = [int(x) for x in smoothed]
            
        return pd.DataFrame(data)

    @staticmethod
    def convert_days_to_timeframe(days: int) -> str:
        """Converte número de dias para formato do Google Trends"""
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