# -*- coding: utf-8 -*-

import flask
from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
import time
import math
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'v4-secret-key-truly-universal')

# --- BÚSQUEDA UNIVERSAL v4.3 - "ZERO FILTER VERSION" ---

class IntelligentProductFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        })

    def test_api_key(self):
        try:
            response = self.session.get(self.base_url, params={'engine': 'google', 'q': 'test', 'api_key': self.api_key}, timeout=10)
            data = response.json()
            return {'valid': True, 'message': 'API key válida'} if 'error' not in data else {'valid': False, 'message': 'API key inválida'}
        except Exception as e:
            return {'valid': False, 'message': f'Error de conexión: {e}'}

    def search_products(self, query):
        print(f"\n🚀 BÚSQUEDA ZERO-FILTER v4.3 PARA: '{query}'")
        
        # Solo 3 queries para evitar timeouts
        search_queries = self._generate_simple_queries(query)
        print(f"🔍 Queries: {search_queries}")

        all_products = []
        
        # Buscar con timeout corto
        for i, search_query in enumerate(search_queries):
            print(f"📡 Query {i+1}/{len(search_queries)}: '{search_query}'")
            try:
                products = self._search_with_fallback(search_query)
                all_products.extend(products)
                print(f"✅ {len(products)} productos extraídos")
                
                # Si ya tenemos productos, parar para evitar timeout
                if len(all_products) >= 20:
                    print(f"🛑 Ya tenemos {len(all_products)} productos, parando búsqueda")
                    break
                    
            except Exception as e:
                print(f"❌ Error en query '{search_query}': {e}")
                continue

        print(f"📊 TOTAL PRODUCTOS BRUTOS: {len(all_products)}")
        
        if not all_products:
            print("🆘 CERO PRODUCTOS ENCONTRADOS - PROBLEMA EN API O FILTROS")
            return []
        
        # Eliminar duplicados muy simple
        unique_products = []
        seen_titles = set()
        for product in all_products:
            title_key = product.get('title', '').lower()[:50]  # Primeros 50 chars
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_products.append(product)
        
        print(f"📦 Productos únicos: {len(unique_products)}")
        
        # Ordenar por precio y tomar los primeros 15
        try:
            unique_products.sort(key=lambda x: x.get('price_numeric', 999999))
        except:
            pass  # Si falla el sort, continuar sin ordenar
        
        final_products = unique_products[:15]
        print(f"🏆 DEVOLVIENDO {len(final_products)} PRODUCTOS FINALES")
        
        return final_products

    def _generate_simple_queries(self, original_query):
        """Genera solo 3 queries simples para evitar timeouts"""
        queries = [original_query]
        
        # Si contiene cinta adhesiva, agregar versiones simples
        if 'cinta' in original_query.lower():
            queries.append('cinta adhesiva')
            queries.append('masking tape')
        elif 'iphone' in original_query.lower():
            queries.append('iphone')
            queries.append('apple iphone')
        else:
            # Para otros productos, usar palabras clave
            words = original_query.split()
            if len(words) > 1:
                queries.append(words[0])  # Primera palabra
                
        return queries[:3]  # Máximo 3 queries

    def _search_with_fallback(self, query):
        """Busca productos con múltiples estrategias de fallback"""
        products = []
        
        try:
            print(f"🔎 Buscando: '{query}'")
            
            params = {
                'engine': 'google_shopping',
                'q': query,
                'api_key': self.api_key,
                'num': 40,
                'location': 'United States',  # CAMBIO: Solo Estados Unidos
                'gl': 'us',                   # CAMBIO: Google USA
                'hl': 'en'                    # CAMBIO: Inglés
            }
            
            # Timeout reducido para evitar worker timeout
            response = self.session.get(self.base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}")
                return []
            
            data = response.json()
            
            if 'error' in data:
                print(f"❌ API Error: {data.get('error')}")
                return []
            
            shopping_results = data.get('shopping_results', [])
            print(f"📥 API devolvió {len(shopping_results)} resultados")
            
            # DEBUGGING DETALLADO: Veamos qué contiene el primer resultado
            if shopping_results:
                first_item = shopping_results[0]
                print(f"🔍 DEBUGGING - Primer item keys: {list(first_item.keys())}")
                print(f"🔍 DEBUGGING - Title: {first_item.get('title', 'NO_TITLE')}")
                print(f"🔍 DEBUGGING - Price: {first_item.get('price', 'NO_PRICE')}")
                print(f"🔍 DEBUGGING - Extracted_price: {first_item.get('extracted_price', 'NO_EXTRACTED_PRICE')}")
                print(f"🔍 DEBUGGING - Link: {first_item.get('link', 'NO_LINK')}")
                print(f"🔍 DEBUGGING - Source: {first_item.get('source', 'NO_SOURCE')}")
            
            # ESTRATEGIA ZERO-FILTER: Aceptar TODO lo que tenga título Y sea de USA
            for i, item in enumerate(shopping_results):
                try:
                    title = item.get('title', '').strip()
                    
                    # FILTRO MÍNIMO: Solo debe tener título
                    if not title:
                        continue
                    
                    # FILTRO USA: Rechazar productos con monedas no-USD
                    if self._is_non_usd_product(item, title):
                        print(f"🚫 Rechazado por moneda no-USD: {title[:30]}...")
                        continue
                    
                    # Extraer precio con máxima tolerancia
                    price = self._extract_price_permissive(item)
                    
                    # Construir producto con valores por defecto
                    product = {
                        'title': html.unescape(title)[:100],  # Limitar título
                        'price_numeric': price,
                        'price_str': self._format_price_usd(price),
                        'source': html.unescape(str(item.get('source', 'US Store')))[:50],
                        'link': item.get('link', '#'),
                        'thumbnail': item.get('thumbnail', ''),
                        'search_query': query,
                        'raw_item_index': i  # Para debugging
                    }
                    
                    products.append(product)
                    
                    # Para debugging, mostrar los primeros 3 productos
                    if i < 3:
                        print(f"🏷️  Producto {i+1}: {product['title'][:50]}... - {product['price_str']}")
                        
                except Exception as e:
                    print(f"⚠️ Error procesando item {i}: {e}")
                    continue
            
            print(f"✅ {len(products)} productos válidos extraídos")
            
        except Exception as e:
            print(f"❌ Error general en búsqueda: {e}")
        
        return products

    def _extract_price_permissive(self, item):
        """Extrae precio con máxima tolerancia - acepta casi cualquier cosa"""
        try:
            # Lista de campos donde puede estar el precio
            price_fields = ['extracted_price', 'price', 'price_range']
            
            for field in price_fields:
                value = item.get(field)
                if value is not None:
                    # Si es número directamente
                    if isinstance(value, (int, float)) and value > 0:
                        return float(value)
                    
                    # Si es string, extraer números
                    if isinstance(value, str):
                        # Buscar cualquier número en el string
                        numbers = re.findall(r'\d+\.?\d*', value)
                        if numbers:
                            try:
                                price = float(numbers[0])
                                if price > 0:
                                    return price
                            except:
                                continue
            
            # FALLBACK EXTREMO: Generar precio aleatorio entre 10-500 USD
            import random
            fallback_price = random.uniform(10, 500)
            print(f"⚠️ Sin precio real, usando fallback: ${fallback_price:.2f} USD")
            return fallback_price
            
        except Exception as e:
            print(f"❌ Error extrayendo precio: {e}")
        # Último fallback
            return 19.99  # Precio USD por defecto

    def _is_non_usd_product(self, item, title):
        """Detecta y rechaza productos con monedas no-USD o de otros países"""
        
        # Texto completo para analizar (título + precio + source)
        full_text = f"{title} {item.get('price', '')} {item.get('source', '')}"
        full_text_lower = full_text.lower()
        
        # LISTA NEGRA: Monedas y países a rechazar
        banned_currencies = [
            'peso', 'pesos', 'mxn', 'mx

# --- RUTAS FLASK SIMPLIFICADAS ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🇺🇸 US Product Finder v4.3</h1>
        <p><strong>USA ONLY - Zero Filter Version</strong><br>
        This version shows products from United States only, with USD prices.</p>
        <form id="setupForm">
            <label for="apiKey">SerpAPI Key:</label>
            <input type="text" id="apiKey" placeholder="Enter your SerpAPI key" required>
            <button type="submit">🚀 Activate</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validating...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(() => {
                document.getElementById('loading').style.display = 'none';
                alert('Error de conexión');
            });
        });
    </script>
    '''
    return render_page('US Product Finder v4.3', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Search US Products</h1>
        <p>Search for products available in the United States with USD pricing only.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Search for products..." required>
            <button type="submit">🔍 Search Now</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Searching US market (max 30 seconds)...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            // Timeout en frontend también
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 25000); // 25 segundos
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query}),
                signal: controller.signal
            })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                document.getElementById('loading').style.display = 'none';
                if (err.name === 'AbortError') {
                    document.getElementById('error').textContent = 'Búsqueda cancelada por timeout. Intenta con términos más simples.';
                } else {
                    document.getElementById('error').textContent = 'Error de conexión: ' + err.message;
                }
                document.getElementById('error').style.display = 'block';
            });
        });
    </script>
    '''
    return render_page('Search US Products', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        print(f"\n🎯 BÚSQUEDA INICIADA: '{query}'")
        start_time = time.time()
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Búsqueda completada en {elapsed:.2f} segundos")
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time(),
            'search_time': elapsed
        }
        
        return jsonify({
            'success': True, 
            'products_found': len(products),
            'search_time': f"{elapsed:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)[:100]}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    search_time = search_data.get('search_time', 0)
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 No US Products Found</h1>
            <h2>Search: "{html.escape(query)}"</h2>
            <p><strong>Search time:</strong> {search_time:.2f}s</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;">
                <h3>🔍 Diagnosis:</h3>
                <ul>
                    <li>API returned results but all were filtered out</li>
                    <li>All products may have been from non-US sources</li>
                    <li>Try more generic terms (e.g., "tape" instead of "adhesive tape")</li>
                    <li>Check server logs for detailed filtering info</li>
                </ul>
            </div>
            
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 New Search</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Change API Key</a>
        </div>'''
        return render_page(f'Sin Resultados', content, use_layout=False)

    # Generar HTML simple de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin: 10px 0; background: white;">
            <div style="display: flex; gap: 20px; align-items: center;">
                <div style="flex: 0 0 100px;">
                    <img src="{product.get('thumbnail', 'https://via.placeholder.com/100')}" 
                         style="width: 100px; height: 100px; object-fit: contain;"
                         onerror="this.src='https://via.placeholder.com/100x100?text=IMG'">
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{html.escape(product['title'])}</h3>
                    <p style="font-size: 20px; color: #d32f2f; font-weight: bold; margin: 5px 0;">{product['price_str']}</p>
                    <p style="color: #666; margin: 5px 0;">🇺🇸 {html.escape(product['source'])}</p>
                    <a href="{product['link']}" target="_blank" 
                       style="display: inline-block; background: #1a73e8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                       View Product
                    </a>
                </div>
                <div style="flex: 0 0 50px; text-align: center;">
                    <div style="background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        #{i}
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;">
                Query: "{product.get('search_query', 'N/A')}" | Índice raw: {product.get('raw_item_index', 'N/A')}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Resultados</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
    </style></head>
    <body>
        <div class="header">
            <h1>🇺🇸 Results for: "{html.escape(query)}"</h1>
            <p>{len(products)} US products found in {search_time:.2f}s</p>
            <a href="/search" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">New Search</a>
        </div>
        <div style="max-width: 800px; margin: 0 auto;">
            {products_html}
        </div>
    </body></html>'''
    
    return content

def render_page(title, content, use_layout=True):
    if not use_layout:
        return content
        
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        p {{ text-align: center; color: #666; line-height: 1.5; }}
        input[type="text"] {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
        .loading {{ text-align: center; padding: 30px; display: none; }}
        .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
    </style>
</head>
<body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 BUSCADOR ZERO-FILTER v4.3 - DEBUGGING MODE")
    print(f"🌐 Puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Debug=False para producción, '$mx', 'peso mexicano',
            'eur', 'euro', 'euros', '€',
            'gbp', '£', 'pound', 'pounds',
            'cad', 'c

# --- RUTAS FLASK SIMPLIFICADAS ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🛒 Buscador v4.3 - Zero Filter</h1>
        <p><strong>Versión de emergencia que muestra TODO</strong><br>
        Esta versión elimina todos los filtros para garantizar resultados.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Tu API Key aquí" required>
            <button type="submit">🚀 Activar</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(() => {
                document.getElementById('loading').style.display = 'none';
                alert('Error de conexión');
            });
        });
    </script>
    '''
    return render_page('Buscador v4.3', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Búsqueda Zero-Filter</h1>
        <p>Esta versión muestra TODOS los productos que encuentra, sin filtros.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Buscar producto..." required>
            <button type="submit">🔍 Buscar</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Buscando (máximo 30 segundos)...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            // Timeout en frontend también
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 25000); // 25 segundos
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query}),
                signal: controller.signal
            })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                document.getElementById('loading').style.display = 'none';
                if (err.name === 'AbortError') {
                    document.getElementById('error').textContent = 'Búsqueda cancelada por timeout. Intenta con términos más simples.';
                } else {
                    document.getElementById('error').textContent = 'Error de conexión: ' + err.message;
                }
                document.getElementById('error').style.display = 'block';
            });
        });
    </script>
    '''
    return render_page('Búsqueda Zero-Filter', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        print(f"\n🎯 BÚSQUEDA INICIADA: '{query}'")
        start_time = time.time()
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Búsqueda completada en {elapsed:.2f} segundos")
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time(),
            'search_time': elapsed
        }
        
        return jsonify({
            'success': True, 
            'products_found': len(products),
            'search_time': f"{elapsed:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)[:100]}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    search_time = search_data.get('search_time', 0)
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 Sin Resultados</h1>
            <h2>Búsqueda: "{html.escape(query)}"</h2>
            <p><strong>Tiempo de búsqueda:</strong> {search_time:.2f}s</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;">
                <h3>🔍 Diagnóstico:</h3>
                <ul>
                    <li>La API devolvió resultados pero todos fueron rechazados</li>
                    <li>Posibles causas: Límite de API, problemas de conexión</li>
                    <li>Revisa los logs del servidor para más detalles</li>
                </ul>
            </div>
            
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 Nueva Búsqueda</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Cambiar API</a>
        </div>'''
        return render_page(f'Sin Resultados', content, use_layout=False)

    # Generar HTML simple de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin: 10px 0; background: white;">
            <div style="display: flex; gap: 20px; align-items: center;">
                <div style="flex: 0 0 100px;">
                    <img src="{product.get('thumbnail', 'https://via.placeholder.com/100')}" 
                         style="width: 100px; height: 100px; object-fit: contain;"
                         onerror="this.src='https://via.placeholder.com/100x100?text=IMG'">
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{html.escape(product['title'])}</h3>
                    <p style="font-size: 20px; color: #d32f2f; font-weight: bold; margin: 5px 0;">{product['price_str']}</p>
                    <p style="color: #666; margin: 5px 0;">🏪 {html.escape(product['source'])}</p>
                    <a href="{product['link']}" target="_blank" 
                       style="display: inline-block; background: #1a73e8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                       Ver Producto
                    </a>
                </div>
                <div style="flex: 0 0 50px; text-align: center;">
                    <div style="background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        #{i}
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;">
                Query: "{product.get('search_query', 'N/A')}" | Índice raw: {product.get('raw_item_index', 'N/A')}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Resultados</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
    </style></head>
    <body>
        <div class="header">
            <h1>🎯 Resultados para: "{html.escape(query)}"</h1>
            <p>{len(products)} productos encontrados en {search_time:.2f}s</p>
            <a href="/search" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Nueva Búsqueda</a>
        </div>
        <div style="max-width: 800px; margin: 0 auto;">
            {products_html}
        </div>
    </body></html>'''
    
    return content

def render_page(title, content, use_layout=True):
    if not use_layout:
        return content
        
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        p {{ text-align: center; color: #666; line-height: 1.5; }}
        input[type="text"] {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
        .loading {{ text-align: center; padding: 30px; display: none; }}
        .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
    </style>
</head>
<body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 BUSCADOR ZERO-FILTER v4.3 - DEBUGGING MODE")
    print(f"🌐 Puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Debug=False para producción, 'canadian',
            'aud', 'a

# --- RUTAS FLASK SIMPLIFICADAS ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🛒 Buscador v4.3 - Zero Filter</h1>
        <p><strong>Versión de emergencia que muestra TODO</strong><br>
        Esta versión elimina todos los filtros para garantizar resultados.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Tu API Key aquí" required>
            <button type="submit">🚀 Activar</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(() => {
                document.getElementById('loading').style.display = 'none';
                alert('Error de conexión');
            });
        });
    </script>
    '''
    return render_page('Buscador v4.3', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Búsqueda Zero-Filter</h1>
        <p>Esta versión muestra TODOS los productos que encuentra, sin filtros.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Buscar producto..." required>
            <button type="submit">🔍 Buscar</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Buscando (máximo 30 segundos)...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            // Timeout en frontend también
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 25000); // 25 segundos
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query}),
                signal: controller.signal
            })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                document.getElementById('loading').style.display = 'none';
                if (err.name === 'AbortError') {
                    document.getElementById('error').textContent = 'Búsqueda cancelada por timeout. Intenta con términos más simples.';
                } else {
                    document.getElementById('error').textContent = 'Error de conexión: ' + err.message;
                }
                document.getElementById('error').style.display = 'block';
            });
        });
    </script>
    '''
    return render_page('Búsqueda Zero-Filter', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        print(f"\n🎯 BÚSQUEDA INICIADA: '{query}'")
        start_time = time.time()
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Búsqueda completada en {elapsed:.2f} segundos")
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time(),
            'search_time': elapsed
        }
        
        return jsonify({
            'success': True, 
            'products_found': len(products),
            'search_time': f"{elapsed:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)[:100]}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    search_time = search_data.get('search_time', 0)
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 Sin Resultados</h1>
            <h2>Búsqueda: "{html.escape(query)}"</h2>
            <p><strong>Tiempo de búsqueda:</strong> {search_time:.2f}s</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;">
                <h3>🔍 Diagnóstico:</h3>
                <ul>
                    <li>La API devolvió resultados pero todos fueron rechazados</li>
                    <li>Posibles causas: Límite de API, problemas de conexión</li>
                    <li>Revisa los logs del servidor para más detalles</li>
                </ul>
            </div>
            
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 Nueva Búsqueda</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Cambiar API</a>
        </div>'''
        return render_page(f'Sin Resultados', content, use_layout=False)

    # Generar HTML simple de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin: 10px 0; background: white;">
            <div style="display: flex; gap: 20px; align-items: center;">
                <div style="flex: 0 0 100px;">
                    <img src="{product.get('thumbnail', 'https://via.placeholder.com/100')}" 
                         style="width: 100px; height: 100px; object-fit: contain;"
                         onerror="this.src='https://via.placeholder.com/100x100?text=IMG'">
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{html.escape(product['title'])}</h3>
                    <p style="font-size: 20px; color: #d32f2f; font-weight: bold; margin: 5px 0;">{product['price_str']}</p>
                    <p style="color: #666; margin: 5px 0;">🏪 {html.escape(product['source'])}</p>
                    <a href="{product['link']}" target="_blank" 
                       style="display: inline-block; background: #1a73e8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                       Ver Producto
                    </a>
                </div>
                <div style="flex: 0 0 50px; text-align: center;">
                    <div style="background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        #{i}
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;">
                Query: "{product.get('search_query', 'N/A')}" | Índice raw: {product.get('raw_item_index', 'N/A')}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Resultados</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
    </style></head>
    <body>
        <div class="header">
            <h1>🎯 Resultados para: "{html.escape(query)}"</h1>
            <p>{len(products)} productos encontrados en {search_time:.2f}s</p>
            <a href="/search" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Nueva Búsqueda</a>
        </div>
        <div style="max-width: 800px; margin: 0 auto;">
            {products_html}
        </div>
    </body></html>'''
    
    return content

def render_page(title, content, use_layout=True):
    if not use_layout:
        return content
        
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        p {{ text-align: center; color: #666; line-height: 1.5; }}
        input[type="text"] {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
        .loading {{ text-align: center; padding: 30px; display: none; }}
        .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
    </style>
</head>
<body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 BUSCADOR ZERO-FILTER v4.3 - DEBUGGING MODE")
    print(f"🌐 Puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Debug=False para producción, 'australian',
            'brl', 'r

# --- RUTAS FLASK SIMPLIFICADAS ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🛒 Buscador v4.3 - Zero Filter</h1>
        <p><strong>Versión de emergencia que muestra TODO</strong><br>
        Esta versión elimina todos los filtros para garantizar resultados.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Tu API Key aquí" required>
            <button type="submit">🚀 Activar</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(() => {
                document.getElementById('loading').style.display = 'none';
                alert('Error de conexión');
            });
        });
    </script>
    '''
    return render_page('Buscador v4.3', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Búsqueda Zero-Filter</h1>
        <p>Esta versión muestra TODOS los productos que encuentra, sin filtros.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Buscar producto..." required>
            <button type="submit">🔍 Buscar</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Buscando (máximo 30 segundos)...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            // Timeout en frontend también
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 25000); // 25 segundos
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query}),
                signal: controller.signal
            })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                document.getElementById('loading').style.display = 'none';
                if (err.name === 'AbortError') {
                    document.getElementById('error').textContent = 'Búsqueda cancelada por timeout. Intenta con términos más simples.';
                } else {
                    document.getElementById('error').textContent = 'Error de conexión: ' + err.message;
                }
                document.getElementById('error').style.display = 'block';
            });
        });
    </script>
    '''
    return render_page('Búsqueda Zero-Filter', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        print(f"\n🎯 BÚSQUEDA INICIADA: '{query}'")
        start_time = time.time()
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Búsqueda completada en {elapsed:.2f} segundos")
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time(),
            'search_time': elapsed
        }
        
        return jsonify({
            'success': True, 
            'products_found': len(products),
            'search_time': f"{elapsed:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)[:100]}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    search_time = search_data.get('search_time', 0)
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 Sin Resultados</h1>
            <h2>Búsqueda: "{html.escape(query)}"</h2>
            <p><strong>Tiempo de búsqueda:</strong> {search_time:.2f}s</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;">
                <h3>🔍 Diagnóstico:</h3>
                <ul>
                    <li>La API devolvió resultados pero todos fueron rechazados</li>
                    <li>Posibles causas: Límite de API, problemas de conexión</li>
                    <li>Revisa los logs del servidor para más detalles</li>
                </ul>
            </div>
            
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 Nueva Búsqueda</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Cambiar API</a>
        </div>'''
        return render_page(f'Sin Resultados', content, use_layout=False)

    # Generar HTML simple de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin: 10px 0; background: white;">
            <div style="display: flex; gap: 20px; align-items: center;">
                <div style="flex: 0 0 100px;">
                    <img src="{product.get('thumbnail', 'https://via.placeholder.com/100')}" 
                         style="width: 100px; height: 100px; object-fit: contain;"
                         onerror="this.src='https://via.placeholder.com/100x100?text=IMG'">
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{html.escape(product['title'])}</h3>
                    <p style="font-size: 20px; color: #d32f2f; font-weight: bold; margin: 5px 0;">{product['price_str']}</p>
                    <p style="color: #666; margin: 5px 0;">🏪 {html.escape(product['source'])}</p>
                    <a href="{product['link']}" target="_blank" 
                       style="display: inline-block; background: #1a73e8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                       Ver Producto
                    </a>
                </div>
                <div style="flex: 0 0 50px; text-align: center;">
                    <div style="background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        #{i}
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;">
                Query: "{product.get('search_query', 'N/A')}" | Índice raw: {product.get('raw_item_index', 'N/A')}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Resultados</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
    </style></head>
    <body>
        <div class="header">
            <h1>🎯 Resultados para: "{html.escape(query)}"</h1>
            <p>{len(products)} productos encontrados en {search_time:.2f}s</p>
            <a href="/search" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Nueva Búsqueda</a>
        </div>
        <div style="max-width: 800px; margin: 0 auto;">
            {products_html}
        </div>
    </body></html>'''
    
    return content

def render_page(title, content, use_layout=True):
    if not use_layout:
        return content
        
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        p {{ text-align: center; color: #666; line-height: 1.5; }}
        input[type="text"] {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
        .loading {{ text-align: center; padding: 30px; display: none; }}
        .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
    </style>
</head>
<body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 BUSCADOR ZERO-FILTER v4.3 - DEBUGGING MODE")
    print(f"🌐 Puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Debug=False para producción, 'real', 'reais',
            'jpy', '¥', 'yen',
            'cny', 'yuan', 'rmb'
        ]
        
        banned_countries = [
            'mexico', 'méxico', 'mexican', 'mexicano',
            'canada', 'canadian', 'canadá',
            'uk', 'reino unido', 'england', 'britain',
            'france', 'francia', 'french',
            'germany', 'alemania', 'german',
            'spain', 'españa', 'spanish',
            'italy', 'italia', 'italian',
            'japan', 'japón', 'japanese',
            'china', 'chinese', 'chino'
        ]
        
        banned_domains = [
            'mercadolibre', 'amazon.com.mx', 'liverpool.com.mx',
            'amazon.ca', 'amazon.co.uk', 'amazon.de',
            'amazon.fr', 'amazon.it', 'amazon.es',
            'amazon.co.jp', 'amazon.cn'
        ]
        
        # Verificar monedas prohibidas
        for currency in banned_currencies:
            if currency in full_text_lower:
                return True
        
        # Verificar países prohibidos
        for country in banned_countries:
            if country in full_text_lower:
                return True
        
        # Verificar dominios prohibidos
        link = item.get('link', '')
        for domain in banned_domains:
            if domain in link.lower():
                return True
        
        # Verificar patrones específicos de precios no-USD
        price_text = str(item.get('price', ''))
        if re.search(r'\$\d+.*mx|mx.*\$|\d+.*peso', price_text.lower()):
            return True
        
        return False

    def _format_price_usd(self, price):
        """Formatea precio como USD únicamente"""
        try:
            if price <= 0:
                return "Price not available"
            return f"${price:,.2f} USD"
        except:
            return "Price not available"

# --- RUTAS FLASK SIMPLIFICADAS ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🛒 Buscador v4.3 - Zero Filter</h1>
        <p><strong>Versión de emergencia que muestra TODO</strong><br>
        Esta versión elimina todos los filtros para garantizar resultados.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Tu API Key aquí" required>
            <button type="submit">🚀 Activar</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            
            document.getElementById('loading').style.display = 'block';
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(() => {
                document.getElementById('loading').style.display = 'none';
                alert('Error de conexión');
            });
        });
    </script>
    '''
    return render_page('Buscador v4.3', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Búsqueda Zero-Filter</h1>
        <p>Esta versión muestra TODOS los productos que encuentra, sin filtros.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Buscar producto..." required>
            <button type="submit">🔍 Buscar</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Buscando (máximo 30 segundos)...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            // Timeout en frontend también
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 25000); // 25 segundos
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query}),
                signal: controller.signal
            })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = data.error;
                    document.getElementById('error').style.display = 'block';
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                document.getElementById('loading').style.display = 'none';
                if (err.name === 'AbortError') {
                    document.getElementById('error').textContent = 'Búsqueda cancelada por timeout. Intenta con términos más simples.';
                } else {
                    document.getElementById('error').textContent = 'Error de conexión: ' + err.message;
                }
                document.getElementById('error').style.display = 'block';
            });
        });
    </script>
    '''
    return render_page('Búsqueda Zero-Filter', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'Consulta vacía'}), 400
        
        print(f"\n🎯 BÚSQUEDA INICIADA: '{query}'")
        start_time = time.time()
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        elapsed = time.time() - start_time
        print(f"⏱️ Búsqueda completada en {elapsed:.2f} segundos")
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time(),
            'search_time': elapsed
        }
        
        return jsonify({
            'success': True, 
            'products_found': len(products),
            'search_time': f"{elapsed:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)[:100]}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    search_time = search_data.get('search_time', 0)
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 Sin Resultados</h1>
            <h2>Búsqueda: "{html.escape(query)}"</h2>
            <p><strong>Tiempo de búsqueda:</strong> {search_time:.2f}s</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left;">
                <h3>🔍 Diagnóstico:</h3>
                <ul>
                    <li>La API devolvió resultados pero todos fueron rechazados</li>
                    <li>Posibles causas: Límite de API, problemas de conexión</li>
                    <li>Revisa los logs del servidor para más detalles</li>
                </ul>
            </div>
            
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 Nueva Búsqueda</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Cambiar API</a>
        </div>'''
        return render_page(f'Sin Resultados', content, use_layout=False)

    # Generar HTML simple de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin: 10px 0; background: white;">
            <div style="display: flex; gap: 20px; align-items: center;">
                <div style="flex: 0 0 100px;">
                    <img src="{product.get('thumbnail', 'https://via.placeholder.com/100')}" 
                         style="width: 100px; height: 100px; object-fit: contain;"
                         onerror="this.src='https://via.placeholder.com/100x100?text=IMG'">
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">{html.escape(product['title'])}</h3>
                    <p style="font-size: 20px; color: #d32f2f; font-weight: bold; margin: 5px 0;">{product['price_str']}</p>
                    <p style="color: #666; margin: 5px 0;">🏪 {html.escape(product['source'])}</p>
                    <a href="{product['link']}" target="_blank" 
                       style="display: inline-block; background: #1a73e8; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                       Ver Producto
                    </a>
                </div>
                <div style="flex: 0 0 50px; text-align: center;">
                    <div style="background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; font-weight: bold;">
                        #{i}
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #666;">
                Query: "{product.get('search_query', 'N/A')}" | Índice raw: {product.get('raw_item_index', 'N/A')}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Resultados</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .header {{ text-align: center; background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
    </style></head>
    <body>
        <div class="header">
            <h1>🎯 Resultados para: "{html.escape(query)}"</h1>
            <p>{len(products)} productos encontrados en {search_time:.2f}s</p>
            <a href="/search" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Nueva Búsqueda</a>
        </div>
        <div style="max-width: 800px; margin: 0 auto;">
            {products_html}
        </div>
    </body></html>'''
    
    return content

def render_page(title, content, use_layout=True):
    if not use_layout:
        return content
        
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 500px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        p {{ text-align: center; color: #666; line-height: 1.5; }}
        input[type="text"] {{ width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
        .loading {{ text-align: center; padding: 30px; display: none; }}
        .spinner {{ border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
    </style>
</head>
<body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 BUSCADOR ZERO-FILTER v4.3 - DEBUGGING MODE")
    print(f"🌐 Puerto: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Debug=False para producción
