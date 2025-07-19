from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
import json

# Importaciones de librerías adicionales (opcionales)
try:
    from bs4 import BeautifulSoup
    import cloudscraper
    from fake_useragent import UserAgent
    from price_parser import Price
    HAS_ENHANCED = True
    print("✅ Librerías mejoradas cargadas: BeautifulSoup, CloudScraper, Price-Parser")
except ImportError:
    HAS_ENHANCED = False
    print("⚠️ Usando modo básico. Para mejores resultados instala: pip install beautifulsoup4 cloudscraper fake-useragent price-parser lxml")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

class EnhancedPriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        
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
        """Búsqueda mejorada con múltiples fuentes"""
        if not query:
            return []
        
        all_products = []
        
        print(f"🔍 Iniciando búsqueda para: {query}")
        
        # 1. SerpAPI Google Shopping (principal)
        try:
            print("📡 Buscando en Google Shopping...")
            serpapi_products = self._search_serpapi_shopping(query)
            all_products.extend(serpapi_products)
            print(f"✅ Google Shopping: {len(serpapi_products)} productos")
        except Exception as e:
            print(f"❌ Error Google Shopping: {e}")
        
        # 2. SerpAPI Bing Shopping
        try:
            print("📡 Buscando en Bing Shopping...")
            bing_products = self._search_bing_shopping(query)
            all_products.extend(bing_products)
            print(f"✅ Bing Shopping: {len(bing_products)} productos")
        except Exception as e:
            print(f"❌ Error Bing Shopping: {e}")
        
        # 3. Scraping directo (si hay librerías mejoradas)
        if HAS_ENHANCED and len(all_products) < 15:
            try:
                print("🕷️ Scraping directo de tiendas...")
                scraped_products = self._scrape_direct_stores(query)
                all_products.extend(scraped_products)
                print(f"✅ Scraping directo: {len(scraped_products)} productos")
            except Exception as e:
                print(f"❌ Error scraping: {e}")
        
        # 4. Búsqueda específica por sitios
        if len(all_products) < 10:
            try:
                print("🎯 Búsqueda específica por tiendas...")
                site_products = self._search_specific_sites(query)
                all_products.extend(site_products)
                print(f"✅ Sitios específicos: {len(site_products)} productos")
            except Exception as e:
                print(f"❌ Error sitios específicos: {e}")
        
        print(f"📊 Total productos encontrados: {len(all_products)}")
        
        if all_products:
            # Filtrar solo productos con links reales
            real_products = [p for p in all_products if p and self._is_real_product_link(p.get('link', ''))]
            print(f"✅ Productos con links reales: {len(real_products)}")
            
            if real_products:
                unique_products = self._remove_duplicates(real_products)
                sorted_products = sorted(unique_products, key=lambda x: x.get('price_numeric', 999))
                print(f"🎯 Productos únicos ordenados: {len(sorted_products)}")
                return sorted_products[:25]
        
        print("❌ No se encontraron productos reales")
        return []
    
    def _search_serpapi_shopping(self, query):
        """Búsqueda principal en Google Shopping"""
        products = []
        
        # Múltiples consultas para mejores resultados
        search_queries = [
            query,
            f"{query} cheap",
            f"{query} sale discount",
            f"{query} best price"
        ]
        
        for search_query in search_queries[:2]:  # Limitar para no agotar créditos
            try:
                params = {
                    'engine': 'google_shopping',
                    'q': search_query,
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
                
                if data and 'shopping_results' in data:
                    for item in data['shopping_results']:
                        product = self._process_shopping_item(item)
                        if product:
                            products.append(product)
                
                if len(products) >= 20:
                    break
                    
            except Exception as e:
                print(f"Error en consulta '{search_query}': {e}")
                continue
        
        return products
    
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
    
    def _scrape_direct_stores(self, query):
        """Scraping directo de tiendas (requiere librerías adicionales)"""
        if not HAS_ENHANCED:
            return []
        
        products = []
        
        # Configurar headers realistas
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Tiendas para scraping directo
        stores = [
            {
                'name': 'eBay',
                'search_url': f'https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=15',
                'item_selector': '.s-item',
                'title_selector': '.s-item__title',
                'price_selector': '.s-item__price',
                'link_selector': '.s-item__link'
            },
            {
                'name': 'Walmart',
                'search_url': f'https://www.walmart.com/search?q={quote_plus(query)}',
                'item_selector': '[data-automation-id="product-title"]',
                'title_selector': '[data-automation-id="product-title"]',
                'price_selector': '[itemprop="price"]',
                'link_selector': 'a'
            }
        ]
        
        for store in stores:
            try:
                store_products = self._scrape_single_store(store, headers)
                products.extend(store_products)
                if len(products) >= 15:
                    break
            except Exception as e:
                print(f"Error scraping {store['name']}: {e}")
                continue
        
        return products
    
    def _scrape_single_store(self, store, headers):
        """Scraping de una tienda específica"""
        products = []
        
        try:
            response = self.scraper.get(store['search_url'], headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'lxml')
            
            items = soup.select(store['item_selector'])[:10]
            
            for item in items:
                try:
                    # Título
                    title_elem = item.select_one(store['title_selector'])
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # Precio usando price-parser
                    price_elem = item.select_one(store['price_selector'])
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                    else:
                        price_text = item.get_text()
                    
                    if HAS_ENHANCED:
                        parsed_price = Price.fromstring(price_text)
                        if not parsed_price.amount:
                            continue
                        price_numeric = float(parsed_price.amount)
                    else:
                        price_numeric = self._extract_price_basic(price_text)
                    
                    if price_numeric <= 0 or price_numeric > 10000:
                        continue
                    
                    # Link
                    link_elem = item.select_one(store['link_selector']) or item.select_one('a')
                    if not link_elem:
                        continue
                    
                    link = link_elem.get('href', '')
                    if link.startswith('/'):
                        if store['name'].lower() == 'ebay':
                            link = 'https://www.ebay.com' + link
                        elif store['name'].lower() == 'walmart':
                            link = 'https://www.walmart.com' + link
                    
                    if not self._is_real_product_link(link):
                        continue
                    
                    products.append({
                        'title': self._clean_text(title),
                        'price': f"${price_numeric:.2f}",
                        'price_numeric': price_numeric,
                        'source': store['name'],
                        'link': link,
                        'rating': '',
                        'reviews': '',
                        'image': '',
                        'is_real': True,
                        'source_type': 'scraped'
                    })
                    
                except Exception as e:
                    print(f"Error procesando item: {e}")
                    continue
        
        except Exception as e:
            print(f"Error scraping {store['name']}: {e}")
        
        return products
    
    def _search_specific_sites(self, query):
        """Búsqueda específica usando site: operator"""
        products = []
        
        site_searches = [
            f'site:amazon.com {query} -site:amazon.com/s',
            f'site:ebay.com {query} -site:ebay.com/sch',
            f'site:walmart.com {query} -site:walmart.com/search'
        ]
        
        for site_query in site_searches:
            try:
                params = {
                    'engine': 'google',
                    'q': site_query,
                    'api_key': self.api_key,
                    'num': 10,
                    'location': 'United States'
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                data = response.json() if response else None
                
                if data and 'organic_results' in data:
                    for item in data['organic_results']:
                        product = self._process_organic_result(item)
                        if product and self._is_real_product_link(product['link']):
                            products.append(product)
            except:
                continue
        
        return products
    
    def _process_shopping_item(self, item):
        """Procesa items de shopping con validación estricta"""
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
            
            price_num = self._extract_price_enhanced(price_str) if HAS_ENHANCED else self._extract_price_basic(price_str)
            if price_num <= 0:
                return None
            
            # Extraer link REAL del producto
            product_link = self._extract_real_product_link(item)
            if not product_link:
                return None
            
            # Verificar título
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
                'source_type': 'api'
            }
            
        except Exception as e:
            print(f"Error procesando shopping item: {e}")
            return None
    
    def _process_organic_result(self, item):
        """Procesa resultados orgánicos buscando precios"""
        if not item:
            return None
        
        try:
            # Buscar precio en snippet y título
            search_text = f"{item.get('snippet', '')} {item.get('title', '')}"
            price_match = re.search(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', search_text)
            
            if not price_match:
                return None
            
            price_str = price_match.group(0)
            price_num = self._extract_price_basic(price_str)
            
            if price_num <= 0:
                return None
            
            link = item.get('link', '')
            if not self._is_real_product_link(link):
                return None
            
            # Extraer fuente del link
            try:
                parsed = urlparse(link)
                source = parsed.netloc.replace('www.', '')
            except:
                source = item.get('displayed_link', 'Unknown')
            
            return {
                'title': self._clean_text(item.get('title', 'Product')),
                'price': price_str,
                'price_numeric': float(price_num),
                'source': self._clean_text(source),
                'link': link,
                'rating': '',
                'reviews': '',
                'image': '',
                'is_real': True,
                'source_type': 'organic'
            }
            
        except:
            return None
    
    def _extract_real_product_link(self, item):
        """Extrae SOLO links reales de productos específicos"""
        if not item:
            return ""
        
        for field in ['product_link', 'link', 'serpapi_product_api_link']:
            if field in item and item[field]:
                raw_link = str(item[field])
                
                # Extraer de redirects de Google
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
        """Validación estricta de links reales de productos"""
        if not link:
            return False
        
        try:
            link_lower = str(link).lower()
            
            # Rechazar búsquedas generales
            search_indicators = [
                '/search?', '/s?k=', '/sch/', '?q=', 'search=', 
                '/search/', 'query=', '_nkw=', 'searchterm=',
                'google.com/search', 'bing.com/search', '/browse/',
                '/category/', '/categories/', '/shop/', '/store/'
            ]
            
            if any(indicator in link_lower for indicator in search_indicators):
                return False
            
            # Patrones de URLs de productos válidos
            product_patterns = [
                r'/dp/[A-Z0-9]+',           # Amazon DP
                r'/gp/product/[A-Z0-9]+',   # Amazon GP
                r'/itm/\d+',                # eBay item
                r'/p/\d+',                  # eBay/Target product
                r'/ip/\d+',                 # Walmart IP
                r'/pd/[^/]+/\d+',          # Lowe's product
                r'/product/[^/]+',          # Generic product
                r'/listing/\d+',            # Etsy listing
                r'/item/\d+',               # Generic item
                r'-p-\d+',                  # Some stores use this format
            ]
            
            # Verificar patrones de productos
            has_product_pattern = any(re.search(pattern, link_lower) for pattern in product_patterns)
            
            # Tiendas válidas conocidas
            valid_domains = [
                'amazon.com', 'ebay.com', 'walmart.com', 'target.com',
                'homedepot.com', 'lowes.com', 'bestbuy.com', 'costco.com',
                'overstock.com', 'wayfair.com', 'etsy.com', 'mercari.com',
                'alibaba.com', 'aliexpress.com', 'liquidator', 'clearance'
            ]
            
            has_valid_domain = any(domain in link_lower for domain in valid_domains)
            
            if has_product_pattern or has_valid_domain:
                parsed = urlparse(link)
                return bool(parsed.scheme and parsed.netloc)
            
            return False
            
        except:
            return False
    
    def _extract_price_enhanced(self, price_str):
        """Extracción de precios con price-parser"""
        try:
            parsed = Price.fromstring(str(price_str))
            if parsed.amount:
                return float(parsed.amount)
        except:
            pass
        
        return self._extract_price_basic(price_str)
    
    def _extract_price_basic(self, price_str):
        """Extracción básica de precios"""
        if not price_str:
            return 0.0
        try:
            price_text = str(price_str).lower()
            
            # Buscar precios de oferta primero
            sale_patterns = [
                r'(?:sale|now|offer|deal)[:\s]*\$?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',
                r'\$(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',
                r'(\d+\.\d{2})',
                r'(\d+)',
            ]
            
            for pattern in sale_patterns:
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
        if not text:
            return "Sin información"
        cleaned = html.escape(str(text), quote=True)
        return cleaned[:150] + "..." if len(cleaned) > 150 else cleaned
    
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
                if product['price_numeric'] < seen_titles[title_key]['price_numeric']:
                    unique_products = [p for p in unique_products if p['title'][:50].lower().strip() != title_key]
                    unique_products.append(product)
                    seen_titles[title_key] = product
        
        return unique_products

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
        .features li:before {{ content: "🚀 "; }}
        .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; 
                 margin: 15px 0; display: none; }}
        .loading {{ text-align: center; padding: 40px; display: none; }}
        .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1a73e8; border-radius: 50%; 
                   width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .enhancement-note {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; 
                           border-radius: 8px; margin-top: 15px; }}
    </style>
</head>
<body>{content}</body>
</html>'''

@app.route('/')
def index():
    enhancement_status = "✅ Modo MEJORADO activado" if HAS_ENHANCED else "⚠️ Modo básico - instala librerías para mejores resultados"
    
    content = f'''
    <div class="container">
        <h1>🚀 Price Finder USA - ENHANCED</h1>
        <p class="subtitle">🎯 Múltiples fuentes + Scraping directo + APIs</p>
        
        <div class="enhancement-note">
            <strong>{enhancement_status}</strong><br>
            {'Scraping directo + Price-parser + CloudScraper funcionando' if HAS_ENHANCED else 'Para mejores resultados: pip install beautifulsoup4 cloudscraper fake-useragent price-parser lxml'}
        </div>
        
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">🚀 Activar Búsqueda ENHANCED</button>
        </form>
        
        <div class="features">
            <h3>🚀 Características ENHANCED:</h3>
            <ul>
                <li>Google Shopping + Bing Shopping APIs</li>
                <li>Scraping directo de eBay, Walmart {"(ACTIVO)" if HAS_ENHANCED else "(requiere librerías)"}</li>
                <li>Price-parser inteligente {"(ACTIVO)" if HAS_ENHANCED else "(requiere librerías)"}</li>
                <li>CloudScraper anti-detección {"(ACTIVO)" if HAS_ENHANCED else "(requiere librerías)"}</li>
                <li>Validación estricta de links reales</li>
                <li>Hasta 25 productos de múltiples fuentes</li>
                <li>Detección automática de ofertas</li>
            </ul>
        </div>
        
        <div id="error" class="error"></div>
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Validando API key...</p>
        </div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return showError('Por favor ingresa tu API key');
            
            showLoading();
            fetch('/setup', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: 'api_key=' + encodeURIComponent(apiKey)
            }})
            .then(response => response.json())
            .then(data => {{
                hideLoading();
                data.success ? window.location.href = '/search' : showError(data.error || 'Error al configurar API key');
            }})
            .catch(() => {{ hideLoading(); showError('Error de conexión'); }});
        }});
        function showLoading() {{ document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }}
        function hideLoading() {{ document.getElementById('loading').style.display = 'none'; }}
        function showError(msg) {{ hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }}
    </script>'''
    return render_page('🚀 Price Finder USA - ENHANCED', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 400
        
        price_finder = EnhancedPriceFinder(api_key)
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
    
    enhancement_note = "🚀 Scraping + APIs múltiples activos" if HAS_ENHANCED else "📱 Modo básico - SerpAPI únicamente"
    
    content = f'''
    <div class="container">
        <h1>🔍 Búsqueda ENHANCED</h1>
        <p class="subtitle">🎯 Múltiples fuentes para mejores resultados</p>
        
        <div class="enhancement-note">
            <strong>{enhancement_note}</strong>
        </div>
        
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: iPhone 15, cinta adhesiva azul, laptop gaming..." required>
                <button type="submit">🚀 Buscar ENHANCED</button>
            </div>
        </form>
        
        <div class="tips">
            <h4>🚀 Búsqueda con múltiples fuentes:</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Google Shopping</strong> - API principal</li>
                <li><strong>Bing Shopping</strong> - Resultados alternativos</li>
                <li><strong>Scraping directo</strong> - eBay, Walmart {"✅" if HAS_ENHANCED else "❌"}</li>
                <li><strong>Búsquedas específicas</strong> - site:amazon.com, etc.</li>
                <li><strong>Validación estricta</strong> - Solo links reales a productos</li>
            </ul>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🚀 Búsqueda ENHANCED en progreso...</h3>
            <p>Analizando múltiples fuentes y validando links...</p>
        </div>
        
        <div id="error" class="error"></div>
    </div>
    <script>
        let searching = false;
        document.getElementById('searchForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            if (searching) return;
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return showError('Por favor ingresa un producto para buscar');
            
            searching = true;
            showLoading();
            fetch('/api/search', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{query: query}})
            }})
            .then(response => response.json())
            .then(data => {{
                searching = false;
                data.success ? window.location.href = '/results' : (hideLoading(), showError(data.error || 'Error en la búsqueda'));
            }})
            .catch(() => {{ searching = false; hideLoading(); showError('Error de conexión'); }});
        }});
        function showLoading() {{ document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }}
        function hideLoading() {{ document.getElementById('loading').style.display = 'none'; }}
        function showError(msg) {{ hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }}
    </script>'''
    return render_page('🔍 Búsqueda ENHANCED - Price Finder USA', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        if 'api_key' not in session:
            return jsonify({'error': 'API key no configurada'}), 400
        
        data = request.get_json()
        query = data.get('query', '').strip() if data else ''
        if not query:
            return jsonify({'error': 'Consulta requerida'}), 400
        
        price_finder = EnhancedPriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        if not products:
            return jsonify({
                'success': False, 
                'error': 'No se encontraron productos reales para esta búsqueda. Intenta con términos más específicos o marcas conocidas.',
                'suggestion': 'Prueba con: marca + modelo específico, palabras más descriptivas, o términos en inglés'
            })
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'enhanced_mode': HAS_ENHANCED
        }
        
        return jsonify({
            'success': True, 
            'products': products, 
            'total': len(products),
            'enhanced_mode': HAS_ENHANCED,
            'sources_used': list(set([p.get('source_type', 'api') for p in products]))
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
        enhanced_mode = search_data.get('enhanced_mode', False)
        
        if not products:
            no_results_content = f'''
            <div style="max-width: 900px; margin: 0 auto;">
                <h1 style="color: white; text-align: center; margin-bottom: 10px;">❌ Sin resultados para: "{query}"</h1>
                <div style="background: white; padding: 40px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #666; margin-bottom: 20px;">No encontramos productos reales con links directos</h3>
                    <p style="color: #888; margin-bottom: 30px;">
                        Sistema ENHANCED activó múltiples fuentes pero no encontró productos válidos.<br>
                        Intenta con términos más específicos, marcas conocidas, o palabras en inglés.
                    </p>
                    <a href="/search" style="background: #1a73e8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        🔍 Intentar Nueva Búsqueda
                    </a>
                </div>
            </div>'''
            return render_page('Sin Resultados - Price Finder USA', no_results_content)
        
        # Generar HTML de productos con indicadores de fuente
        products_html = ""
        
        for i, product in enumerate(products):
            if not product:
                continue
            
            # Badges según posición y tipo de fuente
            badge = ""
            source_type = product.get('source_type', 'api')
            
            if i == 0:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥇 MÁS BARATO</div>'
            elif i == 1:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º MÁS BARATO</div>'
            elif i == 2:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #9c27b0; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥉 3º MÁS BARATO</div>'
            
            # Indicador de fuente
            source_indicators = {
                'scraped': '🕷️ SCRAPED',
                'api': '📡 API',
                'organic': '🔍 SEARCH'
            }
            source_indicator = source_indicators.get(source_type, '📡 API')
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = product.get('link', '#')
            rating = html.escape(str(product.get('rating', '')))
            reviews = html.escape(str(product.get('reviews', '')))
            
            rating_html = f"⭐ {rating}" if rating else ""
            reviews_html = f"📝 {reviews} reseñas" if reviews else ""
            
            products_html += f'''
                <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    {badge}
                    <div style="position: absolute; top: 10px; left: 10px; background: #e3f2fd; color: #1565c0; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">
                        {source_indicator}
                    </div>
                    <h3 style="color: #1a73e8; margin-bottom: 12px; margin-top: 25px;">{title}</h3>
                    <p style="font-size: 32px; color: #2e7d32; font-weight: bold; margin: 12px 0;">{price}</p>
                    <p style="color: #666; margin-bottom: 10px;">🏪 {source}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        {rating_html} {reviews_html} {" • " if rating_html and reviews_html else ""} ✅ Link directo verificado
                    </div>
                    <a href="{link}" target="_blank" rel="noopener noreferrer" style="background: #4caf50; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                        🛒 IR AL PRODUCTO en {source}
                    </a>
                </div>'''
        
        # Estadísticas mejoradas
        prices = [p.get('price_numeric', 0) for p in products if p and p.get('price_numeric', 0) > 0]
        source_types = {}
        for p in products:
            if p:
                source_type = p.get('source_type', 'api')
                source_types[source_type] = source_types.get(source_type, 0) + 1
        
        sources_summary = " + ".join([f"{count} {stype.upper()}" for stype, count in source_types.items()])
        
        stats = ""
        if prices:
            min_price, max_price, avg_price = min(prices), max(prices), sum(prices) / len(prices)
            stats = f'''
                <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c9); border: 2px solid #4caf50; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="color: #2e7d32; margin-bottom: 10px;">🚀 Resultados ENHANCED encontrados</h3>
                    <p><strong>🎯 {len(products)} productos de múltiples fuentes:</strong> {sources_summary}</p>
                    <p><strong>💰 Precio más bajo:</strong> ${min_price:.2f}</p>
                    <p><strong>📊 Precio promedio:</strong> ${avg_price:.2f}</p>
                    <p><strong>💸 Diferencia de precio:</strong> ${max_price - min_price:.2f}</p>
                    <p><strong>🚀 Modo Enhanced:</strong> {"✅ ACTIVO" if enhanced_mode else "❌ Básico"}</p>
                </div>'''
        
        content = f'''
        <div style="max-width: 900px; margin: 0 auto;">
            <h1 style="color: white; text-align: center; margin-bottom: 10px;">🚀 Resultados ENHANCED: "{query}"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px;">✅ Múltiples fuentes + Links directos verificados</p>
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="/search" style="background: white; color: #1a73e8; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600;">🔍 Nueva Búsqueda ENHANCED</a>
            </div>
            {stats}
            {products_html}
        </div>'''
        
        return render_page('🚀 Resultados ENHANCED - Price Finder USA', content)
    except Exception as e:
        print(f"Error en results_page: {e}")
        return redirect(url_for('search_page'))

@app.route('/api/test')
def test_endpoint():
    return jsonify({
        'status': 'SUCCESS',
        'message': '🚀 Price Finder USA - ENHANCED MODE',
        'version': '10.0 - Múltiples fuentes + Scraping + APIs',
        'features': {
            'enhanced_libraries': HAS_ENHANCED,
            'google_shopping': True,
            'bing_shopping': True,
            'direct_scraping': HAS_ENHANCED,
            'real_link_validation': True,
            'multi_source_search': True,
            'price_parser': HAS_ENHANCED,
            'cloudscraper': HAS_ENHANCED
        },
        'libraries_status': {
            'beautifulsoup4': HAS_ENHANCED,
            'cloudscraper': HAS_ENHANCED,
            'fake_useragent': HAS_ENHANCED,
            'price_parser': HAS_ENHANCED
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Sistema ENHANCED funcionando',
        'enhanced_mode': HAS_ENHANCED,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Iniciando Price Finder USA - ENHANCED MODE")
    print(f"📊 Librerías mejoradas: {'✅ ACTIVAS' if HAS_ENHANCED else '❌ No instaladas'}")
    if not HAS_ENHANCED:
        print("💡 Para mejores resultados ejecuta: pip install beautifulsoup4 cloudscraper fake-useragent price-parser lxml")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
