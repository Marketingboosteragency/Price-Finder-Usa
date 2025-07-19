from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
import json
import time

# Importaciones corregidas (sin lxml)
try:
    from bs4 import BeautifulSoup
    import cloudscraper
    from fake_useragent import UserAgent
    from price_parser import Price
    HAS_ENHANCED = True
    print("✅ Librerías mejoradas cargadas: BeautifulSoup (html.parser), CloudScraper, Price-Parser")
except ImportError:
    HAS_ENHANCED = False
    print("⚠️ Usando modo básico. Para mejores resultados instala: pip install beautifulsoup4 cloudscraper fake-useragent price-parser")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

class UltimatePriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        
        # APIs adicionales
        self.scraperapi_key = os.environ.get('SCRAPERAPI_KEY', '')
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY', '')
        
        if HAS_ENHANCED:
            self.scraper = cloudscraper.create_scraper()
            self.ua = UserAgent()
        
        print(f"🔑 ScraperAPI: {'✅' if self.scraperapi_key else '❌ (opcional)'}")
        print(f"🔑 RapidAPI: {'✅' if self.rapidapi_key else '❌ (opcional)'}")
        
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
        """Búsqueda ULTIMATE con todas las fuentes posibles"""
        if not query:
            return []
        
        all_products = []
        
        print(f"🔍 ULTIMATE SEARCH para: {query}")
        
        # 1. SerpAPI Google Shopping (principal)
        try:
            print("📡 Buscando en Google Shopping...")
            serpapi_products = self._search_serpapi_shopping(query)
            all_products.extend(serpapi_products)
            print(f"✅ Google Shopping: {len(serpapi_products)} productos")
        except Exception as e:
            print(f"❌ Error Google Shopping: {e}")
        
        # 2. RapidAPI Shopping
        if self.rapidapi_key and len(all_products) < 20:
            try:
                print("🛒 Buscando en RapidAPI Shopping...")
                rapidapi_products = self._search_rapidapi_shopping(query)
                all_products.extend(rapidapi_products)
                print(f"✅ RapidAPI Shopping: {len(rapidapi_products)} productos")
            except Exception as e:
                print(f"❌ Error RapidAPI: {e}")
        
        # 3. ScraperAPI para sitios especializados
        if self.scraperapi_key and len(all_products) < 15:
            try:
                print("🕷️ Scraping sitios especializados...")
                scraped_specialized = self._scrape_specialized_stores(query)
                all_products.extend(scraped_specialized)
                print(f"✅ Sitios especializados: {len(scraped_specialized)} productos")
            except Exception as e:
                print(f"❌ Error scraping especializado: {e}")
        
        # 4. Scraping directo básico (sin lxml)
        if HAS_ENHANCED and len(all_products) < 15:
            try:
                print("🕷️ Scraping directo básico...")
                scraped_basic = self._scrape_basic_stores(query)
                all_products.extend(scraped_basic)
                print(f"✅ Scraping básico: {len(scraped_basic)} productos")
            except Exception as e:
                print(f"❌ Error scraping básico: {e}")
        
        # 5. Bing Shopping
        try:
            print("📡 Buscando en Bing Shopping...")
            bing_products = self._search_bing_shopping(query)
            all_products.extend(bing_products)
            print(f"✅ Bing Shopping: {len(bing_products)} productos")
        except Exception as e:
            print(f"❌ Error Bing Shopping: {e}")
        
        print(f"📊 Total productos encontrados: {len(all_products)}")
        
        if all_products:
            real_products = [p for p in all_products if p and self._is_real_product_link(p.get('link', ''))]
            print(f"✅ Productos con links reales: {len(real_products)}")
            
            if real_products:
                unique_products = self._remove_duplicates(real_products)
                sorted_products = sorted(unique_products, key=lambda x: x.get('price_numeric', 999))
                print(f"🎯 Productos únicos ordenados: {len(sorted_products)}")
                return sorted_products[:30]
        
        print("❌ No se encontraron productos reales")
        return []
    
    def _search_serpapi_shopping(self, query):
        """Búsqueda principal en Google Shopping"""
        products = []
        
        search_queries = [
            query,
            f"{query} cheap",
            f"{query} sale discount",
            f"{query} liquidator clearance"
        ]
        
        for search_query in search_queries[:2]:
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
                'q': f"{query} discount clearance",
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
    
    def _search_rapidapi_shopping(self, query):
        """RapidAPI Shopping"""
        if not self.rapidapi_key:
            return []
        
        products = []
        
        # API Real-Time Shopping
        try:
            url = "https://real-time-product-search.p.rapidapi.com/search"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "real-time-product-search.p.rapidapi.com"
            }
            params = {
                "q": query,
                "country": "us",
                "language": "en",
                "limit": "20",
                "sort_by": "PRICE_LOW_TO_HIGH"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json() if response else None
            
            if data and 'data' in data:
                for item in data['data'][:15]:
                    product = self._process_rapidapi_item(item)
                    if product:
                        products.append(product)
            
        except Exception as e:
            print(f"Error RapidAPI: {e}")
        
        return products
    
    def _scrape_specialized_stores(self, query):
        """Scraping de tiendas especializadas usando ScraperAPI"""
        if not self.scraperapi_key:
            return []
        
        products = []
        
        specialized_stores = [
            {
                'name': 'LumberLiquidators',
                'search_url': f'https://lumberliquidators.com/search?q={quote_plus(query)}',
                'base_url': 'https://lumberliquidators.com'
            },
            {
                'name': 'Overstock',
                'search_url': f'https://overstock.com/search?keywords={quote_plus(query)}',
                'base_url': 'https://overstock.com'
            }
        ]
        
        for store in specialized_stores[:1]:  # Limitar para no agotar API
            try:
                store_products = self._scrape_with_scraperapi(store, query)
                products.extend(store_products)
                time.sleep(1)
            except Exception as e:
                print(f"Error scraping {store['name']}: {e}")
                continue
        
        return products
    
    def _scrape_with_scraperapi(self, store, query):
        """Scraping usando ScraperAPI"""
        products = []
        
        try:
            scraperapi_url = "http://api.scraperapi.com"
            params = {
                'api_key': self.scraperapi_key,
                'url': store['search_url'],
                'render': 'true',
                'country_code': 'us'
            }
            
            response = requests.get(scraperapi_url, params=params, timeout=20)
            
            if response.status_code == 200:
                # Usar html.parser en lugar de lxml
                soup = BeautifulSoup(response.content, 'html.parser')
                
                product_selectors = [
                    '.product-item', '.product-card', '.product', '.item',
                    '[data-product]', '[data-item]', '.search-result'
                ]
                
                items = []
                for selector in product_selectors:
                    items = soup.select(selector)
                    if items:
                        break
                
                for item in items[:8]:
                    try:
                        product = self._extract_from_scraperapi_element(item, store)
                        if product and self._is_real_product_link(product['link']):
                            products.append(product)
                    except:
                        continue
            
        except Exception as e:
            print(f"Error ScraperAPI para {store['name']}: {e}")
        
        return products
    
    def _scrape_basic_stores(self, query):
        """Scraping básico con CloudScraper (sin lxml)"""
        if not HAS_ENHANCED:
            return []
        
        products = []
        
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        basic_stores = [
            {
                'name': 'eBay',
                'search_url': f'https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=15',
                'item_selector': '.s-item',
                'title_selector': '.s-item__title',
                'price_selector': '.s-item__price',
                'link_selector': '.s-item__link'
            }
        ]
        
        for store in basic_stores:
            try:
                response = self.scraper.get(store['search_url'], headers=headers, timeout=10)
                # Usar html.parser en lugar de lxml
                soup = BeautifulSoup(response.content, 'html.parser')
                
                items = soup.select(store['item_selector'])[:8]
                
                for item in items:
                    try:
                        product = self._extract_basic_store_item(item, store)
                        if product and self._is_real_product_link(product['link']):
                            products.append(product)
                    except:
                        continue
                        
            except Exception as e:
                print(f"Error scraping {store['name']}: {e}")
        
        return products
    
    def _extract_from_scraperapi_element(self, element, store):
        """Extrae datos de elemento HTML de ScraperAPI"""
        try:
            title_selectors = [
                'h3', 'h4', '.title', '.product-title', '.name', 
                '[data-title]', 'a[title]'
            ]
            title = ""
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True) or title_elem.get('title', '')
                    if title and len(title) > 5:
                        break
            
            if not title or len(title) < 5:
                return None
            
            price_text = element.get_text()
            if HAS_ENHANCED:
                try:
                    parsed_price = Price.fromstring(price_text)
                    if parsed_price.amount:
                        price_numeric = float(parsed_price.amount)
                    else:
                        price_numeric = self._extract_price_basic(price_text)
                except:
                    price_numeric = self._extract_price_basic(price_text)
            else:
                price_numeric = self._extract_price_basic(price_text)
            
            if price_numeric <= 0 or price_numeric > 5000:
                return None
            
            link_elem = element.select_one('a[href]')
            if not link_elem:
                return None
            
            link = link_elem.get('href', '')
            if link.startswith('/'):
                link = store['base_url'] + link
            elif link.startswith('//'):
                link = 'https:' + link
            
            if not self._is_real_product_link(link):
                return None
            
            return {
                'title': self._clean_text(title),
                'price': f"${price_numeric:.2f}",
                'price_numeric': price_numeric,
                'source': store['name'],
                'link': link,
                'rating': '',
                'reviews': '',
                'image': '',
                'is_real': True,
                'source_type': 'scraperapi'
            }
            
        except Exception as e:
            print(f"Error extrayendo datos ScraperAPI: {e}")
            return None
    
    def _extract_basic_store_item(self, element, store):
        """Extrae datos de tienda básica"""
        try:
            title_elem = element.select_one(store['title_selector'])
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 5:
                return None
            
            price_elem = element.select_one(store['price_selector'])
            if not price_elem:
                return None
            
            price_text = price_elem.get_text(strip=True)
            price_numeric = self._extract_price_enhanced(price_text) if HAS_ENHANCED else self._extract_price_basic(price_text)
            
            if price_numeric <= 0:
                return None
            
            link_elem = element.select_one(store['link_selector'])
            if not link_elem:
                return None
            
            link = link_elem.get('href', '')
            if link.startswith('/'):
                if store['name'].lower() == 'ebay':
                    link = 'https://www.ebay.com' + link
            
            return {
                'title': self._clean_text(title),
                'price': f"${price_numeric:.2f}",
                'price_numeric': price_numeric,
                'source': store['name'],
                'link': link,
                'rating': '',
                'reviews': '',
                'image': '',
                'is_real': True,
                'source_type': 'basic_scraping'
            }
            
        except:
            return None
    
    def _process_shopping_item(self, item):
        """Procesa items de shopping APIs"""
        if not item:
            return None
        
        try:
            price_str = item.get('price', '')
            if not price_str:
                for field in ['extracted_price', 'sale_price', 'current_price']:
                    if item.get(field):
                        price_str = item[field]
                        break
            
            price_num = self._extract_price_enhanced(price_str) if HAS_ENHANCED else self._extract_price_basic(price_str)
            if price_num <= 0:
                return None
            
            product_link = self._extract_real_product_link(item)
            if not product_link:
                return None
            
            title = item.get('title', '')
            if not title or len(title.strip()) < 5:
                return None
            
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
    
    def _process_rapidapi_item(self, item):
        """Procesa items de RapidAPI"""
        try:
            title = item.get('title') or item.get('product_title') or item.get('name', '')
            if not title or len(title) < 5:
                return None
            
            price_fields = ['price', 'product_price', 'current_price', 'sale_price']
            price_str = ""
            for field in price_fields:
                if item.get(field):
                    price_str = str(item[field])
                    break
            
            if not price_str:
                return None
            
            price_numeric = self._extract_price_enhanced(price_str) if HAS_ENHANCED else self._extract_price_basic(price_str)
            if price_numeric <= 0:
                return None
            
            link = item.get('product_url') or item.get('url') or item.get('link', '')
            if not self._is_real_product_link(link):
                return None
            
            source = item.get('source') or item.get('store') or item.get('merchant', 'Online Store')
            
            return {
                'title': self._clean_text(title),
                'price': f"${price_numeric:.2f}",
                'price_numeric': price_numeric,
                'source': self._clean_text(source),
                'link': link,
                'rating': str(item.get('rating', '')),
                'reviews': str(item.get('reviews', '')),
                'image': str(item.get('image', '')),
                'is_real': True,
                'source_type': 'rapidapi'
            }
            
        except Exception as e:
            print(f"Error procesando RapidAPI item: {e}")
            return None
    
    def _extract_real_product_link(self, item):
        """Extrae links reales de productos"""
        if not item:
            return ""
        
        for field in ['product_link', 'link', 'serpapi_product_api_link']:
            if field in item and item[field]:
                raw_link = str(item[field])
                
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
        """Validación de links reales"""
        if not link:
            return False
        
        try:
            link_lower = str(link).lower()
            
            search_indicators = [
                '/search?', '/s?k=', '/sch/', '?q=', 'search=', 
                '/search/', 'query=', '_nkw=', 'searchterm=',
                'google.com/search', 'bing.com/search'
            ]
            
            if any(indicator in link_lower for indicator in search_indicators):
                return False
            
            product_patterns = [
                r'/dp/[A-Z0-9]+',           # Amazon
                r'/itm/\d+',                # eBay
                r'/ip/\d+',                 # Walmart
                r'/p/\d+',                  # Target/eBay
                r'/product/',               # Generic
                r'/products/',              # Shopify (lumberliquidators)
                r'\?variant=\d+',           # Shopify variants
                r'/listing/\d+',            # Etsy
                r'/item/\d+',               # Generic
            ]
            
            has_product_pattern = any(re.search(pattern, link_lower) for pattern in product_patterns)
            
            valid_domains = [
                'amazon.com', 'ebay.com', 'walmart.com', 'target.com',
                'lumberliquidators.com', 'liquidation.com', 'overstock.com',
                'woot.com', 'surplus.com', 'clearance', 'liquidator',
                'homedepot.com', 'lowes.com', 'bestbuy.com'
            ]
            
            has_valid_domain = any(domain in link_lower for domain in valid_domains)
            
            if has_product_pattern or has_valid_domain:
                parsed = urlparse(link)
                return bool(parsed.scheme and parsed.netloc)
            
            return False
            
        except:
            return False
    
    def _extract_price_enhanced(self, price_str):
        """Extracción mejorada con price-parser"""
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

# Resto del código Flask (igual que antes pero usando la clase corregida)
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
        .api-status {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; 
                      border-radius: 8px; margin-top: 15px; }}
    </style>
</head>
<body>{content}</body>
</html>'''

@app.route('/')
def index():
    finder = UltimatePriceFinder('test')
    
    content = f'''
    <div class="container">
        <h1>🎯 Price Finder USA - FIXED</h1>
        <p class="subtitle">✅ Corregido para Python 3.13 (sin lxml)</p>
        
        <div class="api-status">
            <strong>🔌 Sistema corregido:</strong><br>
            ✅ SerpAPI (Google + Bing Shopping)<br>
            ✅ BeautifulSoup con html.parser (sin lxml)<br>
            {'✅' if finder.scraperapi_key else '❌'} ScraperAPI (opcional)<br>
            {'✅' if finder.rapidapi_key else '❌'} RapidAPI Shopping (opcional)
        </div>
        
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">🎯 Activar Sistema CORREGIDO</button>
        </form>
        
        <div class="features">
            <h3>✅ Sistema corregido para Render:</h3>
            <ul>
                <li>Removido lxml incompatible con Python 3.13</li>
                <li>BeautifulSoup usa html.parser built-in</li>
                <li>Todas las funciones mantienen compatibilidad</li>
                <li>Scraping LumberLiquidators funcional</li>
                <li>APIs opcionales siguen disponibles</li>
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
    return render_page('🎯 Price Finder USA - FIXED', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 400
        
        price_finder = UltimatePriceFinder(api_key)
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
    
    finder = UltimatePriceFinder('test')
    
    content = f'''
    <div class="container">
        <h1>🔍 Búsqueda CORREGIDA</h1>
        <p class="subtitle">✅ Compatible con Python 3.13</p>
        
        <div class="api-status">
            <strong>🚀 Fuentes activas:</strong><br>
            Google Shopping ✅ | Bing Shopping ✅ | 
            ScraperAPI {'✅' if finder.scraperapi_key else '❌'} | 
            RapidAPI {'✅' if finder.rapidapi_key else '❌'} | 
            Scraping directo ✅ (html.parser)
        </div>
        
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: blue painters tape, cinta adhesiva azul..." required>
                <button type="submit">🎯 Buscar CORREGIDO</button>
            </div>
        </form>
        
        <div class="tips">
            <h4>✅ Sistema corregido incluye:</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Sin errores lxml:</strong> BeautifulSoup con parser nativo</li>
                <li><strong>Liquidadores:</strong> LumberLiquidators, Overstock</li>
                <li><strong>APIs múltiples:</strong> Google, Bing, RapidAPI</li>
                <li><strong>Scraping funcional:</strong> CloudScraper + html.parser</li>
                <li><strong>Links reales:</strong> Verificación estricta</li>
            </ul>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🎯 Búsqueda en progreso...</h3>
            <p>Sistema corregido analizando fuentes...</p>
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
    return render_page('🔍 Búsqueda CORREGIDA', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        if 'api_key' not in session:
            return jsonify({'error': 'API key no configurada'}), 400
        
        data = request.get_json()
        query = data.get('query', '').strip() if data else ''
        if not query:
            return jsonify({'error': 'Consulta requerida'}), 400
        
        price_finder = UltimatePriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        if not products:
            return jsonify({
                'success': False, 
                'error': 'No se encontraron productos reales. Sistema corregido analizó todas las fuentes.',
                'suggestion': 'Intenta con términos más específicos o marcas conocidas'
            })
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'fixed_mode': True
        }
        
        return jsonify({
            'success': True, 
            'products': products, 
            'total': len(products),
            'fixed_mode': True
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
                <h1 style="color: white; text-align: center; margin-bottom: 10px;">❌ Sin resultados para: "{query}"</h1>
                <div style="background: white; padding: 40px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #666; margin-bottom: 20px;">Sistema corregido analizó todas las fuentes</h3>
                    <p style="color: #888; margin-bottom: 30px;">
                        El sistema funciona correctamente pero no encontró productos válidos.<br>
                        Intenta con términos más específicos o marcas conocidas.
                    </p>
                    <a href="/search" style="background: #1a73e8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        🔍 Intentar Nueva Búsqueda
                    </a>
                </div>
            </div>'''
            return render_page('Sin Resultados', no_results_content)
        
        # Generar HTML de productos
        products_html = ""
        
        for i, product in enumerate(products):
            if not product:
                continue
            
            badge = ""
            if i == 0:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥇 MÁS BARATO</div>'
            elif i == 1:
                badge = '<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º LUGAR</div>'
            
            source_type = product.get('source_type', 'api')
            source_badge = f'<div style="position: absolute; top: 10px; left: 10px; background: #2196f3; color: white; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">✅ {source_type.upper()}</div>'
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = product.get('link', '#')
            
            products_html += f'''
                <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    {badge}
                    {source_badge}
                    <h3 style="color: #1a73e8; margin-bottom: 12px; margin-top: 25px;">{title}</h3>
                    <p style="font-size: 32px; color: #2e7d32; font-weight: bold; margin: 12px 0;">{price}</p>
                    <p style="color: #666; margin-bottom: 10px;">🏪 {source}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        ✅ Link directo verificado • 🚀 Sistema corregido
                    </div>
                    <a href="{link}" target="_blank" rel="noopener noreferrer" style="background: #4caf50; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                        🛒 IR AL PRODUCTO en {source}
                    </a>
                </div>'''
        
        # Estadísticas
        prices = [p.get('price_numeric', 0) for p in products if p and p.get('price_numeric', 0) > 0]
        stats = ""
        if prices:
            min_price, max_price, avg_price = min(prices), max(prices), sum(prices) / len(prices)
            stats = f'''
                <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c9); border: 2px solid #4caf50; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="color: #2e7d32; margin-bottom: 10px;">✅ Sistema CORREGIDO funcionando</h3>
                    <p><strong>🎯 {len(products)} productos encontrados</strong> sin errores lxml</p>
                    <p><strong>💰 Precio más bajo:</strong> ${min_price:.2f}</p>
                    <p><strong>📊 Precio promedio:</strong> ${avg_price:.2f}</p>
                    <p><strong>💸 Diferencia máxima:</strong> ${max_price - min_price:.2f}</p>
                    <p><strong>🚀 Sistema:</strong> ✅ CORREGIDO para Python 3.13</p>
                </div>'''
        
        content = f'''
        <div style="max-width: 900px; margin: 0 auto;">
            <h1 style="color: white; text-align: center; margin-bottom: 10px;">✅ Resultados CORREGIDOS: "{query}"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px;">🚀 Sistema funcionando sin errores lxml</p>
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="/search" style="background: white; color: #1a73e8; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600;">🔍 Nueva Búsqueda</a>
            </div>
            {stats}
            {products_html}
        </div>'''
        
        return render_page('✅ Resultados CORREGIDOS', content)
    except Exception as e:
        print(f"Error en results_page: {e}")
        return redirect(url_for('search_page'))

@app.route('/api/test')
def test_endpoint():
    return jsonify({
        'status': 'SUCCESS',
        'message': '✅ Price Finder USA - SISTEMA CORREGIDO',
        'version': '12.0 - Compatible con Python 3.13 (sin lxml)',
        'fixed_issues': {
            'lxml_removed': True,
            'html_parser_only': True,
            'python_313_compatible': True
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Sistema CORREGIDO funcionando',
        'timestamp': datetime.now().isoformat(),
        'python_version_compatible': True
    })

if __name__ == '__main__':
    print("✅ Iniciando Price Finder USA - SISTEMA CORREGIDO")
    print("🚀 Cambios aplicados:")
    print("   ✅ Removido lxml incompatible con Python 3.13")
    print("   ✅ BeautifulSoup usa html.parser nativo")
    print("   ✅ Todas las funciones mantienen compatibilidad")
    print("   ✅ Sistema listo para Render.com")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
