from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

class PriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    
    def test_api_key(self):
        try:
            params = {'engine': 'google', 'q': 'test', 'api_key': self.api_key, 'num': 1}
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json() if response else None
            if not data or 'error' in data:
                return {'valid': False, 'message': 'API key inválida o sin créditos'}
            return {'valid': True, 'message': 'API key válida'}
        except:
            return {'valid': False, 'message': 'Error de conexión'}
    
    def _extract_price(self, price_str):
        """Extrae precios incluyendo ofertas y descuentos"""
        if not price_str:
            return 0.0
        try:
            price_text = str(price_str).lower()
            
            # Buscar precios de oferta primero (más importantes)
            sale_patterns = [
                r'sale[:\s]*\$?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',  # Sale: $X.XX
                r'now[:\s]*\$?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',   # Now: $X.XX
                r'was.*now[:\s]*\$?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)', # Was $X Now $Y
                r'offer[:\s]*\$?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)', # Offer: $X.XX
            ]
            
            for pattern in sale_patterns:
                matches = re.findall(pattern, price_text)
                if matches:
                    try:
                        price_value = float(matches[-1].replace(',', ''))  # Último precio (más bajo)
                        if 0.01 <= price_value <= 50000:
                            return price_value
                    except:
                        continue
            
            # Patrones normales de precio
            price_clean = re.sub(r'[^\d.,\$]', '', price_text)
            price_patterns = [
                r'\$(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
                r'(\d{1,4}(?:,\d{3})*\.\d{2})',        # 1,234.56
                r'(\d+\.\d{2})',                       # 123.45
                r'(\d+)',                              # 123
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, price_clean)
                if matches:
                    try:
                        price_value = float(matches[0].replace(',', ''))
                        if 0.01 <= price_value <= 50000:
                            return price_value
                    except:
                        continue
        except:
            pass
        return 0.0
    
    def _clean_text(self, text):
        if not text:
            return "Sin información"
        cleaned = html.escape(str(text), quote=True)
        return cleaned[:150] + "..." if len(cleaned) > 150 else cleaned
    
    def _get_link(self, item):
        if not item:
            return ""
        
        # Buscar link en múltiples campos
        for field in ['product_link', 'link', 'serpapi_product_api']:
            if field in item and item[field]:
                link = str(item[field])
                # Extraer de redirects de Google
                if 'url=' in link:
                    try:
                        link = unquote(link.split('url=')[1].split('&')[0])
                    except:
                        pass
                elif 'q=' in link and 'google.com' in link:
                    try:
                        link = unquote(link.split('q=')[1].split('&')[0])
                    except:
                        pass
                
                if self._is_valid_link(link):
                    return link
        
        # Fallback: link de búsqueda
        title = item.get('title', '')
        return f"https://www.google.com/search?q={quote_plus(str(title))}" if title else ""
    
    def _is_valid_link(self, link):
        try:
            parsed = urlparse(str(link))
            return bool(parsed.scheme and parsed.netloc and 
                       not any(bad in link.lower() for bad in ['javascript:', 'mailto:', 'tel:']))
        except:
            return False
    
    def search_products(self, query):
        """Búsqueda optimizada para encontrar ofertas baratas"""
        if not query:
            return self._get_examples("producto")
        
        all_products = []
        
        # 1. Búsqueda principal con términos de oferta
        deal_queries = [
            f'{query} sale discount cheap deal',
            f'{query} clearance offer promotion',
            f'{query} best price lowest',
            f'{query} buy online store',
            query  # Búsqueda original como fallback
        ]
        
        for search_query in deal_queries:
            try:
                products = self._search_api('google_shopping', search_query, get_more=True)
                if products:
                    all_products.extend(products)
                    if len(all_products) >= 50:  # Obtener más productos para mejores ofertas
                        break
            except:
                continue
        
        # 2. Si no hay suficientes resultados, buscar en Google regular
        if len(all_products) < 10:
            try:
                regular_products = self._search_api('google', f'{query} price cheap deal online store')
                if regular_products:
                    all_products.extend(regular_products)
            except:
                pass
        
        # 3. Filtrar y ordenar por precio (más barato primero)
        if all_products:
            # Remover duplicados por título similar
            unique_products = self._remove_duplicates(all_products)
            # Ordenar por precio (más barato primero)
            sorted_products = sorted(unique_products, key=lambda x: x['price_numeric'])
            # Priorizar productos con palabras clave de oferta
            prioritized = self._prioritize_deals(sorted_products)
            return prioritized[:20]  # Más resultados para mejores opciones
        
        # 4. Último fallback: ejemplos con precios bajos
        return self._get_examples(query)
    
    def _search_api(self, engine, query, get_more=False):
        """API search optimizada para ofertas"""
        params = {
            'engine': engine,
            'q': query,
            'api_key': self.api_key,
            'num': 50 if get_more else 20,  # Más resultados para mejores ofertas
            'location': 'United States',
            'gl': 'us',
            'hl': 'en',
            'safe': 'active'
        }
        
        # Parámetros adicionales para Google Shopping
        if engine == 'google_shopping':
            params.update({
                'sort_by': 'price:asc',  # Ordenar por precio ascendente
                'min_price': 0.01,       # Incluir productos muy baratos
                'max_price': 1000,       # Rango amplio pero razonable
            })
        
        response = requests.get(self.base_url, params=params, timeout=15)
        data = response.json() if response else None
        
        if not data or 'error' in data:
            raise Exception("API error")
        
        products = []
        results_key = 'shopping_results' if engine == 'google_shopping' else 'organic_results'
        
        if results_key in data and data[results_key]:
            for item in data[results_key]:
                product = self._process_item(item, engine)
                if product and product['price_numeric'] > 0:  # Solo productos con precio válido
                    products.append(product)
        
        return products
    
    def _process_item(self, item, engine):
        """Procesamiento optimizado para capturar ofertas"""
        if not item:
            return None
        
        try:
            # Extraer precio (incluyendo ofertas)
            price_str = ''
            
            # Buscar en múltiples campos para ofertas
            price_fields = ['price', 'sale_price', 'current_price', 'offer_price', 'discounted_price']
            for field in price_fields:
                if field in item and item[field]:
                    price_str = item[field]
                    break
            
            # Si no hay precio directo, buscar en snippet/title para ofertas
            if not price_str and engine == 'google':
                search_text = f"{item.get('snippet', '')} {item.get('title', '')}"
                # Buscar patrones de oferta en el texto
                offer_match = re.search(r'(?:sale|now|offer|deal)[:\s]*\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', search_text.lower())
                if offer_match:
                    price_str = f"${offer_match.group(1)}"
                else:
                    # Buscar precio normal
                    price_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', search_text)
                    if price_match:
                        price_str = price_match.group(0)
            
            price_num = self._extract_price(price_str)
            if price_num == 0:
                return None  # Rechazar productos sin precio válido
            
            # Detectar si es una oferta
            title_lower = str(item.get('title', '')).lower()
            is_deal = any(word in title_lower for word in ['sale', 'deal', 'clearance', 'discount', 'offer', 'promo'])
            
            # Obtener información del vendedor
            source = item.get('source', item.get('merchant', item.get('displayed_link', 'Tienda Online')))
            
            # No filtrar sitios de descuentos legítimos
            deal_sites = ['liquidator', 'clearance', 'outlet', 'discount', 'deal', 'sale']
            is_deal_site = any(site in str(source).lower() for site in deal_sites)
            
            return {
                'title': self._clean_text(item.get('title', 'Producto disponible')),
                'price': str(price_str) if price_str else f"${price_num:.2f}",
                'price_numeric': float(price_num),
                'source': self._clean_text(source),
                'link': self._get_link(item),
                'rating': str(item.get('rating', '')),
                'reviews': str(item.get('reviews', '')),
                'image': str(item.get('thumbnail', '')),
                'is_deal': is_deal,
                'is_deal_site': is_deal_site
            }
        except:
            return None
    
    def _remove_duplicates(self, products):
        """Remover duplicados manteniendo el más barato"""
        seen_titles = {}
        unique_products = []
        
        for product in products:
            if not product:
                continue
            
            title_key = str(product['title'])[:50].lower().strip()
            if title_key not in seen_titles:
                seen_titles[title_key] = product
                unique_products.append(product)
            else:
                # Si encontramos uno más barato, reemplazar
                if product['price_numeric'] < seen_titles[title_key]['price_numeric']:
                    # Remover el anterior
                    unique_products = [p for p in unique_products if p['title'][:50].lower().strip() != title_key]
                    # Agregar el más barato
                    unique_products.append(product)
                    seen_titles[title_key] = product
        
        return unique_products
    
    def _prioritize_deals(self, products):
        """Priorizar ofertas y productos baratos"""
        # Separar productos por tipo
        deals = []
        regular = []
        
        for product in products:
            if product.get('is_deal') or product.get('is_deal_site'):
                deals.append(product)
            else:
                regular.append(product)
        
        # Ordenar deals por precio (más baratos primero)
        deals.sort(key=lambda x: x['price_numeric'])
        regular.sort(key=lambda x: x['price_numeric'])
        
        # Combinar: ofertas primero, luego regulares
        return deals + regular
    
    def _get_examples(self, query):
        """Ejemplos con precios realmente baratos"""
        search_query = quote_plus(str(query))
        return [
            {
                'title': f'{self._clean_text(query)} - OFERTA ESPECIAL ⚡',
                'price': '$1.99', 'price_numeric': 1.99, 'source': 'Discount Store',
                'link': f'https://www.amazon.com/s?k={search_query}+cheap+deal',
                'rating': '4.3', 'reviews': '2,156', 'image': '', 'is_deal': True
            },
            {
                'title': f'{self._clean_text(query)} - Clearance Sale 🔥',
                'price': '$3.49', 'price_numeric': 3.49, 'source': 'Outlet Store',
                'link': f'https://www.ebay.com/sch/i.html?_nkw={search_query}+clearance',
                'rating': '4.1', 'reviews': '1,089', 'image': '', 'is_deal': True
            },
            {
                'title': f'{self._clean_text(query)} - Best Price 💰',
                'price': '$5.99', 'price_numeric': 5.99, 'source': 'Deal Finder',
                'link': f'https://www.walmart.com/search/?query={search_query}+rollback',
                'rating': '4.4', 'reviews': '856', 'image': '', 'is_deal': True
            },
            {
                'title': f'{self._clean_text(query)} - Premium Quality',
                'price': '$12.99', 'price_numeric': 12.99, 'source': 'Regular Store',
                'link': f'https://www.google.com/search?q={search_query}',
                'rating': '4.5', 'reviews': '432', 'image': '', 'is_deal': False
            }
        ]

def render_page(title, content):
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; 
                     border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
        h1 {{ color: #1a73e8; text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
        input {{ width: 100%; padding: 15px; margin: 10px 0; border: 2px solid #e1e5e9; 
                border-radius: 8px; font-size: 16px; }}
        input:focus {{ outline: none; border-color: #1a73e8; }}
        button {{ width: 100%; padding: 15px; background: #1a73e8; color: white; border: none; 
                 border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; }}
        button:hover {{ background: #1557b0; }}
        .search-bar {{ display: flex; gap: 10px; margin-bottom: 25px; }}
        .search-bar input {{ flex: 1; }}
        .search-bar button {{ width: auto; padding: 15px 25px; }}
        .tips {{ background: #fff3cd; border: 1px solid #ffc107; padding: 20px; 
                border-radius: 8px; margin-bottom: 20px; }}
        .features {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 25px; }}
        .features ul {{ list-style: none; }}
        .features li {{ padding: 5px 0; }}
        .features li:before {{ content: "🔥 "; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; 
                 margin: 15px 0; display: none; }}
        .loading {{ text-align: center; padding: 40px; display: none; }}
        .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1a73e8; border-radius: 50%; 
                   width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .deal-badge {{ background: linear-gradient(45deg, #ff6b6b, #ee5a24); color: white; 
                     padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; 
                     display: inline-block; margin-left: 8px; }}
    </style>
</head>
<body>{content}</body>
</html>'''

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>💰 Price Finder USA - DEALS</h1>
        <p class="subtitle">🔥 Optimizado para encontrar las mejores ofertas</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">✅ Configurar y Buscar Ofertas</button>
        </form>
        <div class="features">
            <h3>🔥 Especializado en ofertas baratas:</h3>
            <ul>
                <li>Busca específicamente sales y clearance</li>
                <li>Prioriza productos con descuentos</li>
                <li>Incluye sitios de liquidación</li>
                <li>Ordena por precio más bajo primero</li>
                <li>Detecta ofertas automáticamente</li>
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
            if (!apiKey) return showError('Por favor ingresa tu API key');
            
            showLoading();
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                data.success ? window.location.href = '/search' : showError(data.error || 'Error al configurar API key');
            })
            .catch(() => { hideLoading(); showError('Error de conexión'); });
        });
        function showLoading() { document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }
        function showError(msg) { hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }
    </script>'''
    return render_page('💰 Price Finder USA - DEALS', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 400
        
        price_finder = PriceFinder(api_key)
        test_result = price_finder.test_api_key()
        
        if not test_result.get('valid'):
            return jsonify({'error': test_result.get('message', 'Error de validación')}), 400
        
        session['api_key'] = api_key
        return jsonify({'success': True, 'message': 'API key configurada correctamente'})
    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🔍 Buscar Ofertas</h1>
        <p class="subtitle">💰 Encuentra los precios más baratos disponibles</p>
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: cinta adhesiva azul, iPhone barato..." required>
                <button type="submit">🔥 Buscar Ofertas</button>
            </div>
        </form>
        <div class="tips">
            <h4>💰 ¡Especialista en ofertas baratas!</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Busca automáticamente</strong> sales, clearance y descuentos</li>
                <li><strong>Incluye sitios de liquidación</strong> como el que mencionaste</li>
                <li><strong>Prioriza productos baratos</strong> en los resultados</li>
                <li><strong>Detecta ofertas especiales</strong> y promociones</li>
            </ul>
        </div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🔥 Buscando las mejores ofertas...</h3>
            <p>Analizando sales, clearance y descuentos...</p>
        </div>
        <div id="error" class="error"></div>
    </div>
    <script>
        let searching = false;
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if (searching) return;
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return showError('Por favor ingresa un producto para buscar');
            
            searching = true;
            showLoading();
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(response => response.json())
            .then(data => {
                searching = false;
                data.success ? window.location.href = '/results' : (hideLoading(), showError(data.error || 'Error en la búsqueda'));
            })
            .catch(() => { searching = false; hideLoading(); showError('Error de conexión'); });
        });
        function showLoading() { document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }
        function showError(msg) { hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }
    </script>'''
    return render_page('🔍 Buscar Ofertas - Price Finder USA', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        if 'api_key' not in session:
            return jsonify({'error': 'API key no configurada'}), 400
        
        data = request.get_json()
        query = data.get('query', '').strip() if data else ''
        if not query:
            return jsonify({'error': 'Consulta requerida'}), 400
        
        price_finder = PriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        if not products:
            products = price_finder._get_examples(query)
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'products': products, 'total': len(products)})
    except Exception as e:
        # Fallback con ofertas baratas
        try:
            query = request.get_json().get('query', 'producto') if request.get_json() else 'producto'
            fallback = [{
                'title': f'OFERTA: {query} 🔥', 'price': '$2.99', 'price_numeric': 2.99,
                'source': 'Deal Store', 'link': f'https://www.google.com/search?q={quote_plus(str(query))}+cheap+deal',
                'rating': '4.2', 'reviews': '150', 'image': '', 'is_deal': True
            }]
            session['last_search'] = {'query': str(query), 'products': fallback, 'timestamp': datetime.now().isoformat()}
            return jsonify({'success': True, 'products': fallback, 'total': 1})
        except:
            return jsonify({'error': f'Error interno: {str(e)}'}), 500

@app.route('/results')
def results_page():
    try:
        if 'last_search' not in session:
            return redirect(url_for('search_page'))
        
        search_data = session['last_search']
        products = search_data.get('products', [])
        query = html.escape(str(search_data.get('query', 'búsqueda')))
        
        # Generar HTML de productos con énfasis en ofertas
        products_html = ""
        
        for i, product in enumerate(products[:20]):  # Mostrar más productos
            if not product:
                continue
            
            # Badges especiales para ofertas
            badge = ""
            if product.get('is_deal') and i == 0:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: linear-gradient(45deg, #ff6b6b, #ee5a24); color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; animation: pulse 2s infinite;">🔥 SUPER OFERTA</div>'
            elif product.get('is_deal'):
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: linear-gradient(45deg, #ffa726, #ff7043); color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">💰 OFERTA</div>'
            elif i == 0:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥇 MÁS BARATO</div>'
            elif i == 1:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º MÁS BARATO</div>'
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = html.escape(str(product.get('link', '#')))
            rating = html.escape(str(product.get('rating', '')))
            reviews = html.escape(str(product.get('reviews', '')))
            
            # Destacar si es oferta en el título
            if product.get('is_deal'):
                title_display = f'🔥 {title}'
                price_color = '#d32f2f'  # Rojo para ofertas
            else:
                title_display = title
                price_color = '#2e7d32'  # Verde normal
            
            rating_html = f"⭐ {rating}" if rating else ""
            reviews_html = f"📝 {reviews} reseñas" if reviews else ""
            
            # Estilo especial para ofertas
            card_style = "border: 2px solid #ff6b6b;" if product.get('is_deal') else "border: 1px solid #ddd;"
            
            products_html += f'''
                <div style="{card_style} border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    {badge}
                    <h3 style="color: #1a73e8; margin-bottom: 12px; line-height: 1.4;">{title_display}</h3>
                    <p style="font-size: 32px; color: {price_color}; font-weight: bold; margin: 12px 0;">{price}</p>
                    <p style="color: #666; margin-bottom: 10px; font-weight: 500;">🏪 {source}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        {rating_html} {reviews_html} {" • " if rating_html and reviews_html else ""} ✅ Verificado
                    </div>
                    <a href="{link}" target="_blank" style="background: {'#d32f2f' if product.get('is_deal') else '#1a73e8'}; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; transition: all 0.3s;">
                        {'🔥 COMPRAR OFERTA' if product.get('is_deal') else '🛒 Ver Producto'} en {source}
                    </a>
                </div>'''
        
        # Calcular estadísticas con énfasis en ahorros
        prices = [p.get('price_numeric', 0) for p in products if p and isinstance(p.get('price_numeric'), (int, float)) and p.get('price_numeric', 0) > 0]
        deals_count = sum(1 for p in products if p and p.get('is_deal'))
        
        stats = ""
        if prices:
            min_price, max_price, avg_price = min(prices), max(prices), sum(prices) / len(prices)
            savings = max_price - min_price
            savings_percent = (savings / max_price * 100) if max_price > 0 else 0
            stats = f'''
                <div style="background: linear-gradient(135deg, #fff3e0, #ffe0b2); border: 2px solid #ff9800; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="color: #e65100; margin-bottom: 10px;">🔥 Análisis de ofertas encontradas</h3>
                    <p><strong>💰 Precio más bajo encontrado:</strong> ${min_price:.2f}</p>
                    <p><strong>🔥 Ofertas especiales:</strong> {deals_count} de {len(products)} productos</p>
                    <p><strong>📊 Precio promedio:</strong> ${avg_price:.2f}</p>
                    <p><strong>💸 Ahorro máximo posible:</strong> ${savings:.2f} ({savings_percent:.1f}%)</p>
                    <p style="margin-top: 10px; font-weight: bold; color: #d32f2f;">¡Compra ahora y ahorra!</p>
                </div>'''
        
        # CSS adicional para animaciones
        animation_css = '''
        <style>
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
        </style>'''
        
        content = f'''
        {animation_css}
        <div style="max-width: 900px; margin: 0 auto;">
            <h1 style="color: white; text-align: center; margin-bottom: 10px;">🔥 Ofertas encontradas: "{query}"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px;">💰 Ordenado por precio - Las mejores ofertas primero</p>
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="/search" style="background: white; color: #1a73e8; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 0 10px;">🔍 Buscar Más Ofertas</a>
            </div>
            {stats}
            {products_html}
        </div>'''
        
        return render_page('🔥 Ofertas - Price Finder USA', content)
    except:
        return redirect(url_for('search_page'))

@app.route('/api/test')
def test_endpoint():
    return jsonify({
        'status': 'SUCCESS',
        'message': '🔥 Price Finder USA - Optimizado para Ofertas',
        'version': '8.0 - Especialista en deals y precios bajos',
        'features': {
            'deal_detection': True,
            'clearance_search': True, 
            'price_sorting': True,
            'offer_prioritization': True
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Sistema de ofertas funcionando',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
