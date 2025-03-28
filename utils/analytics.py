from textblob import TextBlob
import pandas as pd
from textblob.exceptions import TranslatorError
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def analyze_sentiment(news_data):
    """Analisa sentimento com tratamento robusto"""
    if not news_data:
        return pd.DataFrame({'sentiment': [], 'count': []})
    
    sentiments = []
    for article in news_data:
        try:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            analysis = TextBlob(text)
            polarity = analysis.sentiment.polarity
            
            if polarity > 0.2:
                sentiment = 'positive'
            elif polarity < -0.2:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
                
            sentiments.append(sentiment)
        except Exception as e:
            logger.warning(f"Erro análise sentimento: {str(e)}")
            sentiments.append('neutral')
    
    result = pd.DataFrame({'sentiment': sentiments}).value_counts().reset_index(name='count')
    
    # Garante todas as categorias
    for sentiment in ['positive', 'neutral', 'negative']:
        if sentiment not in result['sentiment'].values:
            result = result.append({'sentiment': sentiment, 'count': 0}, ignore_index=True)
    
    return result

def detect_trends(news_data, trends_data):
    """Correlaciona notícias com tendências de forma robusta"""
    try:
        news_df = pd.DataFrame(news_data)
        if news_df.empty or trends_data.empty:
            return trends_data.reset_index()
        
        # Processa datas das notícias
        news_df['date'] = pd.to_datetime(news_df['publishedAt']).dt.normalize()
        
        # Processa datas das tendências
        trends_df = trends_data.reset_index()
        trends_df['date'] = pd.to_datetime(trends_df['date']).dt.normalize()
        
        # Agrega notícias por dia
        news_count = news_df.groupby('date').size().reset_index(name='news_count')
        
        # Combina os dados
        merged = pd.merge(trends_df, news_count, on='date', how='left')
        merged['news_count'] = merged['news_count'].fillna(0)
        
        return merged
        
    except Exception as e:
        logger.error(f"Erro detect_trends: {str(e)}")
        return trends_data.reset_index()