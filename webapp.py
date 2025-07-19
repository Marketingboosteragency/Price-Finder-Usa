from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import json
from typing import List, Dict, Optional
import time
from dataclasses import dataclass, asdict
from urllib.parse import quote, urlparse
import re
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

@dataclass
class Product:
    title: str
    price: str
    price_numeric: float
    source: str
    link: str
    rating: Optional[str] = None
    reviews: Optional[str] = None
    is_us_seller: bool = True
    link_verified: bool = False

class USLinkValidator:
    def __init__(self):
        self.blacklisted_domains = {
            'alibaba.com', 'aliexpress.com', 'temu.com', 'dhgate.com',
            'banggood.com', 'gearbest.com', 'lightinthebox.com',
            'wish.com', 'joom.com', 'shein.com'
        }
        
        self.trusted_us_domains = {
            'amazon.com', 'walmart.com', 'target.com', 'bestbuy.com',
            'homedepot.com', 'lowes.com', 'costco.com', 'samsclub.com',
            'lumberliquidators.com', 'llflooring.com', 'harborfreight.com',
            'menards.com', 'acehardware.com', 'tapemanblue.com', 'uline.com'
        }
    
    def is_blacklisted_domain(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            return domain in self.blacklisted_domains
        except Exception:
            return True
    
    def is_trusted_us_domain(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            return domain in self.trusted_us_domains
        except Exception:
            return False
    
    def validate_us_link(self, url: str, product_title: str = "") -> Dict:
        validation_result = {
            'is_valid': False,
            'is_us_seller': False,
            'is_accessible': True,
            'is_trusted_domain': False,
            'reasons': [],
            'warnings': [],
            'final_url': url
        }
        
        if self.is_blacklisted_domain(url):
            validation_result['reasons'].append('Dominio en lista negra')
            return validation_result
        
        if self.is_trusted_us_domain(url):
            validation_result['is_trusted_domain'] = True
            validation_result['is_us_seller'] = True
            validation_result['is_valid'] = True
        
        return validation_result

class PriceFinder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.link_validator = USLinkValidator()
        
    def _validate_and_filter_products(self, products: List[Product]) -> List[Product]:
        valid_products = []
        
        for product in products:
            validation = self.link_validator.validate_us_link(product.link, product.title)
            
            if validation['is_valid'] and validation['is_us_seller']:
                product.is_us_seller = True
                product.link_verified = True
                product.link = validation['final_url']
                valid_products.append(product)
        
        return valid_products
        
    def search_google_shopping(self, query: str, location: str = "United States") -> List[Product]:
        all_products = []
        search_variations = [query, f"{query} cheap", f"{query} sale"]
        
        for search_query in search_variations:
            params = {
                'engine': 'google_shopping',
                'q': search_query,
                'location': location,
                'api_key': self.api_key,
                'num': 50
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if 'shopping_results' in data:
                    for item in data['shopping_results']:
                        try:
                            price_str = item.get('price', '0')
                            price_numeric = self._extract_price(price_str)
                            
                            if price_numeric > 0:
                                product = Product(
                                    title=item.get('title', 'Sin título'),
                                    price=price_str,
                                    price_numeric=price_numeric,
                                    source=item.get('source', 'Desconocido'),
                                    link=item.get('link', ''),
                                    rating=item.get('rating'),
                                    reviews=str(item.get('reviews', '')),
                                    is_us_seller=False,
                                    link_verified=False
                                )
                                all_products.append(product)
                        except Exception:
                            continue
                
                time.sleep(1)
                
            except requests.RequestException:
                continue
        
        return all_products
    
    def search_walmart(self, query: str) -> List[Product]:
        params = {
            'engine': 'walmart',
            'query': query,
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            if 'organic_results' in data:
                for item in data['organic_results']:
                    try:
                        primary_offer = item.get('primary_offer', {})
                        price_str = primary_offer.get('offer_price', '0')
                        price_numeric = self._extract_price(price_str)
                        
                        if price_numeric > 0:
                            product = Product(
                                title=item.get('title', 'Sin título'),
                                price=price_str,
                                price_numeric=price_numeric,
                                source='Walmart',
                                link=item.get('product_page_url', ''),
                                rating=str(item.get('rating', '')),
                                reviews=str(item.get('reviews_count', '')),
                                is_us_seller=True,
                                link_verified=False
                            )
                            products.append(product)
                    except Exception:
                        continue
            
            return products
            
        except requests.RequestException:
            return []
    
    def _extract_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        
        price_str = str(price_str)
        
        price_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*\.\d{2})',
            r'(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, price_str)
            if matches:
                price_clean = matches[0]
                break
        else:
            price_clean = re.sub(r'[^\d.,]', '', price_str)
        
        if not price_clean:
            return 0.0
        
        if ',' in price_clean and '.' in price_clean:
            price_clean = price_clean.replace(',', '')
        elif ',' in price_clean:
            if price_clean.count(',') == 1 and len(price_clean.split(',')[1]) <= 2:
                price_clean = price_clean.replace(',', '.')
            else:
                price_clean = price_clean.replace(',', '')
        
        try:
            price_value = float(price_clean)
            if 0.10 <= price_value <= 50000:
                return price_value
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def find_best_deals(self, query: str, max_results: int = 20) -> List[Product]:
        all_products = []
        
        # Buscar en Google Shopping
        google_products = self.search_google_shopping(query)
        all_products.extend(google_products)
        
        # Buscar en Walmart
        walmart_products = self.search_walmart(query)
        all_products.extend(walmart_products)
        
        # Validar productos
        validated_products = self._validate_and_filter_products(all_products)
        
        # Filtrar duplicados y ordenar por precio
        unique_products = self._remove_duplicates(validated_products)
        sorted_products = sorted(unique_products, key=lambda x: x.price_numeric)
        
        return sorted_products[:max_results]
    
    def _remove_duplicates(self, products: List[Product]) -> List[Product]:
        seen_products = set()
        unique_products = []
        
        for product in products:
            title_normalized = re.sub(r'[^\w\s]', '', product.title.lower())
            title_words = title_normalized.split()[:5]
            
            price_rounded = round(product.price_numeric, 2)
            key = (tuple(title_words), price_rounded, product.source.lower())
            
            if key not in seen_products:
                seen_products.add(key)
                unique_products.append(product)
        
        return unique_products

# Rutas Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'error': 'API key requerida'}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True, 'message': 'API key configurada correctamente'})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    return render_template('search.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'error': 'API key no configurada'}), 400
    
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    
    try:
        price_finder = PriceFinder(session['api_key'])
        products = price_finder.find_best_deals(query)
        
        # Convertir a dict para JSON
        products_dict = [asdict(product) for product in products]
        
        # Guardar en sesión
        session['last_search'] = {
            'query': query,
            'products': products_dict,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'products': products_dict,
            'total': len(products_dict)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error en la búsqueda: {str(e)}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    return render_template('results.html', 
                         query=search_data['query'],
                         products=search_data['products'],
                         total=len(search_data['products']))

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'OK', 'message': 'Price Finder USA está funcionando'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)