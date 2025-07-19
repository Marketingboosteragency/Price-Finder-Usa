from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
import json
import time

# Importaciones mejoradas
try:
    from bs4 import BeautifulSoup
    import cloudscraper
    from fake_useragent import UserAgent
    from price_parser import Price
    HAS_ENHANCED = True
    print("✅ Librerías mejoradas cargadas")
except ImportError:
    HAS_ENHANCED = False
    print("⚠️ Modo básico")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

class SmartPriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.scraperapi_key = os.environ.get('SCRAPERAPI_KEY', '')
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY', '')
        
        if HAS_ENHANCED:
            self.scraper = cloudscraper.create_scraper()
            self.ua = UserAgent()
        
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
    
    def search_products(self, query):
        """Búsqueda INTELIGENTE que encuentra productos específicos"""
        if not query:
            return []
        
        print(f"🔍 BÚSQUEDA INTELIGENTE para: '{query}'")
        
        all_products = []
        original_query = query.strip()
        
        # 1. Búsqueda principal con términos exactos
        try:
            print("📡 Búsqueda principal...")
            main_products = self._search_with_exact_terms(original_query)
            all_products.extend(main_products)
            print(f"✅ Búsqueda principal: {len(main_products)} productos")
        except Exception as e:
            print(f"❌ Error búsqueda principal: {e}")
        
        # 2. Búsqueda expandida con variaciones
        if len(all_products) < 10:
            try:
                print("🔄 Búsqueda expandida...")
                expanded_products = self._search_with_variations(original_query)
                all_products.extend(expanded_products)
                print(f"✅ Búsqueda expandida: {len(expanded_products)} productos")
            except Exception as e:
                print(f"❌ Error búsqueda expandida: {e}")
        
        # 3. Búsqueda de ofertas específicas
        if len(all_products) < 15:
            try:
                print("💰 Búsqueda de ofertas...")
                deal_products = self._search_deals_specific(original_query)
                all_products.extend(deal_products)
                print(f"✅ Ofertas específicas: {len(deal_products)} productos")
            except Exception as e:
                print(f"❌ Error búsqueda ofertas: {e}")
        
        print(f"📊 Total productos encontrados: {len(all_products)}")
        
        if all_products:
            # Filtrar por relevancia con la búsqueda original
            relevant_products = self._filter_by_relevance(all_products, original_query)
            print(f"🎯 Productos relevantes: {len(relevant_products)}")
            
            if relevant_products:
                unique_products = self._remove_duplicates(relevant_products)
                sorted_products = sorted(unique_products, key=lambda x: x.get('price_numeric', 999))
                final_products = sorted_products[:20]
                print(f"✅ Productos finales: {len(final_products)}")
                return final_products
        
        print("❌ No se encontraron productos específicos")
        return []
    
    def _search_with_exact_terms(self, query):
        """Búsqueda con términos exactos"""
        products = []
        
        # Consultas específicas para encontrar el producto exacto
        exact_queries = [
            f'"{query}"',  # Búsqueda exacta entre comillas
            query,         # Búsqueda normal
            f"{query} buy", # Con intención de compra
        ]
        
        for search_query in exact_queries:
            try:
                # Google Shopping
                shopping_products = self._search_google_shopping(search_query)
                products.extend(shopping_products)
                
                # Bing Shopping  
                bing_products = self._search_bing_shopping(search_query)
                products.extend(bing_products)
                
                if len(products) >= 15:
                    break
                    
            except Exception as e:
                print(f"Error en consulta exacta '{search_query}': {e}")
                continue
        
        return products
    
    def _search_with_variations(self, query):
        """Búsqueda con variaciones inteligentes del término"""
        products = []
        
        # Generar variaciones inteligentes
        variations = self._generate_smart_variations(query)
        
        for variation in variations[:3]:  # Limitar variaciones
            try:
                shopping_products = self._search_google_shopping(variation)
                products.extend(shopping_products)
                
                if len(products) >= 10:
                    break
                    
            except Exception as e:
                print(f"Error en variación '{variation}': {e}")
                continue
        
        return products
    
    def _search_deals_specific(self, query):
        """Búsqueda específica de ofertas para el producto"""
        products = []
        
        deal_queries = [
            f"{query} sale",
            f"{query} discount", 
            f"{query} cheap",
            f"{query} best price"
        ]
        
        for deal_query in deal_queries[:2]:
            try:
                shopping_products = self._search_google_shopping(deal_query)
                products.extend(shopping_products)
                
                if len(products) >= 8:
                    break
                    
            except Exception as e:
                print(f"Error en oferta '{deal_query}': {e}")
                continue
        
        return products
    
    def _generate_smart_variations(self, query):
        """Genera variaciones inteligentes del término de búsqueda"""
        variations = []
        query_lower = query.lower()
        
        # Variaciones por tipo de producto
        if 'iphone' in query_lower:
            variations.extend([
                query.replace('iphone', 'iPhone'),
                f"Apple {query}",
                f"{query} unlocked",
                f"{query} smartphone"
            ])
        elif 'samsung' in query_lower:
            variations.extend([
                f"{query} galaxy",
                f"{query} phone",
                f"{query} smartphone"
            ])
        elif 'tape' in query_lower or 'cinta' in query_lower:
            variations.extend([
                f"{query} adhesive",
                f"{query} roll",
                f"{query} pack"
            ])
        elif 'laptop' in query_lower:
            variations.extend([
                f"{query} computer",
                f"{query} notebook",
                f"{query} pc"
            ])
        else:
            # Variaciones genéricas
            variations.extend([
                f"{query} new",
                f"{query} original",
                f"{query} brand"
            ])
        
        return variations[:5]  # Limitar variaciones
    
    def _filter_by_relevance(self, products, original_query):
        """Filtra productos por relevancia con la búsqueda original"""
        relevant_products = []
        query_words = set(original_query.lower().split())
        
        for product in products:
            if not product:
                continue
            
            title = str(product.get('title', '')).lower()
            
            # Calcular relevancia
            relevance_score = self._calculate_relevance(title, query_words)
            
            # Solo incluir productos con relevancia alta
            if relevance_score >= 0.3:  # Al menos 30% de relevancia
                product['relevance_score'] = relevance_score
                relevant_products.append(product)
        
        # Ordenar por relevancia y precio
        relevant_products.sort(key=lambda x: (-x.get('relevance_score', 0), x.get('price_numeric', 999)))
        
        return relevant_products
    
    def _calculate_relevance(self, title, query_words):
        """Calcula un score de relevancia entre 0 y 1"""
        title_words = set(title.split())
        
        # Palabras que coinciden exactamente
        exact_matches = query_words.intersection(title_words)
        
        # Palabras que coinciden parcialmente
        partial_matches = 0
        for query_word in query_words:
            for title_word in title_words:
                if query_word in title_word or title_word in query_word:
                    partial_matches += 0.5
                    break
        
        # Calcular score
        total_query_words = len(query_words)
        if total_query_words == 0:
            return 0
        
        exact_score = len(exact_matches) / total_query_words
        partial_score = min(partial_matches / total_query_words, 0.5)
        
        return min(exact_score + partial_score, 1.0)
    
    def _search_google_shopping(self, query):
        """Búsqueda optimizada en Google Shopping"""
        try:
            params = {
                'engine': 'google_shopping',
                'q': query,
                'api_key': self.api_key,
                'num': 50,
                'location': 'United States',
                'gl': 'us',
                'hl': 'en',
                'sort_by': 'price:asc',
                'safe': 'active'
            }
            
            response = requests.get(self.base_url, params=params, timeout=15)
            data = response.json() if response else None
            
            if not data or 'error' in data:
                return []
            
            products = []
            if 'shopping_results' in data and data['shopping_results']:
                for item in data['shopping_results']:
                    product = self._process_shopping_item(item)
                    if product:
                        products.append(product)
            
            return products
            
        except Exception as e:
            print(f"Error Google Shopping: {e}")
            return []
    
    def _search_bing_shopping(self, query):
        """Búsqueda en Bing Shopping"""
        try:
            params = {
                'engine': 'bing_shopping',
                'q': query,
                'api_key': self.api_key,
                'count': 30,
                'location': 'United States'
            }
            
            response = requests.get(self.base_url, params=params, timeout=15)
            data = response.json() if response else None
            
            products = []
            if data and 'shopping_results' in data:
                for item in data['shopping_results']:
                    product = self._process_shopping_item(item)
                    if product:
                        products.append(product)
            
            return products
        except:
            return []
    
    def _process_shopping_item(self, item):
        """Procesa items de shopping con validación mejorada"""
        if not item:
            return None
        
        try:
            # Extraer precio
            price_str = item.get('price', '')
            if not price_str:
                for field in ['extracted_price', 'sale_price', 'current_price']:
                    if item.get(field):
                        price_str = item[field]
                        break
            
            price_num = self._extract_price(price_str)
            if price_num <= 0:
                return None
            
            # Extraer link real
            product_link = self._extract_real_product_link(item)
            if not product_link:
                return None
            
            # Validar título
            title = item.get('title', '')
            if not title or len(title.strip()) < 5:
                return None
            
            # Fuente
            source = item.get('source', item.get('merchant', ''))
            if not source:
                try:
                    parsed = urlparse(product_link)
                    source = parsed.netloc.replace('www.', '')
                except:
                    source = 'Unknown Store'
            
            return {
                'title': self._clean_text(title),
                'price': f"${price_num:.2f}",
                'price_numeric': float(price_num),
                'source': self._clean_text(source),
                'link': product_link,
                'rating': str(item.get('rating', '')),
                'reviews': str(item.get('reviews', '')),
                'image': str(item.get('thumbnail', '')),
                'is_real': True,
                'source_type': 'shopping_api'
            }
            
        except Exception as e:
            print(f"Error procesando shopping item: {e}")
            return None
    
    def _extract_real_product_link(self, item):
        """Extrae links reales de productos"""
        if not item:
            return ""
        
        for field in ['product_link', 'link', 'serpapi_product_api_link']:
            if field in item and item[field]:
                raw_link = str(item[field])
                
                # Limpiar redirects de Google
                if 'url=' in raw_link:
                    try:
                        decoded_link = unquote(raw_link.split('url=')[1].split('&')[0])
                    except:
                        decoded_link = raw_link
                elif 'q=' in raw_link and 'google.com' in raw_link:
                    try:
                        decoded_link = unquote(raw_link.split('q=')[1].split('&')[0])
                    except:
                        decoded_link = raw_link
                else:
                    decoded_link = raw_link
                
                if self._is_real_product_link(decoded_link):
                    return decoded_link
        
        return ""
    
    def _is_real_product_link(self, link):
        """Validación mejorada de links reales"""
        if not link:
            return False
        
        try:
            link_lower = str(link).lower()
            
            # Rechazar búsquedas obvias
            search_indicators = [
                '/search?', '/s?k=', '/sch/', '?q=', 'search=', 
                '/search/', 'query=', '_nkw=', 'searchterm=',
                'google.com/search', 'bing.com/search'
            ]
            
            if any(indicator in link_lower for indicator in search_indicators):
                return False
            
            # Validar patrones de productos
            product_patterns = [
                r'/dp/[A-Z0-9]+',           # Amazon
                r'/itm/\d+',                # eBay
                r'/ip/\d+',                 # Walmart
                r'/p/\d+',                  # Target/otros
                r'/product/',               # Generic
                r'/products/',              # Shopify
                r'/listing/\d+',            # Etsy
            ]
            
            has_product_pattern = any(re.search(pattern, link_lower) for pattern in product_patterns)
            
            # Dominios confiables
            trusted_domains = [
                'amazon.com', 'ebay.com', 'walmart.com', 'target.com',
                'bestbuy.com', 'homedepot.com', 'lowes.com', 'costco.com',
                'newegg.com', 'apple.com', 'samsung.com', 'dell.com'
            ]
            
            has_trusted_domain = any(domain in link_lower for domain in trusted_domains)
            
            if has_product_pattern or has_trusted_domain:
                parsed = urlparse(link)
                return bool(parsed.scheme and parsed.netloc)
            
            return False
            
        except:
            return False
    
    def _extract_price(self, price_str):
        """Extracción robusta de precios"""
        if not price_str:
            return 0.0
        
        try:
            # Usar price-parser si está disponible
            if HAS_ENHANCED:
                try:
                    parsed = Price.fromstring(str(price_str))
                    if parsed.amount:
                        return float(parsed.amount)
                except:
                    pass
            
            # Método básico
            price_text = str(price_str).lower()
            patterns = [
                r'\$(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+\.\d{2})',
                r'(\d+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, price_text)
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
        """Limpia texto de manera segura"""
        if not text:
            return "Sin información"
        cleaned = html.escape(str(text), quote=True)
        return cleaned[:150] + "..." if len(cleaned) > 150 else cleaned
    
    def _remove_duplicates(self, products):
        """Remover duplicados manteniendo el mejor precio"""
        seen_titles = {}
        unique_products = []
        
        for product in products:
            if not product:
                continue
            
            # Crear clave más específica para evitar falsos duplicados
            title_key = str(product['title'])[:60].lower().strip()
            source_key = str(product['source'])[:20].lower().strip()
            combined_key = f"{title_key}_{source_key}"
            
            if combined_key not in seen_titles:
                seen_titles[combined_key] = product
                unique_products.append(product)
            else:
                # Si encontramos uno más barato, reemplazar
                if product['price_numeric'] < seen_titles[combined_key]['price_numeric']:
                    unique_products = [p for p in unique_products 
                                     if f"{str(p['title'])[:60].lower().strip()}_{str(p['source'])[:20].lower().strip()}" != combined_key]
                    unique_products.append(product)
                    seen_titles[combined_key] = product
        
        return unique_products

# Flask app routes
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
        .tips {{ background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; 
                border-radius: 8px; margin-bottom: 20px; }}
        .features {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 25px; }}
        .features ul {{ list-style: none; }}
        .features li {{ padding: 5px 0; }}
        .features li:before {{ content: "🎯 "; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; 
                 margin: 15px 0; display: none; }}
        .loading {{ text-align: center; padding: 40px; display: none; }}
        .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1a73e8; border-radius: 50%; 
                   width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>{content}</body>
</html>'''

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🎯 Price Finder INTELIGENTE</h1>
        <p class="subtitle">✅ Encuentra productos ESPECÍFICOS y REALES</p>
        
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">🎯 Activar Búsqueda INTELIGENTE</button>
        </form>
        
        <div class="features">
            <h3>🎯 Búsqueda INTELIGENTE arreglada:</h3>
            <ul>
                <li>Encuentra productos específicos de tu búsqueda</li>
                <li>Filtra por relevancia - NO resultados genéricos</li>
                <li>Búsquedas exactas + variaciones inteligentes</li>
                <li>Precios reales de productos reales</li>
                <li>Links directos verificados</li>
                <li>Score de relevancia para cada producto</li>
            </ul>
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
    return render_page('🎯 Price Finder INTELIGENTE', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 400
        
        price_finder = SmartPriceFinder(api_key)
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
        <h1>🔍 Búsqueda ESPECÍFICA</h1>
        <p class="subtitle">🎯 Encuentra exactamente lo que buscas</p>
        
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: iPhone 15, Samsung Galaxy S24, cinta adhesiva azul..." required>
                <button type="submit">🎯 Buscar ESPECÍFICO</button>
            </div>
        </form>
        
        <div class="tips">
            <h4>🎯 Búsqueda ESPECÍFICA arreglada:</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Productos específicos:</strong> Encuentra exactamente lo que buscas</li>
                <li><strong>Filtro de relevancia:</strong> Solo productos relacionados con tu búsqueda</li>
                <li><strong>Múltiples variaciones:</strong> Búsquedas exactas + sinónimos inteligentes</li>
                <li><strong>Precios reales:</strong> De productos que realmente existen</li>
                <li><strong>Sin resultados genéricos:</strong> No más "Shop on eBay" irrelevantes</li>
            </ul>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🎯 Buscando productos específicos...</h3>
            <p>Analizando relevancia y filtrando resultados...</p>
        </div>
        
        <div id="error" class="error"></div>
    </div>
    <script>
        let searching = false;
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if (searching) return;
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return showError('Por favor ingresa un producto específico para buscar');
            
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
    return render_page('🔍 Búsqueda ESPECÍFICA', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        if 'api_key' not in session:
            return jsonify({'error': 'API key no configurada'}), 400
        
        data = request.get_json()
        query = data.get('query', '').strip() if data else ''
        if not query:
            return jsonify({'error': 'Consulta requerida'}), 400
        
        price_finder = SmartPriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        if not products:
            return jsonify({
                'success': False, 
                'error': f'No se encontraron productos específicos para "{query}". Intenta con términos más específicos como marca + modelo.',
                'suggestion': 'Ejemplos: "iPhone 15 Pro", "Samsung Galaxy S24", "Sony WH-1000XM4"'
            })
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'smart_mode': True
        }
        
        return jsonify({
            'success': True, 
            'products': products, 
            'total': len(products),
            'smart_mode': True
        })
        
    except Exception as e:
        print(f"Error en api_search: {e}")
        return jsonify({'error': f'Error de búsqueda: {str(e)}'}), 500

@app.route('/results')
def results_page():
    try:
        if 'last_search' not in session:
            return redirect(url_for('search_page'))
        
        search_data = session['last_search']
        products = search_data.get('products', [])
        query = html.escape(str(search_data.get('query', 'búsqueda')))
        
        if not products:
            no_results_content = f'''
            <div style="max-width: 900px; margin: 0 auto;">
                <h1 style="color: white; text-align: center; margin-bottom: 10px;">🎯 Sin productos específicos para: "{query}"</h1>
                <div style="background: white; padding: 40px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #666; margin-bottom: 20px;">Búsqueda INTELIGENTE activada</h3>
                    <p style="color: #888; margin-bottom: 30px;">
                        El sistema buscó productos específicos relacionados con "{query}" pero no encontró resultados relevantes.<br>
                        Intenta con términos más específicos incluyendo marca y modelo.
                    </p>
                    <a href="/search" style="background: #1a73e8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        🔍 Buscar con Términos Específicos
                    </a>
                </div>
            </div>'''
            return render_page('Sin Productos Específicos', no_results_content)
        
        # Generar HTML de productos específicos
        products_html = ""
        
        for i, product in enumerate(products):
            if not product:
                continue
            
            # Badge de relevancia
            relevance = product.get('relevance_score', 0)
            relevance_percent = int(relevance * 100)
            
            relevance_badge = ""
            if relevance >= 0.8:
                relevance_badge = f'<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🎯 {relevance_percent}% RELEVANTE</div>'
            elif relevance >= 0.5:
                relevance_badge = f'<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">📍 {relevance_percent}% RELEVANTE</div>'
            else:
                relevance_badge = f'<div style="position: absolute; top: 10px; right: 10px; background: #9e9e9e; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🔍 {relevance_percent}% RELEVANTE</div>'
            
            # Badge de precio
            price_badge = ""
            if i == 0:
                price_badge = '<div style="position: absolute; top: 40px; right: 10px; background: #e91e63; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">💰 MÁS BARATO</div>'
            elif i == 1:
                price_badge = '<div style="position: absolute; top: 40px; right: 10px; background: #9c27b0; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º LUGAR</div>'
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = product.get('link', '#')
            rating = html.escape(str(product.get('rating', '')))
            reviews = html.escape(str(product.get('reviews', '')))
            
            rating_html = f"⭐ {rating}" if rating else ""
            reviews_html = f"📝 {reviews} reseñas" if reviews else ""
            
            products_html += f'''
                <div style="border: 2px solid #1a73e8; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                    {relevance_badge}
                    {price_badge}
                    <h3 style="color: #1a73e8; margin-bottom: 12px; margin-top: 35px; line-height: 1.4;">{title}</h3>
                    <p style="font-size: 32px; color: #2e7d32; font-weight: bold; margin: 12px 0;">{price}</p>
                    <p style="color: #666; margin-bottom: 10px; font-weight: 500;">🏪 {source}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        {rating_html} {reviews_html} {" • " if rating_html and reviews_html else ""} 
                        ✅ Producto específico verificado
                    </div>
                    <a href="{link}" target="_blank" rel="noopener noreferrer" style="background: #4caf50; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; transition: all 0.3s;">
                        🛒 COMPRAR PRODUCTO ESPECÍFICO en {source}
                    </a>
                </div>'''
        
        # Estadísticas mejoradas
        prices = [p.get('price_numeric', 0) for p in products if p and p.get('price_numeric', 0) > 0]
        avg_relevance = sum(p.get('relevance_score', 0) for p in products) / len(products) if products else 0
        
        stats = ""
        if prices:
            min_price, max_price, avg_price = min(prices), max(prices), sum(prices) / len(prices)
            stats = f'''
                <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c9); border: 2px solid #4caf50; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="color: #2e7d32; margin-bottom: 10px;">🎯 Productos ESPECÍFICOS encontrados</h3>
                    <p><strong>✅ {len(products)} productos específicos para "{query}"</strong></p>
                    <p><strong>🎯 Relevancia promedio:</strong> {int(avg_relevance * 100)}% (productos específicos)</p>
                    <p><strong>💰 Precio más bajo:</strong> ${min_price:.2f}</p>
                    <p><strong>📊 Precio promedio:</strong> ${avg_price:.2f}</p>
                    <p><strong>💸 Ahorro máximo:</strong> ${max_price - min_price:.2f}</p>
                    <p><strong>🚀 Sistema:</strong> ✅ BÚSQUEDA INTELIGENTE</p>
                </div>'''
        
        content = f'''
        <div style="max-width: 900px; margin: 0 auto;">
            <h1 style="color: white; text-align: center; margin-bottom: 10px;">🎯 Productos ESPECÍFICOS: "{query}"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px;">✅ Filtrados por relevancia - Solo productos específicos</p>
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="/search" style="background: white; color: #1a73e8; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600;">🔍 Nueva Búsqueda ESPECÍFICA</a>
            </div>
            {stats}
            {products_html}
        </div>'''
        
        return render_page('🎯 Productos ESPECÍFICOS', content)
    except Exception as e:
        print(f"Error en results_page: {e}")
        return redirect(url_for('search_page'))

@app.route('/api/test')
def test_endpoint():
    return jsonify({
        'status': 'SUCCESS',
        'message': '🎯 Price Finder INTELIGENTE - Resultados Específicos',
        'version': '13.0 - Búsqueda específica con filtro de relevancia',
        'features': {
            'smart_search': True,
            'relevance_filtering': True,
            'specific_products': True,
            'intelligent_variations': True
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Sistema INTELIGENTE funcionando',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🎯 Iniciando Price Finder INTELIGENTE")
    print("✅ Características del sistema:")
    print("   🎯 Búsqueda específica con filtro de relevancia")
    print("   ✅ Encuentra productos exactos de tu búsqueda")
    print("   🔍 Variaciones inteligentes del término")
    print("   💰 Precios reales de productos reales")
    print("   🚫 NO más resultados genéricos irrelevantes")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
