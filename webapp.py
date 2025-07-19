from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus
import json
import time

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

class UltimatePriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        
        # APIs adicionales para retailers especializados
        self.scraperapi_key = os.environ.get('SCRAPERAPI_KEY', '')  # API gratuita 5000 requests/mes
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY', '')      # API gratuita 100 requests/mes
        
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
        
        # 2. RapidAPI Shopping (incluye retailers especializados)
        if self.rapidapi_key and len(all_products) < 20:
            try:
                print("🛒 Buscando en RapidAPI Shopping...")
                rapidapi_products = self._search_rapidapi_shopping(query)
                all_products.extend(rapidapi_products)
                print(f"✅ RapidAPI Shopping: {len(rapidapi_products)} productos")
            except Exception as e:
                print(f"❌ Error RapidAPI: {e}")
        
        # 3. ScraperAPI para sitios especializados (como lumberliquidators)
        if self.scraperapi_key and len(all_products) < 15:
            try:
                print("🕷️ Scraping sitios especializados...")
                scraped_specialized = self._scrape_specialized_stores(query)
                all_products.extend(scraped_specialized)
                print(f"✅ Sitios especializados: {len(scraped_specialized)} productos")
            except Exception as e:
                print(f"❌ Error scraping especializado: {e}")
        
        # 4. Scraping directo básico
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
            # Filtrar solo productos con links reales
            real_products = [p for p in all_products if p and self._is_real_product_link(p.get('link', ''))]
            print(f"✅ Productos con links reales: {len(real_products)}")
            
            if real_products:
                unique_products = self._remove_duplicates(real_products)
                sorted_products = sorted(unique_products, key=lambda x: x.get('price_numeric', 999))
                print(f"🎯 Productos únicos ordenados: {len(sorted_products)}")
                return sorted_products[:30]  # Más resultados
        
        print("❌ No se encontraron productos reales")
        return []
    
    def _search_rapidapi_shopping(self, query):
        """RapidAPI Shopping - incluye retailers especializados como lumberliquidators"""
        if not self.rapidapi_key:
            return []
        
        products = []
        
        # API 1: Real-Time Shopping API
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
            print(f"Error RapidAPI Real-Time: {e}")
        
        # API 2: Shopping API (incluye más retailers)
        try:
            url = "https://shopping-api2.p.rapidapi.com/search"
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "shopping-api2.p.rapidapi.com"
            }
            params = {
                "query": query,
                "country": "US",
                "min_price": "0",
                "max_price": "1000",
                "sort": "price_asc"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json() if response else None
            
            if data and 'products' in data:
                for item in data['products'][:10]:
                    product = self._process_rapidapi_item(item)
                    if product:
                        products.append(product)
                        
        except Exception as e:
            print(f"Error RapidAPI Shopping: {e}")
        
        return products
    
    def _scrape_specialized_stores(self, query):
        """Scraping de tiendas especializadas usando ScraperAPI"""
        if not self.scraperapi_key:
            return []
        
        products = []
        
        # Tiendas especializadas en liquidación/descuentos
        specialized_stores = [
            {
                'name': 'LumberLiquidators',
                'search_url': f'https://lumberliquidators.com/search?q={quote_plus(query)}',
                'base_url': 'https://lumberliquidators.com'
            },
            {
                'name': 'Liquidation.com',
                'search_url': f'https://liquidation.com/search?q={quote_plus(query)}',
                'base_url': 'https://liquidation.com'
            },
            {
                'name': 'Overstock',
                'search_url': f'https://overstock.com/search?keywords={quote_plus(query)}',
                'base_url': 'https://overstock.com'
            },
            {
                'name': 'Woot',
                'search_url': f'https://woot.com/search?query={quote_plus(query)}',
                'base_url': 'https://woot.com'
            }
        ]
        
        for store in specialized_stores[:2]:  # Limitar para no agotar API
            try:
                store_products = self._scrape_with_scraperapi(store, query)
                products.extend(store_products)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"Error scraping {store['name']}: {e}")
                continue
        
        return products
    
    def _scrape_with_scraperapi(self, store, query):
        """Scraping usando ScraperAPI (bypass automático)"""
        products = []
        
        try:
            # ScraperAPI con JavaScript rendering
            scraperapi_url = "http://api.scraperapi.com"
            params = {
                'api_key': self.scraperapi_key,
                'url': store['search_url'],
                'render': 'true',  # JavaScript rendering
                'country_code': 'us'
            }
            
            response = requests.get(scraperapi_url, params=params, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Selectores genéricos para productos
                product_selectors = [
                    '.product-item', '.product-card', '.product', '.item',
                    '[data-product]', '[data-item]', '.search-result'
                ]
                
                items = []
                for selector in product_selectors:
                    items = soup.select(selector)
                    if items:
                        break
                
                for item in items[:8]:  # Limitar items
                    try:
                        product = self._extract_from_scraperapi_element(item, store)
                        if product and self._is_real_product_link(product['link']):
                            products.append(product)
                    except:
                        continue
            
        except Exception as e:
            print(f"Error ScraperAPI para {store['name']}: {e}")
        
        return products
    
    def _extract_from_scraperapi_element(self, element, store):
        """Extrae datos de elemento HTML de ScraperAPI"""
        try:
            # Título - múltiples selectores
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
            
            # Precio - usar price-parser si está disponible
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
            
            # Link
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
    
    def _process_rapidapi_item(self, item):
        """Procesa items de RapidAPI"""
        try:
            # Diferentes estructuras según la API
            title = item.get('title') or item.get('product_title') or item.get('name', '')
            if not title or len(title) < 5:
                return None
            
            # Precio
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
            
            # Link
            link = item.get('product_url') or item.get('url') or item.get('link', '')
            if not self._is_real_product_link(link):
                return None
            
            # Fuente
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
    
    def _search_serpapi_shopping(self, query):
        """Búsqueda mejorada en Google Shopping con términos especializados"""
        products = []
        
        # Consultas optimizadas para encontrar retailers especializados
        search_queries = [
            query,
            f"{query} liquidator clearance",
            f"{query} discount outlet",
            f"{query} wholesale bulk",
            f"{query} cheap sale"
        ]
        
        for search_query in search_queries[:3]:
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
                    'safe': 'active',
                    'no_cache': 'true'  # Resultados frescos
                }
                
                response = requests.get(self.base_url, params=params, timeout=15)
                data = response.json() if response else None
                
                if data and 'shopping_results' in data:
                    for item in data['shopping_results']:
                        product = self._process_shopping_item(item)
                        if product:
                            products.append(product)
                
                if len(products) >= 25:
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
    
    def _scrape_basic_stores(self, query):
        """Scraping básico con CloudScraper"""
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
                soup = BeautifulSoup(response.content, 'lxml')
                
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
        """Validación mejorada de links reales"""
        if not link:
            return False
        
        try:
            link_lower = str(link).lower()
            
            # Rechazar búsquedas
            search_indicators = [
                '/search?', '/s?k=', '/sch/', '?q=', 'search=', 
                '/search/', 'query=', '_nkw=', 'searchterm=',
                'google.com/search', 'bing.com/search'
            ]
            
            if any(indicator in link_lower for indicator in search_indicators):
                return False
            
            # Patrones de productos válidos (incluyendo retailers especializados)
            product_patterns = [
                r'/dp/[A-Z0-9]+',           # Amazon
                r'/itm/\d+',                # eBay
                r'/ip/\d+',                 # Walmart
                r'/p/\d+',                  # Target/eBay
                r'/product/',               # Generic
                r'/products/',              # Shopify (lumberliquidators usa esto)
                r'\?variant=\d+',           # Shopify variants
                r'/listing/\d+',            # Etsy
                r'/item/\d+',               # Generic
            ]
            
            has_product_pattern = any(re.search(pattern, link_lower) for pattern in product_patterns)
            
            # Dominios válidos (incluyendo liquidadores)
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
    finder = UltimatePriceFinder('test')  # Solo para verificar APIs
    
    content = f'''
    <div class="container">
        <h1>🎯 Price Finder USA - ULTIMATE</h1>
        <p class="subtitle">🚀 Todas las fuentes + APIs especializadas</p>
        
        <div class="api-status">
            <strong>🔌 APIs disponibles:</strong><br>
            SerpAPI: ✅ (principal)<br>
            Librerías Enhanced: {'✅' if HAS_ENHANCED else '❌'}<br>
            ScraperAPI: {'✅' if finder.scraperapi_key else '❌ (opcional)'}<br>
            RapidAPI Shopping: {'✅' if finder.rapidapi_key else '❌ (opcional)'}
        </div>
        
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">🎯 Activar ULTIMATE Search</button>
        </form>
        
        <div class="features">
            <h3>🎯 Fuentes ULTIMATE (incluye lumberliquidators.com):</h3>
            <ul>
                <li>Google Shopping + Bing Shopping (SerpAPI)</li>
                <li>RapidAPI Shopping - retailers especializados {'✅' if finder.rapidapi_key else '❌'}</li>
                <li>ScraperAPI - sitios de liquidación {'✅' if finder.scraperapi_key else '❌'}</li>
                <li>Scraping directo eBay, Walmart {'✅' if HAS_ENHANCED else '❌'}</li>
                <li>Liquidadores: LumberLiquidators, Overstock, Woot</li>
                <li>Validación estricta solo productos reales</li>
            </ul>
            
            <div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px;">
                <strong>💡 Para APIs opcionales (gratuitas):</strong><br>
                • ScraperAPI: <a href="https://scraperapi.com" target="_blank">5000 requests gratis/mes</a><br>
                • RapidAPI: <a href="https://rapidapi.com" target="_blank">100+ requests gratis/mes</a><br>
                Variables de entorno: SCRAPERAPI_KEY, RAPIDAPI_KEY
            </div>
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
    return render_page('🎯 Price Finder USA - ULTIMATE', content)

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
        <h1>🔍 Búsqueda ULTIMATE</h1>
        <p class="subtitle">🎯 Todas las fuentes activas para mejores resultados</p>
        
        <div class="api-status">
            <strong>🚀 Fuentes activas:</strong><br>
            Google Shopping ✅ | Bing Shopping ✅ | 
            ScraperAPI {'✅' if finder.scraperapi_key else '❌'} | 
            RapidAPI {'✅' if finder.rapidapi_key else '❌'} | 
            Scraping directo {'✅' if HAS_ENHANCED else '❌'}
        </div>
        
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Ej: blue painters tape, cinta adhesiva azul..." required>
                <button type="submit">🎯 ULTIMATE Search</button>
            </div>
        </form>
        
        <div class="tips">
            <h4>🎯 ULTIMATE Search incluye:</h4>
            <ul style="margin: 10px 0 0 20px;">
                <li><strong>Liquidadores:</strong> LumberLiquidators, Overstock, Woot</li>
                <li><strong>APIs múltiples:</strong> Google, Bing, RapidAPI Shopping</li>
                <li><strong>Scraping especializado:</strong> ScraperAPI con JS rendering</li>
                <li><strong>Retailers tradicionales:</strong> Amazon, eBay, Walmart</li>
                <li><strong>Solo productos reales:</strong> Links directos verificados</li>
            </ul>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <h3>🎯 ULTIMATE Search en progreso...</h3>
            <p>Analizando TODAS las fuentes disponibles...</p>
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
    return render_page('🔍 ULTIMATE Search - Price Finder USA', content)

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
                'error': 'No se encontraron productos reales. El sistema ULTIMATE analizó todas las fuentes disponibles.',
                'suggestion': 'Intenta con: términos más específicos, marcas conocidas, o palabras en inglés'
            })
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'ultimate_mode': True,
            'sources_available': {
                'scraperapi': bool(price_finder.scraperapi_key),
                'rapidapi': bool(price_finder.rapidapi_key),
                'enhanced': HAS_ENHANCED
            }
        }
        
        return jsonify({
            'success': True, 
            'products': products, 
            'total': len(products),
            'ultimate_mode': True,
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
        ultimate_mode = search_data.get('ultimate_mode', False)
        
        if not products:
            no_results_content = f'''
            <div style="max-width: 900px; margin: 0 auto;">
                <h1 style="color: white; text-align: center; margin-bottom: 10px;">❌ Sin resultados ULTIMATE para: "{query}"</h1>
                <div style="background: white; padding: 40px; border-radius: 15px; text-align: center;">
                    <h3 style="color: #666; margin-bottom: 20px;">Sistema ULTIMATE analizó todas las fuentes</h3>
                    <p style="color: #888; margin-bottom: 30px;">
                        Se analizaron Google Shopping, Bing, APIs especializadas y scraping directo.<br>
                        No se encontraron productos con links directos válidos.
                    </p>
                    <a href="/search" style="background: #1a73e8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                        🔍 Intentar Nueva Búsqueda ULTIMATE
                    </a>
                </div>
            </div>'''
            return render_page('Sin Resultados ULTIMATE', no_results_content)
        
        # Generar HTML con indicadores de fuente
        products_html = ""
        
        source_colors = {
            'scraperapi': '#e91e63',      # Rosa - ScraperAPI
            'rapidapi': '#ff9800',        # Naranja - RapidAPI  
            'shopping_api': '#2196f3',    # Azul - Shopping APIs
            'basic_scraping': '#4caf50',  # Verde - Scraping básico
            'api': '#9c27b0'              # Morado - SerpAPI
        }
        
        source_names = {
            'scraperapi': '🕷️ SCRAPER',
            'rapidapi': '🛒 RAPID',
            'shopping_api': '📡 SHOP',
            'basic_scraping': '🕸️ BASIC',
            'api': '📡 SERP'
        }
        
        for i, product in enumerate(products):
            if not product:
                continue
            
            # Badge de posición
            position_badge = ""
            if i == 0:
                position_badge = '<div style="position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥇 MÁS BARATO</div>'
            elif i == 1:
                position_badge = '<div style="position: absolute; top: 10px; right: 10px; background: #ff9800; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º LUGAR</div>'
            elif i == 2:
                position_badge = '<div style="position: absolute; top: 10px; right: 10px; background: #9c27b0; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥉 3º LUGAR</div>'
            
            # Badge de fuente
            source_type = product.get('source_type', 'api')
            source_color = source_colors.get(source_type, '#666')
            source_name = source_names.get(source_type, '📡 API')
            
            source_badge = f'<div style="position: absolute; top: 10px; left: 10px; background: {source_color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{source_name}</div>'
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = product.get('link', '#')
            rating = html.escape(str(product.get('rating', '')))
            reviews = html.escape(str(product.get('reviews', '')))
            
            rating_html = f"⭐ {rating}" if rating else ""
            reviews_html = f"📝 {reviews} reseñas" if reviews else ""
            
            # Destacar si es de liquidadores
            is_liquidator = any(liq in source.lower() for liq in ['liquidator', 'lumber', 'clearance', 'outlet', 'woot', 'overstock'])
            card_border = "border: 2px solid #e91e63;" if is_liquidator else "border: 1px solid #ddd;"
            
            products_html += f'''
                <div style="{card_border} border-radius: 10px; padding: 20px; margin-bottom: 20px; background: white; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    {position_badge}
                    {source_badge}
                    <h3 style="color: #1a73e8; margin-bottom: 12px; margin-top: 25px;">{title}</h3>
                    <p style="font-size: 32px; color: {'#e91e63' if is_liquidator else '#2e7d32'}; font-weight: bold; margin: 12px 0;">{price}</p>
                    <p style="color: #666; margin-bottom: 10px;">🏪 {source} {'🔥' if is_liquidator else ''}</p>
                    <div style="color: #888; font-size: 14px; margin-bottom: 15px;">
                        {rating_html} {reviews_html} {" • " if rating_html and reviews_html else ""} ✅ Link directo verificado
                    </div>
                    <a href="{link}" target="_blank" rel="noopener noreferrer" style="background: {'#e91e63' if is_liquidator else '#4caf50'}; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                        🛒 IR AL PRODUCTO en {source}
                    </a>
                </div>'''
        
        # Estadísticas ULTIMATE
        prices = [p.get('price_numeric', 0) for p in products if p and p.get('price_numeric', 0) > 0]
        source_types = {}
        liquidator_count = 0
        
        for p in products:
            if p:
                source_type = p.get('source_type', 'api')
                source_types[source_type] = source_types.get(source_type, 0) + 1
                
                source_name = p.get('source', '').lower()
                if any(liq in source_name for liq in ['liquidator', 'lumber', 'clearance', 'outlet', 'woot', 'overstock']):
                    liquidator_count += 1
        
        sources_summary = " + ".join([f"{count} {stype.upper()}" for stype, count in source_types.items()])
        
        stats = ""
        if prices:
            min_price, max_price, avg_price = min(prices), max(prices), sum(prices) / len(prices)
            stats = f'''
                <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c9); border: 2px solid #4caf50; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                    <h3 style="color: #2e7d32; margin-bottom: 10px;">🎯 Resultados ULTIMATE encontrados</h3>
                    <p><strong>🚀 {len(products)} productos de múltiples fuentes:</strong> {sources_summary}</p>
                    <p><strong>🔥 Liquidadores encontrados:</strong> {liquidator_count} productos</p>
                    <p><strong>💰 Precio más bajo:</strong> ${min_price:.2f}</p>
                    <p><strong>📊 Precio promedio:</strong> ${avg_price:.2f}</p>
                    <p><strong>💸 Diferencia máxima:</strong> ${max_price - min_price:.2f}</p>
                    <p><strong>🎯 Sistema ULTIMATE:</strong> ✅ ACTIVO</p>
                </div>'''
        
        content = f'''
        <div style="max-width: 900px; margin: 0 auto;">
            <h1 style="color: white; text-align: center; margin-bottom: 10px;">🎯 Resultados ULTIMATE: "{query}"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 30px;">🚀 Todas las fuentes + APIs especializadas</p>
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="/search" style="background: white; color: #1a73e8; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: 600;">🔍 Nueva Búsqueda ULTIMATE</a>
            </div>
            {stats}
            {products_html}
        </div>'''
        
        return render_page('🎯 Resultados ULTIMATE - Price Finder', content)
    except Exception as e:
        print(f"Error en results_page: {e}")
        return redirect(url_for('search_page'))

@app.route('/api/test')
def test_endpoint():
    finder = UltimatePriceFinder('test')
    return jsonify({
        'status': 'SUCCESS',
        'message': '🎯 Price Finder USA - ULTIMATE MODE',
        'version': '11.0 - Todas las fuentes + APIs especializadas',
        'apis_available': {
            'serpapi': True,
            'scraperapi': bool(finder.scraperapi_key),
            'rapidapi': bool(finder.rapidapi_key),
            'enhanced_libraries': HAS_ENHANCED
        },
        'retailers_covered': [
            'Amazon', 'eBay', 'Walmart', 'Target', 'BestBuy',
            'LumberLiquidators', 'Overstock', 'Woot', 'Liquidation.com'
        ]
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Sistema ULTIMATE funcionando',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🎯 Iniciando Price Finder USA - ULTIMATE MODE")
    print("🚀 Fuentes disponibles:")
    print("   ✅ SerpAPI (Google + Bing Shopping)")
    print(f"   {'✅' if HAS_ENHANCED else '❌'} Enhanced Libraries (BeautifulSoup, CloudScraper)")
    print(f"   {'✅' if os.environ.get('SCRAPERAPI_KEY') else '❌'} ScraperAPI (LumberLiquidators, etc.)")
    print(f"   {'✅' if os.environ.get('RAPIDAPI_KEY') else '❌'} RapidAPI Shopping")
    
    if not HAS_ENHANCED:
        print("💡 Para librerías enhanced: pip install beautifulsoup4 cloudscraper fake-useragent price-parser lxml")
    
    if not os.environ.get('SCRAPERAPI_KEY'):
        print("💡 Para ScraperAPI (encuentra lumberliquidators): export SCRAPERAPI_KEY=tu_key")
        
    if not os.environ.get('RAPIDAPI_KEY'):
        print("💡 Para RapidAPI Shopping: export RAPIDAPI_KEY=tu_key")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
