import os
import time
from datetime import datetime, timedelta
from newsapi import NewsApiClient
import logging
from typing import List, Dict, Union

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsFetcher:
    def __init__(self):
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            raise ValueError("NEWS_API_KEY não encontrada nas variáveis de ambiente")
        
        self.newsapi = NewsApiClient(api_key=api_key)
        self.max_retries = 3
        self.retry_delay = 2

    def fetch_news(
        self,
        query: str,
        days: int = 7,
        language: str = 'pt',
        retry_count: int = 0
    ) -> List[Dict[str, Union[str, Dict]]]:
        """
        Busca notícias da NewsAPI com tratamento robusto de erros e retry automático
        
        Args:
            query: Termo de busca
            days: Número de dias para buscar (máx 30)
            language: Idioma dos resultados
            retry_count: Contador interno para tentativas
            
        Returns:
            Lista de artigos ou lista vazia em caso de erro
        """
        try:
            date_from = (datetime.now() - timedelta(days=min(days, 30))).strftime('%Y-%m-%d')
            
            response = self.newsapi.get_everything(
                q=query,
                from_param=date_from,
                language=language,
                sort_by='relevancy',
                page_size=100
            )
            
            if not response.get('articles'):
                logger.warning(f"Nenhum artigo encontrado para a query: {query}")
                return []
                
            logger.info(f"Encontrados {len(response['articles'])} artigos para '{query}'")
            return response['articles']
            
        except Exception as e:
            if retry_count < self.max_retries:
                logger.warning(f"Tentativa {retry_count + 1} falhou. Tentando novamente...")
                time.sleep(self.retry_delay)
                return self.fetch_news(query, days, language, retry_count + 1)
                
            logger.error(f"Erro ao buscar notícias após {self.max_retries} tentativas: {str(e)}")
            return []

    def fetch_news_safe(self, query: str, **kwargs) -> List[Dict]:
        """Versão mais segura com fallback para dados simulados"""
        try:
            news = self.fetch_news(query, **kwargs)
            if not news:
                return self._generate_fallback_news(query)
            return news
        except Exception as e:
            logger.error(f"Erro crítico: {str(e)}")
            return self._generate_fallback_news(query)

    def _generate_fallback_news(self, query: str) -> List[Dict]:
        """Gera dados de notícias simulados para fallback"""
        logger.info(f"Gerando dados simulados para query: {query}")
        return [{
            'title': f'Artigo de exemplo sobre {query}',
            'description': f'Esta é uma descrição simulada sobre {query}',
            'publishedAt': datetime.now().isoformat(),
            'source': {'name': 'Fonte Simulada'},
            'url': 'https://example.com',
            'content': f'Conteúdo simulado sobre {query}...'
        } for _ in range(5)]