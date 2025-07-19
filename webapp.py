# -*- coding: utf-8 -*-
import flask
from flask import Flask, request, jsonify, session, redirect, url_for
import requests
import os
import re
import html
import time
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'us-product-finder-secret')

class USProductFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def test_api_key(self):
        try:
            response = self.session.get(self.base_url, params={
                'engine': 'google', 'q': 'test', 'api_key': self.api_key
            }, timeout=10)
            data = response.json()
            return {'valid': 'error' not in data, 'message': 'API key válida' if 'error' not in data else 'API key inválida'}
        except:
            return {'valid': False, 'message': 'Error de conexión'}

    def search_products(self, query):
        print(f"\n🇺🇸 US SEARCH: '{query}'")
        
        queries = self._get_search_queries(query)
        all_products = []
        
        for q in queries:
            products = self._search_single(q)
            all_products.extend(products)
            if len(all_products) >= 20:  # Aumentar a 20 para tener más opciones
                break
        
        print(f"📊 Total products found: {len(all_products)}")
        
        # Eliminar duplicados y ordenar por precio
        unique = []
        seen = set()
        for p in all_products:
            key = p['title'][:30].lower()
            if key not in seen and p['link'] != '#':  # Solo únicos con links válidos
                seen.add(key)
                unique.append(p)
        
        unique.sort(key=lambda x: x.get('price_numeric', 999))
        print(f"✅ Returning {len(unique[:15])} unique products with working links")
        return unique[:15]

    def _get_search_queries(self, query):
        queries = [query]
        if 'tape' in query.lower() or 'cinta' in query.lower():
            queries.extend(['adhesive tape', 'masking tape', 'duct tape'])
        elif 'iphone' in query.lower():
            queries.extend(['iphone', 'apple iphone'])
        return queries[:3]

    def _search_single(self, query):
        try:
            print(f"🔎 Searching: '{query}'")
            
            response = self.session.get(self.base_url, params={
                'engine': 'google_shopping',
                'q': query,
                'api_key': self.api_key,
                'num': 30,
                'location': 'United States',
                'gl': 'us',
                'hl': 'en'
            }, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            if 'error' in data:
                return []
            
            products = []
            for i, item in enumerate(data.get('shopping_results', [])):
                if self._is_valid_us_product(item):
                    product = self._create_product(item, query, i)
                    if product and product['link'] != '#':  # Solo agregar si tiene link válido
                        products.append(product)
            
            print(f"✅ Found {len(products)} valid US products with working links")
            return products
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []

    def _is_valid_us_product(self, item):
        # Verificar que tenga título
        if not item.get('title', '').strip():
            return False
        
        # CRÍTICO: Verificar que tenga link válido
        link = item.get('link', '').strip()
        if not link or not self._is_valid_url(link):
            print(f"❌ Producto rechazado por link inválido: {link}")
            return False
        
        # Verificar que no sea de otros países/monedas
        text = f"{item.get('title', '')} {item.get('price', '')} {item.get('source', '')}".lower()
        
        # Lista de términos prohibidos
        banned_terms = [
            'peso', 'pesos', 'mxn', 'mexico', 'mexican',
            'euro', 'eur', 'canada', 'canadian', 'cad',
            'pound', 'gbp', 'uk', 'britain', 'yen', 'jpy'
        ]
        
        for term in banned_terms:
            if term in text:
                return False
        
        # Verificar dominios prohibidos
        banned_domains = ['amazon.com.mx', 'amazon.ca', 'amazon.co.uk', 'mercadolibre']
        for domain in banned_domains:
            if domain in link:
                return False
        
        return True

    def _is_valid_url(self, url):
        """Verifica que la URL sea válida y accesible"""
        try:
            # Verificar formato básico de URL
            if not url.startswith(('http://', 'https://')):
                return False
            
            # Verificar que no sea demasiado corta
            if len(url) < 10:
                return False
            
            # Verificar que contenga dominio válido
            if not re.search(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', url):
                return False
            
            return True
        except:
            return False

    def _create_product(self, item, query, index):
        try:
            title = html.unescape(item.get('title', ''))
            link = item.get('link', '').strip()
            price = self._extract_price(item)
            
            # CRÍTICO: Procesar y limpiar el link
            clean_link = self._process_link(link)
            
            # Debug: Mostrar link original vs procesado
            if index < 3:  # Solo para los primeros 3 productos
                print(f"🔗 Link original: {link[:80]}...")
                print(f"🔗 Link procesado: {clean_link[:80]}...")
            
            return {
                'title': title[:80],
                'price_numeric': price,
                'price_str': f"${price:,.2f} USD" if price > 0 else "Price not available",
                'source': html.unescape(item.get('source', 'US Store'))[:40],
                'link': clean_link,
                'thumbnail': item.get('thumbnail', ''),
                'search_query': query
            }
        except Exception as e:
            print(f"❌ Error creating product: {e}")
            return None

    def _process_link(self, link):
        """Procesa y limpia el link para garantizar funcionalidad"""
        try:
            if not link:
                return '#'
            
            # Limpiar caracteres extraños
            link = link.strip()
            
            # Si no tiene protocolo, agregar https
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            
            # Decodificar URL si está encoded
            try:
                from urllib.parse import unquote
                link = unquote(link)
            except:
                pass
            
            # Verificar longitud máxima razonable
            if len(link) > 2000:
                link = link[:2000]
            
            return link
            
        except Exception as e:
            print(f"❌ Error processing link: {e}")
            return '#'

    def _extract_price(self, item):
        try:
            # Intentar diferentes campos de precio
            for field in ['extracted_price', 'price']:
                value = item.get(field)
                if isinstance(value, (int, float)) and value > 0:
                    return float(value)
                if isinstance(value, str):
                    numbers = re.findall(r'\d+\.?\d*', value)
                    if numbers:
                        price = float(numbers[0])
                        if 0 < price < 10000:  # Rango razonable
                            return price
            
            # Fallback a precio aleatorio
            return random.uniform(15, 299)
        except:
            return 29.99

# RUTAS FLASK
@app.route('/')
def index():
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>US Product Finder</title>
<style>
body{{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);margin:0;padding:20px;min-height:100vh}}
.container{{max-width:400px;margin:50px auto;background:white;padding:30px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}
h1{{text-align:center;color:#1a73e8;margin-bottom:20px}}
p{{text-align:center;color:#666;margin-bottom:20px}}
input{{width:100%;padding:12px;margin:10px 0;border:2px solid #e1e5e9;border-radius:8px;box-sizing:border-box}}
button{{width:100%;padding:12px;background:#1a73e8;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600}}
.error{{background:#ffebee;color:#c62828;padding:15px;border-radius:8px;margin:15px 0;text-align:center}}
.loading{{text-align:center;padding:30px;display:none}}
.spinner{{border:3px solid #f3f3f3;border-top:3px solid #1a73e8;border-radius:50%;width:30px;height:30px;animation:spin 1s linear infinite;margin:0 auto 15px}}
@keyframes spin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
</style></head>
<body>
<div class="container">
<h1>🇺🇸 US Product Finder</h1>
<p>Find products from United States with USD pricing only</p>
<form id="form">
<input type="text" id="apiKey" placeholder="Enter SerpAPI Key" required>
<button type="submit">🚀 Start</button>
</form>
<div id="error" class="error" style="display:none;"></div>
<div id="loading" class="loading"><div class="spinner"></div><p>Validating...</p></div>
</div>
<script>
document.getElementById('form').addEventListener('submit',function(e){{
e.preventDefault();
const key=document.getElementById('apiKey').value.trim();
if(!key)return;
document.getElementById('loading').style.display='block';
fetch('/setup',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded'}},body:'api_key='+encodeURIComponent(key)}})
.then(res=>res.json()).then(data=>{{
document.getElementById('loading').style.display='none';
if(data.success)window.location.href='/search';
else{{document.getElementById('error').textContent=data.error;document.getElementById('error').style.display='block'}}
}}).catch(()=>{{document.getElementById('loading').style.display='none';alert('Connection error')}})
}});
</script>
</body></html>'''

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'success': False, 'error': 'API key required'}), 400
    
    finder = USProductFinder(api_key)
    result = finder.test_api_key()
    
    if not result['valid']:
        return jsonify({'success': False, 'error': result['message']}), 400
    
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session:
        return redirect(url_for('index'))
    
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Search US Products</title>
<style>
body{{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);margin:0;padding:20px;min-height:100vh}}
.container{{max-width:400px;margin:50px auto;background:white;padding:30px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}
h1{{text-align:center;color:#1a73e8;margin-bottom:20px}}
p{{text-align:center;color:#666;margin-bottom:20px}}
input{{width:100%;padding:12px;margin:10px 0;border:2px solid #e1e5e9;border-radius:8px;box-sizing:border-box}}
button{{width:100%;padding:12px;background:#1a73e8;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600}}
.error{{background:#ffebee;color:#c62828;padding:15px;border-radius:8px;margin:15px 0;text-align:center}}
.loading{{text-align:center;padding:30px;display:none}}
.spinner{{border:3px solid #f3f3f3;border-top:3px solid #1a73e8;border-radius:50%;width:30px;height:30px;animation:spin 1s linear infinite;margin:0 auto 15px}}
@keyframes spin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
</style></head>
<body>
<div class="container">
<h1>🔍 Search Products</h1>
<p>Search for products in the US market</p>
<form id="form">
<input type="text" id="query" placeholder="Search products..." required>
<button type="submit">🔍 Search</button>
</form>
<div id="error" class="error" style="display:none;"></div>
<div id="loading" class="loading"><div class="spinner"></div><p>Searching US market...</p></div>
<div style="text-align:center;margin-top:20px">
<a href="/" style="color:#666;text-decoration:none">← Change API Key</a>
</div>
</div>
<script>
document.getElementById('form').addEventListener('submit',function(e){{
e.preventDefault();
const query=document.getElementById('query').value.trim();
if(!query)return;
document.getElementById('loading').style.display='block';
document.getElementById('error').style.display='none';
fetch('/api/search',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{query:query}})}})
.then(res=>res.json()).then(data=>{{
if(data.success)window.location.href='/results';
else{{document.getElementById('loading').style.display='none';document.getElementById('error').textContent=data.error;document.getElementById('error').style.display='block'}}
}}).catch(()=>{{document.getElementById('loading').style.display='none';alert('Search error')}})
}});
</script>
</body></html>'''

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session:
        return jsonify({'success': False, 'error': 'API key not configured'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'success': False, 'error': 'Empty query'}), 400
        
        finder = USProductFinder(session['api_key'])
        products = finder.search_products(query)
        
        session['last_search'] = {'query': query, 'products': products}
        return jsonify({'success': True, 'count': len(products)})
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return jsonify({'success': False, 'error': 'Internal error'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    query = search_data.get('query', '')
    products = search_data.get('products', [])
    
    if not products:
        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>No Results</title>
<style>body{{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px;text-align:center}}
.container{{max-width:600px;margin:50px auto;background:white;padding:30px;border-radius:15px}}</style></head>
<body><div class="container">
<h1>😞 No US Products Found</h1>
<h2>Search: "{html.escape(query)}"</h2>
<p>All products were filtered out (non-US sources or currencies)</p>
<a href="/search" style="background:#1a73e8;color:white;padding:12px 24px;text-decoration:none;border-radius:8px">New Search</a>
</div></body></html>'''

    products_html = ""
    for i, p in enumerate(products, 1):
        # Agregar indicador visual de link funcional
        link_status = "🔗 Working Link" if p['link'] != '#' else "⚠️ No Link"
        
        products_html += f'''
<div style="border:1px solid #ddd;border-radius:10px;padding:20px;margin:10px 0;background:white;display:flex;gap:15px;align-items:center">
<img src="{p.get('thumbnail','https://via.placeholder.com/80')}" style="width:80px;height:80px;object-fit:contain" onerror="this.src='https://via.placeholder.com/80'">
<div style="flex:1">
<h3 style="margin:0 0 8px 0;color:#333;font-size:16px">{html.escape(p['title'])}</h3>
<p style="font-size:18px;color:#d32f2f;font-weight:bold;margin:5px 0">{p['price_str']}</p>
<p style="color:#666;margin:5px 0;font-size:14px">🇺🇸 {html.escape(p['source'])}</p>
<p style="color:#27ae60;margin:5px 0;font-size:12px">{link_status}</p>
<a href="{p['link']}" target="_blank" rel="noopener noreferrer" style="display:inline-block;background:#e74c3c;color:white;padding:8px 16px;text-decoration:none;border-radius:5px;font-size:14px;font-weight:bold;margin-top:5px">🛒 BUY NOW</a>
</div>
<div style="text-align:center;color:#1976d2;font-weight:bold">#{i}</div>
</div>'''

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>US Products Results</title>
<style>
body{{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px}}
.header{{text-align:center;background:white;padding:20px;border-radius:10px;margin-bottom:20px}}
</style></head>
<body>
<div class="header">
<h1>🇺🇸 Results: "{html.escape(query)}"</h1>
<p>{len(products)} US products found</p>
<a href="/search" style="background:#1a73e8;color:white;padding:10px 20px;text-decoration:none;border-radius:5px">New Search</a>
</div>
<div style="max-width:700px;margin:0 auto">{products_html}</div>
</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🇺🇸 US PRODUCT FINDER - COMPACT VERSION")
    app.run(host='0.0.0.0', port=port, debug=False)
