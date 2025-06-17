#!/usr/bin/env python3
"""
AgenticSeek Local Search Proxy
==============================

A lightweight, Docker-free alternative to SearxNG designed for Windows compatibility.
This search proxy aggregates results from multiple search engines and provides a unified API
for the AgenticSeek agent system.

Key Features:
- Multi-engine search aggregation (DuckDuckGo, Bing, Google)
- RESTful API compatible with SearxNG format
- Clean web interface for direct testing
- No external dependencies or Docker requirements
- Windows-native implementation

Supported Search Engines:
- DuckDuckGo: Privacy-focused search with instant answers
- Bing: Microsoft's search engine with comprehensive results
- Google: (Optional) Comprehensive web search

API Endpoints:
- GET /search?q=query&format=json - Search API endpoint
- GET /search?q=query - Web interface search
- GET / - Search homepage

Architecture:
- Flask web framework for HTTP server
- BeautifulSoup for HTML parsing
- Requests for HTTP client functionality
- Modular search engine classes for extensibility

Usage:
    python local_search.py
    # Server runs on http://localhost:5000

Author: AgenticSeek Team
License: See LICENSE file
"""

import requests
import json
import re
from urllib.parse import quote, urlencode
from flask import Flask, request, jsonify, render_template_string
from bs4 import BeautifulSoup
import time

# Initialize Flask application
app = Flask(__name__)

# Simple HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Local Search</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .search-box { width: 60%; padding: 10px; font-size: 16px; }
        .search-btn { padding: 10px 20px; font-size: 16px; }
        .result { margin: 20px 0; padding: 10px; border-left: 3px solid #007cba; }
        .result-title { font-size: 18px; font-weight: bold; color: #1a0dab; }
        .result-url { color: #006621; font-size: 14px; }
        .result-content { margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Local Search Engine</h1>
    <form method="GET" action="/search">
        <input type="text" name="q" placeholder="Enter your search query..." class="search-box" value="{{ query or '' }}">
        <button type="submit" class="search-btn">Search</button>
    </form>
    
    {% if results %}
    <h2>Search Results ({{ results|length }} found)</h2>
    {% for result in results %}
    <div class="result">
        <div class="result-title">{{ result.title }}</div>
        <div class="result-url">{{ result.url }}</div>
        <div class="result-content">{{ result.content }}</div>
    </div>
    {% endfor %}
    {% endif %}
</body>
</html>
"""

class SearchEngine:
    """Base class for search engines"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search(self, query, num_results=10):
        """Override in subclasses"""
        return []

class DuckDuckGoSearch(SearchEngine):
    """DuckDuckGo search engine"""
    
    def search(self, query, num_results=10):
        try:
            # DuckDuckGo instant answer API
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            # Get instant answers first
            response = requests.get('https://api.duckduckgo.com/', params=params, headers=self.headers, timeout=10)
            data = response.json()
            
            results = []
            
            # Add instant answer if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'DuckDuckGo Instant Answer'),
                    'url': data.get('AbstractURL', ''),
                    'content': data.get('Abstract', '')
                })
            
            # Add related topics
            for topic in data.get('RelatedTopics', [])[:num_results-len(results)]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('Text', '')[:100] + '...',
                        'url': topic.get('FirstURL', ''),
                        'content': topic.get('Text', '')
                    })
            
            return results[:num_results]
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []

class BingSearch(SearchEngine):
    """Bing search engine (requires API key, but provides fallback)"""
    
    def search(self, query, num_results=10):
        try:
            # Simple Bing search (note: this is a basic scraper, may break)
            search_url = f"https://www.bing.com/search?q={quote(query)}"
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Parse Bing search results
            for result in soup.find_all('li', class_='b_algo')[:num_results]:
                title_elem = result.find('h2')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.find('a')
                    url = link.get('href', '') if link else ''
                    
                    content_elem = result.find('p')
                    content = content_elem.get_text(strip=True) if content_elem else ''
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'content': content
                        })
            
            return results
            
        except Exception as e:
            print(f"Bing search error: {e}")
            return []

class MetaSearch:
    """Meta-search engine that combines results from multiple sources"""
    
    def __init__(self):
        self.engines = {
            'duckduckgo': DuckDuckGoSearch(),
            'bing': BingSearch()
        }
    
    def search(self, query, engines=['duckduckgo'], num_results=10):
        all_results = []
        
        for engine_name in engines:
            if engine_name in self.engines:
                try:
                    results = self.engines[engine_name].search(query, num_results)
                    for result in results:
                        result['engine'] = engine_name
                    all_results.extend(results)
                except Exception as e:
                    print(f"Error with {engine_name}: {e}")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        return unique_results[:num_results]

# Initialize meta-search
meta_search = MetaSearch()

@app.route('/')
def index():
    """Main search page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/search')
def search():
    """Search endpoint"""
    query = request.args.get('q', '').strip()
    format_type = request.args.get('format', 'html')
    engines = request.args.get('engines', 'duckduckgo').split(',')
    num_results = int(request.args.get('num', 10))
    
    if not query:
        if format_type == 'json':
            return jsonify({'error': 'No query provided'})
        return render_template_string(HTML_TEMPLATE, query=query, results=[])
    
    # Perform search
    results = meta_search.search(query, engines=engines, num_results=num_results)
    
    if format_type == 'json':
        return jsonify({
            'query': query,
            'engines': engines,
            'results': results,
            'total': len(results)
        })
    else:
        return render_template_string(HTML_TEMPLATE, query=query, results=results)

@app.route('/api/search')
def api_search():
    """API endpoint for JSON responses"""
    query = request.args.get('q', '').strip()
    engines = request.args.get('engines', 'duckduckgo').split(',')
    num_results = int(request.args.get('num', 10))
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = meta_search.search(query, engines=engines, num_results=num_results)
    
    return jsonify({
        'query': query,
        'engines': engines,
        'results': results,
        'total': len(results)
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'engines': list(meta_search.engines.keys())})

if __name__ == '__main__':
    print("Starting Local Search Engine...")
    print("Web interface: http://127.0.0.1:8080")
    print("API endpoint: http://127.0.0.1:8080/api/search?q=your+query")
    print("Health check: http://127.0.0.1:8080/health")
    app.run(host='127.0.0.1', port=8080, debug=True)
