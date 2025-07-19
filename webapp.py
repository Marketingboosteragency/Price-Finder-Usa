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
app.secret_key = os.environ.get('SECRET_KEY', 'v3-secret-key-super-robust-and-final')

# --- INICIO DE LA CLASE v3.0 - "NIVEL EXPERTO" ---

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
        print(f"\n🧠 INICIANDO BÚSQUEDA EXPERTA v3.0 PARA: '{query}'")
        
        specs = self._extract_specifications(query)
        print(f"📋 Especificaciones extraídas: {specs}")

        smart_queries = self._generate_smart_queries(query, specs)
        print(f"🔍 Queries estratégicos: {smart_queries}")

        all_products = self._fetch_all_products(smart_queries)
        if not all_products:
            print("🆘 La API no devolvió ningún producto.")
            return []
        
        print(f"📊 Total productos brutos: {len(all_products)}")
        unique_products = list({p['link']: p for p in all_products if p.get('link')}.values())
        print(f"📦 Total productos únicos: {len(unique_products)}")
        
        scored_products = self._score_products(unique_products, specs, query)
        print(f"⭐ Productos calificados: {len(scored_products)}")

        # Filtro de relevancia: solo considerar productos con una puntuación positiva
        relevant_products = [p for p in scored_products if p['relevance_score'] > 30]
        print(f"🎯 Productos relevantes (score > 30): {len(relevant_products)}")
        
        if not relevant_products:
            print("🆘 Ningún producto superó el umbral de relevancia.")
            return []

        verified_products = self._verify_links(relevant_products)
        print(f"✅ Productos con enlaces verificados: {len(verified_products)}")
        
        final_products = sorted(verified_products, key=lambda x: x.get('final_score', 0), reverse=True)
        print(f"🏆 BÚSQUEDA COMPLETADA. Devolviendo {len(final_products)} productos.")
        return final_products[:30]

    def _extract_specifications(self, query):
        specs = {}
        q_lower = query.lower()

        # Marcas y Modelos (más inteligente)
        if "iphone" in q_lower:
            specs['brand'] = 'apple'
            # Captura "iphone 15 pro max", "iphone 14 plus", etc.
            model_match = re.search(r'iphone(?:\s?(\d+\s?(?:pro|max|plus|mini|pro\s?max)?))', q_lower)
            if model_match and model_match.group(1):
                specs['model'] = f"iphone {model_match.group(1).strip()}"
        
        # Colores
        colors = ['azul', 'rojo', 'verde', 'negro', 'blanco', 'plata', 'gris', 'titanio', 'morado']
        for color in colors:
            if color in q_lower:
                specs['color'] = color
                break
        
        # Capacidades
        capacity_match = re.search(r'(\d+)\s?(gb|tb)', q_lower)
        if capacity_match:
            specs['capacity'] = f"{capacity_match.group(1)}{capacity_match.group(2)}"
            
        return specs

    def _generate_smart_queries(self, original_query, specs):
        queries = {original_query}
        if specs.get('model'):
            # Consulta "perfecta": Modelo + Color + Capacidad
            perfect_query = specs['model']
            if specs.get('capacity'):
                perfect_query += f" {specs['capacity']}"
            if specs.get('color'):
                perfect_query += f" {specs['color']}"
            queries.add(perfect_query)
            # Consulta amplia: solo el Modelo
            queries.add(specs['model'])
        return list(queries)[:3]

    def _fetch_all_products(self, queries):
        all_products = []
        for q in queries:
            try:
                print(f"🔎 Buscando con: '{q}'")
                params = {
                    'engine': 'google_shopping', 'q': q, 'api_key': self.api_key, 'num': 100,
                    'location': 'Mexico', 'gl': 'mx', 'hl': 'es' # Mercado de México
                }
                response = self.session.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('shopping_results', []):
                    price = self._extract_price(item)
                    if item.get('title') and item.get('link') and price > 0:
                        all_products.append({
                            'title': self._clean_text(item['title']),
                            'price_numeric': price,
                            'price_str': f"${price:,.2f} MXN",
                            'source': self._clean_text(item.get('source', 'Tienda')),
                            'link': item['link'], 'thumbnail': item.get('thumbnail'),
                        })
            except Exception as e:
                print(f"❌ Error buscando '{q}': {e}")
        return all_products

    def _score_products(self, products, specs, original_query):
        scored = []
        query_words = set(original_query.lower().split())

        for product in products:
            title_lower = product['title'].lower()
            score = 0
            
            # 1. Puntuación por Especificaciones
            if specs.get('brand') and specs['brand'] in title_lower: score += 20
            if specs.get('color') and specs['color'] in title_lower: score += 15
            if specs.get('capacity') and specs['capacity'] in title_lower.replace(' ', ''): score += 25
            if specs.get('model'):
                # Comprobar que todas las palabras del modelo estén en el título
                model_words = set(specs['model'].split())
                title_words = set(title_lower.split())
                if model_words.issubset(title_words):
                    score += 50 # Puntuación alta por coincidencia de modelo
            
            # 2. Penalización por "Ruido" (elimina accesorios)
            title_word_set = set(title_lower.split())
            noise_words = title_word_set - query_words
            accessory_words = {'funda', 'mica', 'protector', 'case', 'para', 'compatible', 'con', 'cargador'}
            penalty = 0
            for word in noise_words:
                if word in accessory_words:
                    penalty += 25 # Penalización fuerte
                else:
                    penalty += 1 # Penalización ligera por cada palabra extra
            
            score -= penalty
            
            product['relevance_score'] = score
            product['final_score'] = score / (math.log10(product['price_numeric'] + 1)) if product['price_numeric'] > 0 else score
            scored.append(product)
        return scored

    def _verify_links(self, products):
        verified = []
        # Solo verificar los 15 mejores candidatos para ser rápido
        for product in sorted(products, key=lambda p: p['final_score'], reverse=True)[:15]:
            try:
                response = self.session.head(product['link'], timeout=5, allow_redirects=True)
                if response.status_code < 400:
                    product['verified_link'] = True
                    verified.append(product)
                else:
                    print(f"❌ Enlace Roto ({response.status_code}): {product['link'][:70]}")
            except requests.exceptions.RequestException:
                pass 
        return verified
    
    def _extract_price(self, item):
        price_str = str(item.get('extracted_price') or item.get('price', '0'))
        clean_price = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(clean_price) if clean_price and clean_price != '.' else 0.0
        except ValueError:
            return 0.0
            
    def _clean_text(self, text):
        return html.unescape(str(text)).strip() if text else ""

# --- RUTAS Y PLANTILLAS DE LA APLICACIÓN FLASK ---

def render_page(title, content):
    """Función auxiliar para renderizar el layout básico de la página."""
    return f'''<!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
            h1 {{ text-align: center; color: #1a73e8; }}
            p {{ line-height: 1.6; }}
            input[type="text"], input[type="password"] {{ width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }}
            button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; }}
            button:hover {{ background: #1557b0; }}
            .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
            .loading {{ text-align: center; padding: 40px; display: none; }}
            .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1a73e8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
            a {{ color: #1a73e8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>{content}</body>
    </html>'''

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🧠 Búsqueda Experta v3.0</h1>
        <p>Introduce tu API Key de SerpAPI para comenzar. Este buscador utiliza una lógica avanzada para encontrar exactamente lo que buscas, filtrando accesorios y resultados irrelevantes.</p>
        <form id="setupForm">
            <label for="apiKey">API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu clave de API" required>
            <button type="submit">Activar Buscador</button>
        </form>
        <div id="error" class="error" style="display:none;"></div>
        <div id="loading" class="loading"><div class="spinner"></div><p>Validando API Key...</p></div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            }).then(res => res.json()).then(data => {
                document.getElementById('loading').style.display = 'none';
                if (data.success) {
                    window.location.href = '/search';
                } else {
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Ocurrió un error desconocido.';
                    errorDiv.style.display = 'block';
                }
            }).catch(() => {
                // ... (Manejo de errores)
            });
        });
    </script>
    '''
    return render_page('Configuración del Buscador', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key: return jsonify({'success': False, 'error': 'API key requerida'}), 400
    
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    
    if not test_result.get('valid'):
        return jsonify({'success': False, 'error': test_result.get('message')}), 400
        
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session: return redirect(url_for('index'))
    
    content = '''
    <div class="container">
        <h1>🎯 Realiza una búsqueda</h1>
        <p>Describe el producto que buscas. Sé tan específico como quieras, el sistema se encargará de entenderte.</p>
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Ej: iPhone 15 pro max 256gb titanio azul" required style="margin-bottom: 10px;">
            <button type="submit">Buscar Productos</button>
        </form>
        <div id="loading" class="loading"><div class="spinner"></div><p>Buscando y calificando los mejores productos...</p></div>
        <div id="error" class="error" style="display:none;"></div>
    </div>
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    window.location.href = '/results';
                } else {
                    document.getElementById('loading').style.display = 'none';
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Ocurrió un error al buscar.';
                    errorDiv.style.display = 'block';
                }
            }).catch(() => {
                 // ... (Manejo de errores)
            });
        });
    </script>
    '''
    return render_page('Búsqueda de Productos', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session: return jsonify({'success': False, 'error': 'API key no configurada'}), 401
    
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query: return jsonify({'success': False, 'error': 'La consulta no puede estar vacía'}), 400
    
    try:
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        session['last_search'] = {'query': query, 'products': products}
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR CRÍTICO en /api/search]: {e}")
        return jsonify({'success': False, 'error': f'Ocurrió un error inesperado en el servidor: {e}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session.get('last_search', {})
    query = html.escape(search_data.get('query', ''))
    products = search_data.get('products', [])

    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>Resultados para "{query}"</h1>
            <h2 style="color: #c62828; margin-top: 20px;">No se encontraron resultados relevantes</h2>
            <p style="margin: 20px 0;">La búsqueda avanzada no encontró productos que coincidieran lo suficiente con tu consulta, o fueron filtrados por ser considerados accesorios.</p>
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:600">Intentar Nueva Búsqueda</a>
        </div>
        '''
        return render_page(f'Sin Resultados para "{query}"', content)

    products_html = ""
    for prod in products:
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 12px; padding: 20px; margin-bottom: 20px; background: white; display: flex; flex-wrap: wrap; gap: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <div style="flex: 0 0 150px; text-align: center;">
                <img src="{prod.get('thumbnail', 'https://via.placeholder.com/150')}" alt="{html.escape(prod['title'])}" style="width: 150px; height: 150px; object-fit: contain; border-radius: 8px;">
            </div>
            <div style="flex: 1; min-width: 300px;">
                <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px;">{prod['title']}</h3>
                <p style="font-size: 28px; color: #2e7d32; font-weight: bold; margin: 0 0 10px 0;">{prod['price_str']}</p>
                <p style="color: #555; margin: 0 0 15px 0; font-weight: 500;">Vendido por: <strong>{prod['source']}</strong></p>
                <a href="{prod['link']}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600;">Ver Producto en {prod['source']}</a>
            </div>
            <div style="flex: 1 1 100%; font-size: 12px; color: #666; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <strong>Puntuación de Relevancia:</strong> {int(prod.get('relevance_score',0))} | 
                <strong>Puntuación Final (Relevancia / Precio):</strong> {prod.get('final_score',0):.2f}
            </div>
        </div>'''

    content = f'''
    <div style="max-width: 900px; margin: 0 auto;">
        <h1 style="color: #333; text-align: center; margin-bottom: 20px;">Resultados para: "{query}"</h1>
        <div style="text-align: center; margin-bottom: 30px;">
            <a href="/search" style="background: white; border: 1px solid #ccc; color: #333; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: 600;">Nueva Búsqueda</a>
        </div>
        {products_html}
    </div>
    '''
    return render_page(f'Resultados para "{query}"', content)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("--- 🧠 BÚSQUEDA EXPERTA v3.0 ---")
    print(f"✅ Servidor listo y escuchando en http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
