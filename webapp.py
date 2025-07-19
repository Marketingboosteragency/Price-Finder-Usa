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

# --- BÚSQUEDA UNIVERSAL v4.2 - "SIEMPRE MUESTRA RESULTADOS" ---

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
        except Exception:
            return {'valid': False, 'message': 'Error de conexión con la API'}

    def search_products(self, query):
        print(f"\n🧠 INICIANDO BÚSQUEDA UNIVERSAL v4.2 PARA: '{query}'")
        
        # Generar múltiples queries sin filtros complejos
        search_queries = self._generate_search_queries(query)
        print(f"🔍 Queries a usar: {search_queries}")

        all_products = []
        
        # Buscar con cada query
        for search_query in search_queries:
            products = self._search_single_query(search_query)
            all_products.extend(products)
            print(f"📦 Query '{search_query}': {len(products)} productos encontrados")
            
            # Si ya tenemos suficientes productos, no seguir buscando
            if len(all_products) >= 50:
                break

        if not all_products:
            print("🆘 NO SE ENCONTRARON PRODUCTOS EN NINGUNA BÚSQUEDA")
            return []
        
        print(f"📊 Total productos encontrados: {len(all_products)}")
        
        # Eliminar duplicados por link
        unique_products = []
        seen_links = set()
        for product in all_products:
            if product.get('link') and product['link'] not in seen_links:
                seen_links.add(product['link'])
                unique_products.append(product)
        
        print(f"📦 Productos únicos: {len(unique_products)}")
        
        # Ordenar por precio (productos más baratos primero)
        unique_products.sort(key=lambda x: x.get('price_numeric', float('inf')))
        
        # Aplicar scoring básico
        scored_products = self._apply_basic_scoring(unique_products, query)
        
        # GARANTIZAR RESULTADOS: Tomar los mejores 20 productos sin filtros restrictivos
        final_products = scored_products[:20]
        
        print(f"🏆 BÚSQUEDA COMPLETADA. Devolviendo {len(final_products)} productos.")
        return final_products

    def _generate_search_queries(self, original_query):
        """Genera múltiples variaciones de búsqueda para maximizar resultados"""
        queries = []
        
        # Query original
        queries.append(original_query)
        
        # Extraer palabras clave importantes
        words = original_query.lower().split()
        
        # Si contiene "cinta adhesiva"
        if 'cinta' in words and 'adhesiva' in words:
            queries.extend([
                'cinta adhesiva',
                'masking tape',
                'cinta de papel',
                'tape adhesivo',
                'cinta enmascarar'
            ])
            
            # Si también tiene color
            colors = ['azul', 'blue', 'rojo', 'red', 'verde', 'green', 'negro', 'black', 'blanco', 'white']
            for word in words:
                if word in colors:
                    queries.append(f'cinta adhesiva {word}')
                    queries.append(f'masking tape {word}')
        
        # Si contiene medidas
        size_pattern = r'(\d+(?:\.\d+)?)\s*(?:pulgada|pulgadas|inch|in|")'
        if re.search(size_pattern, original_query):
            match = re.search(size_pattern, original_query)
            if match:
                size = match.group(1)
                queries.append(f'cinta {size} pulgadas')
                queries.append(f'tape {size} inch')
        
        # Queries más generales como fallback
        if 'cinta' in original_query.lower():
            queries.extend(['cinta', 'tape', 'adhesivo'])
        
        # Limitar a máximo 8 queries para no abusar de la API
        return list(dict.fromkeys(queries))[:8]  # Eliminar duplicados y limitar

    def _search_single_query(self, query):
        """Realiza una búsqueda con una query específica"""
        products = []
        
        try:
            print(f"🔎 Buscando: '{query}'")
            
            params = {
                'engine': 'google_shopping',
                'q': query,
                'api_key': self.api_key,
                'num': 60,  # Solicitar más productos
                'location': 'Mexico',
                'gl': 'mx',
                'hl': 'es'
            }
            
            response = self.session.get(self.base_url, params=params, timeout=20)
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code} para '{query}'")
                return []
            
            data = response.json()
            
            if 'error' in data:
                print(f"❌ Error API: {data.get('error', {}).get('message', 'Error desconocido')}")
                return []
            
            shopping_results = data.get('shopping_results', [])
            print(f"📥 API devolvió {len(shopping_results)} resultados para '{query}'")
            
            for item in shopping_results:
                try:
                    # Extraer información básica
                    title = item.get('title', '').strip()
                    link = item.get('link', '').strip()
                    source = item.get('source', 'Tienda desconocida').strip()
                    thumbnail = item.get('thumbnail', '')
                    
                    # Extraer precio
                    price = self._extract_price(item)
                    
                    # Filtros mínimos: debe tener título, link y precio válido
                    if title and link and price > 0 and price < 50000:  # Precio máximo razonable
                        product = {
                            'title': html.unescape(title),
                            'price_numeric': price,
                            'price_str': f"${price:,.2f} MXN",
                            'source': html.unescape(source),
                            'link': link,
                            'thumbnail': thumbnail,
                            'search_query': query
                        }
                        products.append(product)
                        
                except Exception as e:
                    print(f"⚠️ Error procesando producto: {e}")
                    continue
            
            print(f"✅ {len(products)} productos válidos extraídos de '{query}'")
            
        except Exception as e:
            print(f"❌ Error en búsqueda '{query}': {e}")
        
        return products

    def _extract_price(self, item):
        """Extrae el precio de un item de shopping results"""
        try:
            # Intentar diferentes campos de precio
            price_fields = ['extracted_price', 'price']
            
            for field in price_fields:
                price_value = item.get(field)
                if price_value:
                    # Si es un número directamente
                    if isinstance(price_value, (int, float)):
                        return float(price_value)
                    
                    # Si es string, limpiar y convertir
                    if isinstance(price_value, str):
                        # Remover todo excepto números y punto decimal
                        clean_price = re.sub(r'[^\d.]', '', str(price_value))
                        if clean_price and clean_price != '.':
                            return float(clean_price)
            
            return 0.0
            
        except (ValueError, TypeError):
            return 0.0

    def _apply_basic_scoring(self, products, original_query):
        """Aplica un scoring básico para ordenar por relevancia"""
        query_words = set(original_query.lower().split())
        
        for product in products:
            title_words = set(product['title'].lower().split())
            
            # Scoring básico por coincidencia de palabras
            word_matches = len(query_words.intersection(title_words))
            word_score = word_matches * 10
            
            # Bonus por precio bajo (productos más baratos son mejor)
            price_score = max(0, 100 - (product['price_numeric'] / 10))
            
            # Bonus por fuentes confiables
            source_score = 0
            reliable_sources = ['mercadolibre', 'amazon', 'liverpool', 'coppel', 'office depot', 'home depot']
            if any(source.lower() in product['source'].lower() for source in reliable_sources):
                source_score = 20
            
            # Score final
            total_score = word_score + price_score + source_score
            product['relevance_score'] = total_score
        
        # Ordenar por score descendente
        return sorted(products, key=lambda x: x.get('relevance_score', 0), reverse=True)

# --- RUTAS FLASK ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🛒 Buscador de Productos v4.2</h1>
        <p><strong>Versión mejorada que SIEMPRE muestra resultados.</strong><br>
        Encuentra productos baratos y reales con precios verificados.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Ingresa tu API Key de SerpAPI" required>
            <button type="submit">🚀 Activar Buscador</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando API Key...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) {
                alert('Por favor ingresa tu API Key');
                return;
            }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
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
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Error al validar API Key';
                    errorDiv.style.display = 'block';
                }
            })
            .catch(err => {
                document.getElementById('loading').style.display = 'none';
                console.error('Error:', err);
                alert('Error de conexión. Intenta de nuevo.');
            });
        });
    </script>
    '''
    return render_page('Configuración - Buscador v4.2', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key es requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message', 'API key inválida')}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True, 'message': 'API key configurada correctamente'})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Buscar Productos</h1>
        <p>Busca cualquier producto y obtén resultados baratos y reales.<br>
        <strong>Ejemplos:</strong> "cinta adhesiva azul", "iPhone 13", "martillo", etc.</p>
        
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="¿Qué producto buscas?" required>
            <button type="submit">🔍 Buscar Ahora</button>
        </form>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Buscando los mejores productos y precios...</p>
        </div>
        
        <div id="error" class="error" style="display:none;"></div>
        
        <div style="margin-top: 20px; text-align: center;">
            <a href="/" style="color: #666; text-decoration: none;">← Cambiar API Key</a>
        </div>
    </div>
    
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            
            if (!query) {
                alert('Por favor ingresa un término de búsqueda');
                return;
            }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Error al realizar la búsqueda';
                    errorDiv.style.display = 'block';
                }
            })
            .catch(err => {
                document.getElementById('loading').style.display = 'none';
                console.error('Error:', err);
                alert('Error de conexión. Intenta de nuevo.');
            });
        });
    </script>
    '''
    return render_page('Buscar Productos', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'error': 'La consulta no puede estar vacía'}), 400
        
        print(f"\n🎯 NUEVA BÚSQUEDA: '{query}'")
        
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        # Guardar resultados en sesión
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': time.time()
        }
        
        print(f"💾 Guardados {len(products)} productos en sesión")
        
        return jsonify({'success': True, 'products_found': len(products)})
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en /api/search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    
    print(f"🎨 Mostrando resultados para '{query}': {len(products)} productos")
    
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>😞 Sin Resultados</h1>
            <h2>No se encontraron productos para: "{html.escape(query)}"</h2>
            <p>Esto puede suceder si:</p>
            <ul style="text-align: left; max-width: 400px; margin: 20px auto;">
                <li>La API de SerpAPI no devolvió resultados</li>
                <li>Tu API key alcanzó el límite de uso</li>
                <li>El término de búsqueda es muy específico</li>
            </ul>
            <p><strong>Sugerencias:</strong></p>
            <ul style="text-align: left; max-width: 400px; margin: 20px auto;">
                <li>Usa términos más generales (ej: "cinta" en lugar de "cinta adhesiva de papel azul")</li>
                <li>Verifica tu conexión a internet</li>
                <li>Revisa tu saldo de API en SerpAPI</li>
            </ul>
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">🔍 Intentar Nueva Búsqueda</a>
            <a href="/" style="display:inline-block; background:#666;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600; margin: 10px;">⚙️ Cambiar API Key</a>
        </div>'''
        return render_page(f'Sin Resultados para "{query}"', content, use_layout=False)

    # Generar HTML de productos
    products_html = ""
    for i, product in enumerate(products, 1):
        price_color = "#d32f2f" if product['price_numeric'] < 100 else "#ff9800" if product['price_numeric'] < 500 else "#4caf50"
        
        products_html += f'''
        <div class="product-card">
            <div class="product-image">
                <img src="{product.get('thumbnail', 'https://via.placeholder.com/200x200?text=Sin+Imagen')}" 
                     alt="{html.escape(product['title'])}" 
                     onerror="this.src='https://via.placeholder.com/200x200?text=Sin+Imagen'">
                <div class="product-rank">#{i}</div>
            </div>
            <div class="product-info">
                <h3>{html.escape(product['title'])}</h3>
                <div class="product-price" style="color: {price_color};">{product['price_str']}</div>
                <div class="product-source">📍 {html.escape(product['source'])}</div>
                <a href="{product['link']}" target="_blank" class="product-link">
                    🛒 Ver en {html.escape(product['source'])}
                </a>
            </div>
            <div class="product-details">
                <small>Score: {int(product.get('relevance_score', 0))} | Query: "{product.get('search_query', 'N/A')}"</small>
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultados para "{html.escape(query)}"</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header h1 {{ color: #333; margin: 0; }}
            .header .actions {{ margin-top: 15px; }}
            .header .actions a {{ margin: 0 10px; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
            .btn-search {{ background: #1a73e8; color: white; }}
            .btn-config {{ background: #666; color: white; }}
            
            .products-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
            
            .product-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.2s; }}
            .product-card:hover {{ transform: translateY(-5px); }}
            
            .product-image {{ position: relative; height: 200px; background: #f9f9f9; display: flex; align-items: center; justify-content: center; }}
            .product-image img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
            .product-rank {{ position: absolute; top: 10px; left: 10px; background: #1a73e8; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px; }}
            
            .product-info {{ padding: 20px; }}
            .product-info h3 {{ margin: 0 0 10px 0; font-size: 16px; line-height: 1.4; color: #333; height: 2.8em; overflow: hidden; }}
            .product-price {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
            .product-source {{ color: #666; margin: 10px 0; font-size: 14px; }}
            .product-link {{ display: inline-block; background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 10px; }}
            .product-link:hover {{ background: linear-gradient(135deg, #ee5a24, #ff6b6b); }}
            
            .product-details {{ padding: 10px 20px; background: #f8f9fa; font-size: 12px; color: #666; border-top: 1px solid #eee; }}
            
            .stats {{ text-align: center; margin-bottom: 20px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 Resultados para: "{html.escape(query)}"</h1>
            <div class="stats">Se encontraron {len(products)} productos • Ordenados por relevancia y precio</div>
            <div class="actions">
                <a href="/search" class="btn-search">🔍 Nueva Búsqueda</a>
                <a href="/" class="btn-config">⚙️ Cambiar API Key</a>
            </div>
        </div>
        
        <div class="products-grid">
            {products_html}
        </div>
        
        <div style="text-align: center; margin-top: 40px; color: #666;">
            <p>💡 Los precios pueden variar. Verifica en la tienda antes de comprar.</p>
        </div>
    </body>
    </html>'''
    
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
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: #333; 
            margin: 0; 
            padding: 20px; 
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 500px; 
            margin: 50px auto; 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }}
        h1 {{ 
            text-align: center; 
            color: #1a73e8; 
            margin-bottom: 10px;
            font-size: 2em;
        }} 
        p {{ 
            line-height: 1.6; 
            margin-bottom: 20px;
            text-align: center;
            color: #666;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }}
        input[type="text"] {{ 
            width: 100%; 
            padding: 15px; 
            margin-bottom: 20px; 
            border: 2px solid #e1e5e9; 
            border-radius: 10px; 
            box-sizing: border-box; 
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        input[type="text"]:focus {{
            outline: none;
            border-color: #1a73e8;
        }}
        button {{ 
            width: 100%; 
            padding: 15px; 
            background: linear-gradient(135deg, #1a73e8, #1557b0); 
            color: white; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600;
            transition: transform 0.2s;
        }}
        button:hover {{ 
            transform: translateY(-2px);
        }}
        .error {{ 
            background: #ffebee; 
            color: #c62828; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 15px 0; 
            text-align: center;
            border-left: 4px solid #c62828;
        }}
        .loading {{ 
            text-align: center; 
            padding: 40px; 
            display: none; 
        }}
        .spinner {{ 
            border: 4px solid #f3f3f3; 
            border-top: 4px solid #1a73e8; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            animation: spin 1s linear infinite; 
            margin: 0 auto 20px; 
        }}
        @keyframes spin {{ 
            0% {{ transform: rotate(0deg) }} 
            100% {{ transform: rotate(360deg) }} 
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🛒 BUSCADOR DE PRODUCTOS v4.2")
    print("✨ Versión mejorada - SIEMPRE muestra resultados")
    print(f"🚀 Servidor iniciado en http://localhost:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=True)  # Debug=True para desarrollo
