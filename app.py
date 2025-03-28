from flask import Flask, render_template, jsonify, request
from utils.data_fetcher import fetch_news_data, fetch_trends_data
from utils.analytics import analyze_sentiment, detect_trends
import plotly.express as px
import json
import os
from datetime import datetime
import time
from pytrends.exceptions import ResponseError
from werkzeug.exceptions import HTTPException
import traceback
from functools import wraps

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Configuração de cache
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Configuração de logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Middleware de tratamento de erros
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Erro não tratado: {str(e)}\n{traceback.format_exc()}")
    
    if isinstance(e, HTTPException):
        return e
    
    return jsonify({
        "status": "error",
        "message": "Erro interno no servidor",
        "code": 500,
        "details": str(e)
    }), 500

# Decorator para validação de parâmetros
def validate_params(params):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for param, validator in params.items():
                value = request.args.get(param)
                if value and not validator(value):
                    return jsonify({
                        "status": "error",
                        "message": f"Parâmetro inválido: {param}"
                    }), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/news')
@validate_params({
    'days': lambda x: x.isdigit() and 1 <= int(x) <= 365,
    'query': lambda x: len(x) <= 100,
    'keywords': lambda x: len(x) <= 200
})
@cache.cached(timeout=300, query_string=True)
def get_news():
    query = request.args.get('query', 'tecnologia')
    days = int(request.args.get('days', 7))
    keywords = request.args.get('keywords', query)
    
    try:
        # Obter dados com tratamento de erro
        news_data = fetch_news_data(query, days)
        
        if not news_data:
            logger.warning("Nenhuma notícia encontrada para a query")
            return jsonify({
                'status': 'success',
                'message': 'Nenhuma notícia encontrada',
                'news': [],
                'analytics': {},
                'visualizations': {}
            })
        
        # PyTrends com fallback
        try:
            trends_data = fetch_trends_data(keywords.split(','), days)
        except ResponseError as e:
            logger.warning(f"PyTrends falhou, usando fallback: {str(e)}")
            trends_data = generate_fallback_trends(keywords.split(','), days)
        
        # Análises
        sentiment_results = analyze_sentiment(news_data)
        trend_analysis = detect_trends(news_data, trends_data)
        
        # Visualizações
        fig1 = px.line(trend_analysis, x='date', y=trend_analysis.columns[1], 
                      title=f'Tendência de Busca: {keywords}',
                      labels={'value': 'Interesse', 'date': 'Data'})
        
        fig2 = px.pie(sentiment_results, names='sentiment', values='count',
                     title='Análise de Sentimento',
                     color='sentiment',
                     color_discrete_map={
                         'positive': '#2ecc71',
                         'neutral': '#3498db',
                         'negative': '#e74c3c'
                     })
        
        return jsonify({
            'status': 'success',
            'news': format_news(news_data[:10]),
            'analytics': {
                'sentiment': sentiment_results.to_dict('records'),
                'trends': trend_analysis.describe().to_dict(),
                'keywords': keywords.split(',')
            },
            'visualizations': {
                'trend_graph': json.loads(fig1.to_json()),
                'sentiment_graph': json.loads(fig2.to_json())
            }
        })
        
    except Exception as e:
        logger.error(f"Erro na API: {str(e)}")
        raise  # Será capturado pelo handler de exceções

def format_news(news_items):
    """Formata os dados de notícias para o frontend"""
    formatted = []
    for item in news_items:
        try:
            published = datetime.strptime(item['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            date_str = published.strftime('%d/%m/%Y %H:%M')
        except (KeyError, ValueError):
            date_str = item.get('publishedAt', '')
            
        formatted.append({
            'title': item.get('title', ''),
            'source': item.get('source', {}).get('name', 'Fonte desconhecida'),
            'date': date_str,
            'url': item.get('url', '#'),
            'content': (item.get('content', '')[:200] + '...') if item.get('content') else '',
            'image': item.get('urlToImage', '')
        })
    return formatted

def generate_fallback_trends(keywords, days):
    """Gera dados simulados quando o PyTrends falha"""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(end=datetime.today(), periods=days)
    data = {'date': dates}
    for kw in keywords:
        # Padrão mais realista com alguma variação
        base = np.linspace(0, 100, days)
        noise = np.random.normal(0, 10, days)
        data[kw] = np.clip(base + noise, 0, 100).astype(int)
    
    return pd.DataFrame(data)

@app.route('/api/real-time')
def real_time_updates():
    """Endpoint para dados simulados em tempo real"""
    from random import randint
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'value': randint(1, 100),
        'metric': 'engagement',
        'status': 'success'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)