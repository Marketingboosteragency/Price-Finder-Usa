from flask import Flask, request, jsonify, session, redirect, url_for
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

# HTML Templates embebidos
INDEX_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇺🇸 Price Finder USA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .setup-card { 
            background: white; border-radius: 16px; padding: 40px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 600px; margin: 0 auto;
        }
        .input-group { margin-bottom: 20px; }
        .input-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #374151; }
        .input-group input { 
            width: 100%; padding: 16px; border: 2px solid #e5e7eb; border-radius: 12px; 
            font-size: 16px; transition: all 0.3s ease;
        }
        .input-group input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        .btn { 
            background: #3b82f6; color: white; border: none; padding: 16px 24px; 
            border-radius: 12px; cursor: pointer; font-size: 16px; font-weight: 600; 
            transition: all 0.3s ease; text-decoration: none; display: inline-block;
        }
        .btn:hover { background: #2563eb; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3); }
        .features { background: #f0f9ff; padding: 25px; border-radius: 12px; border-left: 4px solid #3b82f6; margin-top: 20px; }
        .error { background: #fef2f2; border: 2px solid #fecaca; color: #991b1b; padding: 20px; border-radius: 12px; margin: 20px 0; }
        .hidden { display: none !important; }
        .loading { text-align: center; padding: 20px; }
        .spinner { width: 30px; height: 30px; border: 3px solid #e5e7eb; border-left: 3px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🇺🇸 Price Finder USA</h1>
            <p>Encuentra los mejores precios solo en vendedores de EE.UU.</p>
        </div>

        <div class="setup-card" id="setupCard">
            <h2>¡Bienvenido! 🚀</h2>
            <p>Para comenzar necesitas una API key gratuita de SerpAPI.</p>
            
            <form id="setupForm">
                <div class="input-group">
                    <label for="apiKey">API Key de SerpAPI:</label>
                    <input type="text" id="apiKey" name="api_key" placeholder="Pega aquí tu API key..." required>
                </div>
                
                <div style="text-align: center; margin: 20px 0;">
                    <a href="https://serpapi.com/" target="_blank" style="color: #3b82f6;">
                        📝 ¿No tienes API key? Obtén una gratis aquí →
                    </a>
                </div>
                
                <button type="submit" class="btn">✅ Configurar y Continuar</button>
            </form>

            <div class="features">
                <h3>🛡️ Características principales:</h3>
                <ul style="list-style: none; padding-left: 0;">
                    <li>✅ Solo vendedores verificados de EE.UU.</li>
                    <li>❌ Filtra automáticamente sitios chinos</li>
                    <li>🔗 Links de compra directa verificados</li>
                    <li>💰 Encuentra las mejores ofertas</li>
                </ul>
            </div>
        </div>

        <div id="loading" class="loading hidden">
            <div class="spinner"></div>
            <p>Configurando API key...</p>
        </div>

        <div id="error" class="error hidden"></div>
    </div>

    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const apiKey = formData.get('api_key').trim();
            
            if (!apiKey) {
                showError('Por favor ingresa tu API key');
                return;
            }
            
            showLoading();
            
            fetch('/setup', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    showError(data.error || 'Error al configurar API key');
                }
            })
            .catch(error => {
                showError('Error de conexión: ' + error.message);
            });
        });

        function showLoading() {
            document.getElementById('setupCard').style.display = 'none';
            document.getElementById('loading').classList.remove('hidden');
        }

        function showError(message) {
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('setupCard').style.display = 'block';
            
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
            
            setTimeout(() => {
                errorDiv.classList.add('hidden');
            }, 5000);
        }
    </script>
</body>
</html>
"""

SEARCH_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Búsqueda - Price Finder USA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .search-card { 
            background: white; border-radius: 16px; padding: 40px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 600px; margin: 0 auto;
        }
        .search-bar { display: flex; gap: 12px; margin-bottom: 20px; }
        .search-bar input { 
            flex: 1; padding: 16px; border: 2px solid #e5e7eb; border-radius: 12px; 
            font-size: 16px; transition: all 0.3s ease;
        }
        .btn { 
            background: #3b82f6; color: white; border: none; padding: 16px 24px; 
            border-radius: 12px; cursor: pointer; font-size: 16px; font-weight: 600; 
        }
        .btn:hover { background: #2563eb; transform: translateY(-2px); }
        .loading { text-align: center; padding: 40px; background: white; border-radius: 16px; margin: 20px 0; }
        .spinner { width: 50px; height: 50px; border: 5px solid #e5e7eb; border-left: 5px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .hidden { display: none !important; }
        .error { background: #fef2f2; border: 2px solid #fecaca; color: #991b1b; padding: 20px; border-radius: 12px; margin: 20px 0; }
        .progress-bar { background: #e5e7eb; border-radius: 10px; margin: 20px 0; height: 8px; }
        .progress-fill { background: #3b82f6; height: 100%; border-radius: 10px; transition: width 0.5s ease; width: 0%; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Buscar Productos</h1>
            <p>Encuentra los mejores precios en tiendas de EE.UU.</p>
        </div>

        <div class="search-card" id="searchCard">
            <form id="searchForm">
                <div class="search-bar">
                    <input type="text" id="searchQuery" placeholder="¿Qué producto buscas? Ej: iPhone 15, Samsung TV..." required>
                    <button type="submit" class="btn">🚀 Buscar</button>
                </div>
            </form>

            <p style="text-align: center; color: #6b7280;">
                🏪 Buscaremos en: Amazon, Walmart y más tiendas de EE.UU.<br>
                ⏱️ La búsqueda puede tomar 1-2 minutos.
            </p>
        </div>

        <div id="searchLoading" class="loading hidden">
            <div class="spinner"></div>
            <h3>🔍 Buscando mejores precios...</h3>
            <p id="loadingMessage">Iniciando búsqueda...</p>
            
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p id="progressText">0% completado</p>

            <button type="button" class="btn" style="background: #6b7280; margin-top: 20px;" onclick="cancelSearch()">
                ❌ Cancelar búsqueda
            </button>
        </div>

        <div id="searchError" class="error hidden"></div>
    </div>

    <script>
        let searchInProgress = false;

        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if (searchInProgress) return;

            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;

            startSearch(query);
        });

        function startSearch(query) {
            searchInProgress = true;
            document.getElementById('searchCard').style.display = 'none';
            document.getElementById('searchLoading').classList.remove('hidden');
            
            simulateProgress();

            fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    showError(data.error || 'Error en la búsqueda');
                }
            })
            .catch(error => {
                showError('Error de conexión: ' + error.message);
            });
        }

        function simulateProgress() {
            const messages = [
                'Buscando en Google Shopping...',
                'Consultando Walmart...',
                'Validando vendedores de EE.UU...',
                'Organizando resultados...'
            ];

            let currentStep = 0;
            let progress = 0;

            const interval = setInterval(() => {
                progress += Math.random() * 15 + 5;
                if (progress > 95) progress = 95;

                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressText').textContent = Math.round(progress) + '% completado';

                if (currentStep < messages.length) {
                    document.getElementById('loadingMessage').textContent = messages[currentStep];
                    currentStep++;
                }

                if (progress >= 95) {
                    clearInterval(interval);
                }
            }, 800);
        }

        function showError(message) {
            searchInProgress = false;
            document.getElementById('searchLoading').classList.add('hidden');
            document.getElementById('searchCard').style.display = 'block';
            
            const errorDiv = document.getElementById('searchError');
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }

        function cancelSearch() {
            searchInProgress = false;
            document.getElementById('searchLoading').classList.add('hidden');
            document.getElementById('searchCard').style.display = 'block';
        }
    </script>
</body>
</html>
"""

# Rutas Flask
@app.route('/')
def index():
    return INDEX_HTML

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
    return SEARCH_HTML

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
    products = search_data['products']
    
    # Crear HTML de resultados dinámicamente
    products_html = ""
    if products:
        for product in products:
            title = product['title'][:80] + ("..." if len(product['title']) > 80 else "")
            price = f"${product['price_numeric']:.2f}"
            source = product['source']
            link = product['link']
            rating = product.get('rating', '')
            reviews = product.get('reviews', '')
            
            products_html += f"""
                <div class="product-card">
                    <div class="verified-badge">🇺🇸 Verificado</div>
                    <div class="product-title">{title}</div>
                    <div class="product-price">{price}</div>
                    <div class="product-source">{source}</div>
                    <div style="color: #6b7280; margin-bottom: 15px;">
                        {f'⭐ {rating}' if rating else ''} 
                        {f'📝 {reviews} reseñas' if reviews and reviews != 'None' else ''}
                        🚚 Envío a EE.UU.
                    </div>
                    <a href="{link}" target="_blank" class="btn">🛒 Ver en {source}</a>
                    <p style="font-size: 12px; color: #059669; margin-top: 8px;">Link verificado ✅</p>
                </div>
            """
    else:
        products_html = """
            <div style="background: white; padding: 40px; border-radius: 16px; text-align: center;">
                <h3>😔 No se encontraron productos</h3>
                <p style="margin: 15px 0; color: #6b7280;">No se encontraron productos válidos de vendedores de EE.UU.</p>
                <a href="/search" class="btn">🔍 Intentar Nueva Búsqueda</a>
            </div>
        """
    
    results_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultados - Price Finder USA</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; color: #333;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: white; }}
            .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
            .results-summary {{ 
                background: #f0fdf4; border: 2px solid #bbf7d0; border-radius: 16px; 
                padding: 25px; margin-bottom: 30px; color: #166534;
            }}
            .product-card {{ 
                background: white; border: 2px solid #e5e7eb; border-radius: 16px; 
                padding: 25px; margin-bottom: 20px; position: relative;
                transition: all 0.3s ease;
            }}
            .product-card:hover {{ 
                border-color: #3b82f6; transform: translateY(-2px); 
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }}
            .verified-badge {{ 
                background: #059669; color: white; padding: 6px 12px; border-radius: 20px; 
                font-size: 12px; position: absolute; top: 15px; right: 15px;
            }}
            .product-title {{ font-size: 18px; font-weight: 600; margin-bottom: 12px; color: #1f2937; }}
            .product-price {{ font-size: 28px; font-weight: bold; color: #059669; margin-bottom: 12px; }}
            .product-source {{ 
                background: #3b82f6; color: white; padding: 6px 16px; border-radius: 20px; 
                display: inline-block; font-size: 14px; margin-bottom: 15px;
            }}
            .btn {{ 
                background: #3b82f6; color: white; border: none; padding: 12px 20px; 
                border-radius: 8px; text-decoration: none; font-weight: 600;
                display: inline-block; transition: all 0.3s ease;
            }}
            .btn:hover {{ background: #2563eb; transform: translateY(-2px); }}
            .btn-secondary {{ background: #6b7280; }}
            .btn-secondary:hover {{ background: #4b5563; }}
            .actions {{ display: flex; gap: 15px; justify-content: center; margin-bottom: 30px; flex-wrap: wrap; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Resultados de Búsqueda</h1>
                <p>{search_data['query']} - {len(products)} productos verificados de EE.UU.</p>
            </div>

            {f'''
            <div class="results-summary">
                <h3>✅ Búsqueda Completada</h3>
                <p><strong>{len(products)} productos verificados</strong> de vendedores de EE.UU.</p>
                {f"<p>💰 Rango de precios: ${products[0]['price_numeric']:.2f} - ${products[-1]['price_numeric']:.2f}</p>" if products else ""}
            </div>
            ''' if products else ''}

            <div class="actions">
                <a href="/search" class="btn">🔍 Nueva Búsqueda</a>
                <button onclick="window.print()" class="btn btn-secondary">📄 Imprimir Resultados</button>
            </div>

            {products_html}
        </div>
    </body>
    </html>"""
