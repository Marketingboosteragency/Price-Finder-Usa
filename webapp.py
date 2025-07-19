from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

class PriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    
    def test_api_key(self):
        params = {'engine': 'google', 'q': 'test', 'api_key': self.api_key, 'num': 1}
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            if 'error' in data:
                return {'valid': False, 'message': 'API key inválida o sin créditos'}
            return {'valid': True, 'message': 'API key válida'}
        except Exception as e:
            return {'valid': False, 'message': f'Error de conexión: {str(e)}'}
    
    def _extract_price(self, price_str):
        """Extrae precio numérico de manera robusta"""
        if not price_str:
            return 0.0
        
        # Convertir a string y limpiar
        price_str = str(price_str).strip()
        
        # Buscar patrones de precio
        price_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d{1,3}(?:,\d{3})*\.\d{2})',            # 1,234.56
            r'(\d+\.\d{2})',                           # 123.45
            r'(\d+)',                                  # 123
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, price_str)
            if matches:
                price_clean = matches[0].replace(',', '')
                try:
                    price_value = float(price_clean)
                    if 0.1 <= price_value <= 10000:  # Rango razonable
                        return price_value
                except ValueError:
                    continue
        
        return 0.0
    
    def _clean_text(self, text):
        """Limpia texto para prevenir problemas de HTML"""
        if not text:
            return "Sin información"
        
        # Escapar HTML y truncar
        cleaned = html.escape(str(text))
        return cleaned[:100] + "..." if len(cleaned) > 100 else cleaned
    
    def search_products(self, query):
        params = {
            'engine': 'google_shopping',
            'q': query,
            'api_key': self.api_key,
            'num': 20,
            'location': 'United States'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                error_msg = data['error']
                if 'credits' in error_msg.lower() or 'quota' in error_msg.lower():
                    raise Exception("Se agotaron los créditos de tu API key")
                raise Exception(f"Error de API: {error_msg}")
            
            products = []
            if 'shopping_results' in data:
                for item in data['shopping_results']:
                    try:
                        price_str = item.get('price', '0')
                        price_num = self._extract_price(price_str)
                        
                        if price_num > 0:
                            # Validar que sea de tienda de EE.UU. (básico)
                            source = item.get('source', 'Desconocido')
                            link = item.get('link', '')
                            
                            # Filtrar dominios chinos básicos
                            if any(domain in link.lower() for domain in ['alibaba', 'aliexpress', 'temu', 'wish']):
                                continue
                            
                            products.append({
                                'title': self._clean_text(item.get('title', 'Sin título')),
                                'price': price_str,
                                'price_numeric': price_num,
                                'source': self._clean_text(source),
                                'link': link,
                                'rating': item.get('rating', ''),
                                'reviews': item.get('reviews', '')
                            })
                    except Exception as e:
                        # Log error pero continúa con otros productos
                        print(f"Error procesando producto: {e}")
                        continue
            
            # Ordenar por precio y remover duplicados básicos
            products = sorted(products, key=lambda x: x['price_numeric'])
            
            # Filtrar duplicados por título similar
            unique_products = []
            seen_titles = set()
            for product in products:
                title_key = product['title'][:30].lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_products.append(product)
            
            return unique_products[:15]  # Máximo 15 productos
        
        except requests.RequestException as e:
            raise Exception(f"Error de conexión con SerpAPI: {str(e)}")
        except Exception as e:
            raise e

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="es">
<head>
    <title>🇺🇸 Price Finder USA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            padding: 20px;
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        input { 
            width: 100%; 
            padding: 15px; 
            margin: 10px 0; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: #1a73e8; }
        button { 
            width: 100%; 
            padding: 15px; 
            background: #1a73e8; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600;
            transition: background 0.3s;
        }
        button:hover { background: #1557b0; }
        .features { 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 8px; 
            margin-top: 25px; 
        }
        .features ul { list-style: none; }
        .features li { padding: 5px 0; }
        .features li:before { content: "✅ "; }
        .error { 
            background: #ffebee; 
            color: #c62828; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0; 
            display: none;
        }
        .loading { 
            text-align: center; 
            padding: 20px; 
            display: none;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #1a73e8;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🇺🇸 Price Finder USA</h1>
        <p class="subtitle">Encuentra los mejores precios en tiendas verificadas de EE.UU.</p>
        
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">✅ Configurar y Continuar</button>
        </form>
        
        <div class="features">
            <h3>🛡️ Características principales:</h3>
            <ul>
                <li>Solo vendedores verificados de EE.UU.</li>
                <li>Filtra automáticamente sitios chinos</li>
                <li>Precios ordenados de menor a mayor</li>
                <li>Links directos de compra verificados</li>
                <li>Búsquedas rápidas y precisas</li>
            </ul>
            <p style="margin-top: 15px;">
                <strong>¿No tienes API key?</strong> 
                <a href="https://serpapi.com/" target="_blank" style="color: #1a73e8;">
                    Obtén una gratis aquí (100 búsquedas/mes)
                </a>
            </p>
        </div>
        
        <div id="error" class="error"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando API key...</p>
        </div>
    </div>

    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) {
                showError('Por favor ingresa tu API key');
                return;
            }
            
            showLoading();
            
            const formData = new FormData();
            formData.append('api_key', apiKey);
            
            fetch('/setup', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    showError(data.error || 'Error al configurar API key');
                }
            })
            .catch(error => {
                hideLoading();
                showError('Error de conexión. Verifica tu internet.');
            });
        });

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        function showError(message) {
            hideLoading();
            document.getElementById('error').textContent = message;
            document.getElementById('error').style.display = 'block';
        }
    </script>
</body>
</html>
'''

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'error': 'API key requerida'}), 400
    
    try:
        price_finder = PriceFinder(api_key)
        test_result = price_finder.test_api_key()
        
        if not test_result['valid']:
            return jsonify({'error': test_result['message']}), 400
        
        session['api_key'] = api_key
        return jsonify({'success': True, 'message': 'API key configurada correctamente'})
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar API key: {str(e)}'}), 400

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    return '''
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Búsqueda - Price Finder USA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            padding: 20px;
        }
        .container { 
            max-width: 700px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .search-bar { display: flex; gap: 10px; margin-bottom: 25px; }
        input { 
            flex: 1; 
            padding: 15px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 16px;
        }
        input:focus { outline: none; border-color: #1a73e8; }
        button { 
            padding: 15px 25px; 
            background: #1a73e8; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600;
        }
        button:hover { background: #1557b0; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #545b62; }
        .tips { 
            background: #fff3cd; 
            border: 1px solid #ffeaa7; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
        }
        .loading { 
            text-align: center; 
            padding: 40px; 
            display: none; 
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1a73e8;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error { 
            background: #ffebee; 
            color: #c62828; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0; 
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Buscar Productos</h1>
        <p class="subtitle">Búsqueda inteligente en tiendas verificadas de EE.UU.</p>
        
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: iPhone 15 azul, Samsung TV 55 pulgadas..." required>
                <button type="submit">🎯 Buscar</button>
            </div>
        </form>
        
        <div class="tips">
            <h4>💡 Tips para mejores resultados:</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Sé específico:</strong> "iPhone 15 Pro azul 128GB"</li>
                <li><strong>Incluye marca:</strong> "Samsung Galaxy S24"</li>
                <li><strong>Menciona tamaño:</strong> "TV 55 pulgadas"</li>
                <li><strong>Agrega color:</strong> "Nike Air Max negro"</li>
            </ul>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🔍 Buscando mejores precios...</h3>
            <p>Analizando productos en tiendas de EE.UU...</p>
            <button type="button" class="btn-secondary" style="margin-top: 20px;" onclick="cancelSearch()">
                ❌ Cancelar
            </button>
        </div>
        
        <div id="error" class="error"></div>
    </div>

    <script>
        let searchInProgress = false;

        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (searchInProgress) return;
            
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) {
                showError('Por favor ingresa un producto para buscar');
                return;
            }
            
            startSearch(query);
        });

        function startSearch(query) {
            searchInProgress = true;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            
            fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                searchInProgress = false;
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    hideLoading();
                    showError(data.error || 'Error en la búsqueda');
                }
            })
            .catch(error => {
                searchInProgress = false;
                hideLoading();
                showError('Error de conexión. Verifica tu internet.');
            });
        }

        function cancelSearch() {
            searchInProgress = false;
            hideLoading();
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        function showError(message) {
            hideLoading();
            document.getElementById('error').textContent = message;
            document.getElementById('error').style.display = 'block';
        }
    </script>
</body>
</html>
'''

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'error': 'API key no configurada'}), 400
    
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    try:
        price_finder = PriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'products': products,
            'total': len(products)
        })
        
    except Exception as e:
        error_message = str(e)
        return jsonify({'error': error_message}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    products = search_data['products']
    query = html.escape(search_data['query'])  # Escapar query para HTML
    
    products_html = ""
    if products:
        for i, product in enumerate(products):
            # Los datos ya están escapados por _clean_text()
            badge = ""
            if i == 0:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">💰 MEJOR PRECIO</div>'
            elif i == 1:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º MEJOR</div>'
            
            rating_html = ""
            if product.get('rating'):
                rating_html = f"⭐ {product['rating']}"
            
            reviews_html = ""
            if product.get('reviews'):
                reviews_html = f"📝 {product['reviews']} reseñas"
            
            products_html += f'''
                <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; transition: box-shadow 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    {badge}
                    <h3 style="color: #1a73e8; margin-bottom: 12px; line-height: 1.4;">{product['title']}</h3>
                    <p style="font-size: 28px; color: #2e7d32; font-weight: bold; margin: 12px 0;">{product['price']}</p>
                    <p style="color: #666; margin-bottom: 10px; font-weight: 500;">🏪 {product['source']}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        {rating_html} {reviews_html}
                        {" • " if rating_html and reviews_html else ""}
                        🇺🇸 Vendedor EE.UU.
                    </div>
                    <a href="{product['link']}" target="_blank" style="background: #1a73e8; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; transition: background 0.3s;">
                        🛒 Ver en {product['source']}
                    </a>
                </div>
            '''
    else:
        products_html = '''
            <div style="text-align: center; padding: 60px 20px; background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h3 style="color: #666; margin-bottom: 15px;">😔 No se encontraron productos</h3>
                <p style="color: #888; margin-bottom: 25px;">
                    No encontramos productos que coincidan con tu búsqueda en tiendas de EE.UU.<br>
                    Intenta con términos más específicos o diferentes.
                </p>
                <a href="/search" style="background: #1a73e8; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                    🔍 Nueva Búsqueda
                </a>
            </div>
        '''
    
    # Calcular estadísticas de precios
    price_stats = ""
    if products:
        min_price = min(p['price_numeric'] for p in products)
        max_price = max(p['price_numeric'] for p in products)
        price_stats = f'''
            <div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h3 style="color: #2e7d32; margin-bottom: 10px;">📊 Resumen de búsqueda</h3>
                <p><strong>{len(products)} productos encontrados</strong> de vendedores verificados de EE.UU.</p>
                <p><strong>Rango de precios:</strong> ${min_price:.2f} - ${max_price:.2f}</p>
                <p><strong>Ahorro potencial:</strong> ${max_price - min_price:.2f} ({((max_price - min_price) / max_price * 100):.1f}%)</p>
            </div>
        '''
    
    return f'''
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Resultados - Price Finder USA</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ color: white; text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px; }}
        .actions {{ 
            text-align: center; 
            margin-bottom: 25px; 
        }}
        .btn {{ 
            background: white; 
            color: #1a73e8; 
            padding: 12px 20px; 
            text-decoration: none; 
            border-radius: 8px; 
            font-weight: 600; 
            margin: 0 10px;
            display: inline-block;
            transition: all 0.3s;
        }}
        .btn:hover {{ 
            background: #f0f0f0; 
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 0 10px; }}
            .btn {{ margin: 5px; display: block; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 Resultados para: "{query}"</h1>
        <p class="subtitle">Productos verificados de vendedores de EE.UU. ordenados por precio</p>
        
        <div class="actions">
            <a href="/search" class="btn">🔍 Nueva Búsqueda</a>
            <a href="javascript:window.print()" class="btn">📄 Imprimir Resultados</a>
        </div>
        
        {price_stats}
        {products_html}
    </div>
</body>
</html>
'''

@app.route('/api/test')
def test_endpoint():
    return jsonify({
        'status': 'SUCCESS',
        'message': '🇺🇸 Price Finder USA funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'version': '3.1 - Errores corregidos'
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Aplicación funcionando',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
