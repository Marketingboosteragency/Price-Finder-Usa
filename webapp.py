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
app.secret_key = os.environ.get('SECRET_KEY', 'v4-secret-key-truly-universal')

# --- INICIO DE LA NUEVA CLASE v4.1 - "UNIVERSAL MEJORADA" ---

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
        print(f"\n🧠 INICIANDO BÚSQUEDA UNIVERSAL v4.1 PARA: '{query}'")
        
        specs = self._extract_specifications(query)
        print(f"📋 Especificaciones extraídas: {specs}")

        smart_queries = self._generate_smart_queries(specs, query)
        print(f"🔍 Queries estratégicos: {smart_queries}")

        all_products = self._fetch_all_products(smart_queries)
        if not all_products:
            print("🆘 La API no devolvió ningún producto para ninguna consulta.")
            return []
        
        print(f"📊 Total productos brutos: {len(all_products)}")
        unique_products = list({p['link']: p for p in all_products if p.get('link')}.values())
        print(f"📦 Total productos únicos: {len(unique_products)}")
        
        scored_products = self._score_products(unique_products, specs, query)
        print(f"⭐ Productos calificados: {len(scored_products)}")

        # CAMBIO CRÍTICO: Reducir umbral de relevancia de 25 a 10
        relevant_products = [p for p in scored_products if p['relevance_score'] > 10]
        print(f"🎯 Productos relevantes (score > 10): {len(relevant_products)}")
        
        # FALLBACK: Si no hay productos relevantes, tomar los mejores 10
        if not relevant_products:
            print("🔄 Aplicando fallback: tomando los 10 mejores productos")
            relevant_products = sorted(scored_products, key=lambda x: x.get('relevance_score', 0), reverse=True)[:10]

        verified_products = self._verify_links(relevant_products)
        print(f"✅ Productos con enlaces verificados: {len(verified_products)}")
        
        # FALLBACK 2: Si la verificación elimina todo, devolver sin verificar
        if not verified_products and relevant_products:
            print("🔄 Verificación muy restrictiva, devolviendo productos sin verificar")
            verified_products = relevant_products[:20]
        
        final_products = sorted(verified_products, key=lambda x: x.get('final_score', 0), reverse=True)
        print(f"🏆 BÚSQUEDA COMPLETADA. Devolviendo {len(final_products)} productos.")
        return final_products[:30]

    def _extract_specifications(self, query):
        specs = {}
        q_lower = query.lower()

        # Marcas y Modelos (para productos como iPhones)
        if "iphone" in q_lower:
            specs['brand'] = 'apple'
            model_match = re.search(r'iphone(?:\s?(\d+\s?(?:pro|max|plus|mini|pro\s?max)?))', q_lower)
            if model_match and model_match.group(1):
                specs['model'] = f"iphone {model_match.group(1).strip()}"
        
        # MEJORA: Tipos de producto más amplios y específicos
        product_patterns = [
            (r'cinta\s+adhesiva\s+de\s+papel', 'cinta adhesiva papel'),
            (r'cinta\s+adhesiva', 'cinta adhesiva'),
            (r'cinta\s+de\s+papel', 'cinta papel'),
            (r'tape\s+paper', 'paper tape'),
            (r'masking\s+tape', 'masking tape'),
            (r'cinta', 'cinta'),
            (r'tape', 'tape'),
            (r'tornillo', 'tornillo'),
            (r'martillo', 'martillo'),
        ]
        
        for pattern, product_type in product_patterns:
            if re.search(pattern, q_lower):
                specs['product_type'] = product_type
                break

        # Colores
        colors = ['azul', 'blue', 'rojo', 'red', 'verde', 'green', 'negro', 'black', 'blanco', 'white', 'plata', 'silver', 'gris', 'gray', 'titanio', 'morado', 'purple']
        for color in colors:
            if color in q_lower:
                specs['color'] = color
                break
        
        # Capacidades (para electrónica)
        capacity_match = re.search(r'(\d+)\s?(gb|tb)', q_lower)
        if capacity_match:
            specs['capacity'] = f"{capacity_match.group(1)}{capacity_match.group(2)}"
        
        # MEJORA: Medidas más flexibles
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:pulgadas|pulgada|inch|in|")',
            r'(\d+(?:\.\d+)?)\s*(?:cm|centimetros)',
            r'(\d+(?:\.\d+)?)\s*(?:mm|milimetros)',
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, q_lower)
            if size_match:
                specs['size_val'] = float(size_match.group(1))
                if 'cm' in pattern:
                    specs['size_unit'] = 'cm'
                elif 'mm' in pattern:
                    specs['size_unit'] = 'mm'
                else:
                    specs['size_unit'] = 'in'
                break
            
        return specs

    def _generate_smart_queries(self, specs, original_query):
        queries = set()
        
        # Estrategia 1: Query original siempre
        queries.add(original_query)
        
        # Estrategia 2: Construir desde especificaciones
        if specs.get('product_type'):
            base = specs['product_type']
            query = base
            if specs.get('size_val'): 
                query += f" {specs['size_val']}{specs['size_unit']}"
            if specs.get('color'): 
                query += f" {specs['color']}"
            queries.add(query)
            queries.add(base)  # Búsqueda más amplia
        
        # Estrategia 3: Palabras clave simplificadas
        simple_keywords = re.findall(r'\b\w+\b', original_query.lower())
        if len(simple_keywords) > 2:
            queries.add(' '.join(simple_keywords[:3]))  # Primeras 3 palabras
        
        # Estrategia 4: Variaciones de la query original
        if 'adhesiva de papel' in original_query.lower():
            queries.add('masking tape')
            queries.add('paper tape')
            queries.add('cinta papel')
        
        return list(queries)[:5]  # Aumentar a 5 queries

    def _fetch_all_products(self, queries):
        all_products = []
        for q in queries:
            try:
                print(f"🔎 Buscando con: '{q}'")
                params = {
                    'engine': 'google_shopping', 'q': q, 'api_key': self.api_key, 'num': 100,
                    'location': 'Mexico', 'gl': 'mx', 'hl': 'es'
                }
                response = self.session.get(self.base_url, params=params, timeout=15)
                if response.status_code != 200: 
                    print(f"❌ Status code {response.status_code} para '{q}'")
                    continue
                
                data = response.json()
                if 'error' in data:
                    print(f"❌ Error en API para '{q}': {data.get('error')}")
                    continue
                    
                products_found = 0
                for item in data.get('shopping_results', []):
                    price = self._extract_price(item)
                    if item.get('title') and item.get('link') and price > 0:
                        all_products.append({
                            'title': self._clean_text(item['title']),
                            'price_numeric': price, 
                            'price_str': f"${price:,.2f} MXN",
                            'source': self._clean_text(item.get('source', 'Tienda')),
                            'link': item['link'], 
                            'thumbnail': item.get('thumbnail'),
                            'query_used': q  # Para debug
                        })
                        products_found += 1
                print(f"✅ {products_found} productos encontrados con '{q}'")
                        
            except Exception as e:
                print(f"❌ Error buscando '{q}': {e}")
        return all_products

    def _score_products(self, products, specs, original_query):
        scored = []
        original_words = set(original_query.lower().split())
        
        for product in products:
            title_lower = product['title'].lower()
            score = 10  # CAMBIO: Score base de 10 en lugar de 0
            
            # Puntuación por especificaciones clave
            if specs.get('color') and specs['color'] in title_lower: 
                score += 15
            if specs.get('capacity') and specs['capacity'] in title_lower.replace(' ', ''): 
                score += 20
            if specs.get('model') and all(word in title_lower for word in specs['model'].split()): 
                score += 40
            if specs.get('product_type'):
                # MEJORA: Scoring más flexible para tipos de producto
                product_words = specs['product_type'].split()
                matches = sum(1 for word in product_words if word in title_lower)
                score += matches * 15  # 15 puntos por cada palabra que coincida

            # MEJORA: Puntuación por coincidencia de palabras originales
            title_words = set(title_lower.split())
            word_matches = len(original_words.intersection(title_words))
            score += word_matches * 8  # 8 puntos por palabra coincidente

            # Puntuación por coincidencia de tamaño (más flexible)
            if specs.get('size_val') and self._size_matches(title_lower, specs['size_val']):
                score += 25

            # MEJORA: Penalización reducida por ruido
            noise_words = title_words - original_words
            accessory_words = {'funda', 'mica', 'protector', 'case', 'para', 'compatible', 'con'}
            penalty = sum(5 for word in noise_words if word in accessory_words)  # Reducir penalización
            score -= penalty
            
            # MEJORA: Bonus por fuentes confiables
            reliable_sources = ['amazon', 'mercadolibre', 'liverpool', 'home depot', 'office depot']
            if any(source in product['source'].lower() for source in reliable_sources):
                score += 10
            
            product['relevance_score'] = max(score, 0)  # No permitir scores negativos
            product['final_score'] = score / (math.log10(product['price_numeric'] + 1) + 1)
            scored.append(product)
            
        return scored

    def _size_matches(self, title_lower, target_size):
        # MEJORA: Patrón más amplio para encontrar números con unidades
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:in|inch|"|pulgada|pulgadas)',
            r'(\d+(?:\.\d+)?)\s*(?:cm|centimetro|centimetros)',
            r'(\d+(?:\.\d+)?)\s*(?:mm|milimetro|milimetros)',
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)',  # Para dimensiones como "2x1"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, title_lower)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        # Para patrones con múltiples grupos (como dimensiones)
                        values = [float(v) for v in match if v]
                    else:
                        values = [float(match)]
                    
                    for value in values:
                        # Convertir a pulgadas si es necesario
                        inches_found = value
                        if 'cm' in pattern: 
                            inches_found = value / 2.54
                        elif 'mm' in pattern: 
                            inches_found = value / 25.4
                        
                        # MEJORA: Tolerancia más amplia (25% en lugar de 15%)
                        if abs(inches_found - target_size) < (target_size * 0.25):
                            return True
                except ValueError:
                    continue
        return False

    def _verify_links(self, products):
        verified = []
        # MEJORA: Verificar más productos (30 en lugar de 15)
        for product in sorted(products, key=lambda p: p['final_score'], reverse=True)[:30]:
            try:
                response = self.session.head(product['link'], timeout=3, allow_redirects=True)  # Timeout reducido
                if response.status_code < 400:
                    product['verified_link'] = True
                    verified.append(product)
                else:
                    print(f"⚠️ Link no verificado para {product['title'][:50]}... (Status: {response.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Error verificando link para {product['title'][:50]}...: {e}")
                # En lugar de descartar, agregar sin verificar si tenemos pocos productos
                if len(verified) < 5:
                    product['verified_link'] = False
                    verified.append(product)
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

# --- EL RESTO DE LA APP FLASK SE MANTIENE IGUAL ---

@app.route('/')
def index():
    content = '''
    <div class="container">
        <h1>🧠 Búsqueda Universal v4.1</h1>
        <p>Introduce tu API Key de SerpAPI. Este buscador mejorado entiende medidas, tipos de producto y electrónica para darte siempre el mejor resultado.</p>
        <form id="setupForm"><label for="apiKey">API Key de SerpAPI:</label><input type="text" id="apiKey" placeholder="Pega aquí tu clave de API" required><button type="submit">Activar Buscador</button></form>
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
                if (data.success) { window.location.href = '/search'; }
                else {
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Ocurrió un error.';
                    errorDiv.style.display = 'block';
                }
            }).catch(() => { document.getElementById('loading').style.display = 'none'; });
        });
    </script>
    '''
    return render_page('Configuración del Buscador v4.1', content)

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
        <p>El sistema entenderá tanto "iPhone 15 pro max azul" como "cinta adhesiva de papel azul 2 pulgadas".</p>
        <form id="searchForm">
            <input type="text" id="searchQuery" placeholder="Describe el producto que buscas..." required style="margin-bottom: 10px;">
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
                if (data.success) { window.location.href = '/results'; }
                else {
                    document.getElementById('loading').style.display = 'none';
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = data.error || 'Ocurrió un error al buscar.';
                    errorDiv.style.display = 'block';
                }
            }).catch(() => { document.getElementById('loading').style.display = 'none'; });
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
        return jsonify({'success': False, 'error': f'Ocurrió un error inesperado: {e}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session: return redirect(url_for('search_page'))
    search_data = session.get('last_search', {})
    query = html.escape(search_data.get('query', ''))
    products = search_data.get('products', [])
    if not products:
        content = f'''
        <div class="container" style="text-align: center;">
            <h1>Resultados para "{query}"</h1>
            <h2 style="color: #c62828; margin-top: 20px;">No se encontraron resultados relevantes</h2>
            <p style="margin: 20px 0;">La búsqueda avanzada no encontró productos que coincidieran lo suficiente con tu consulta. Intenta con términos más generales.</p>
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:600">Intentar Nueva Búsqueda</a>
        </div>'''
        return render_page(f'Sin Resultados para "{query}"', content, use_layout=False)

    products_html = ""
    for prod in products:
        verification_badge = "✅ Verificado" if prod.get('verified_link') else "⚠️ No verificado"
        products_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 12px; padding: 20px; margin-bottom: 20px; background: white; display: flex; flex-wrap: wrap; gap: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <div style="flex: 0 0 150px; text-align: center;"><img src="{prod.get('thumbnail', 'https://via.placeholder.com/150')}" alt="{html.escape(prod['title'])}" style="width: 150px; height: 150px; object-fit: contain; border-radius: 8px;"></div>
            <div style="flex: 1; min-width: 300px;">
                <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px;">{prod['title']}</h3>
                <p style="font-size: 28px; color: #2e7d32; font-weight: bold; margin: 0 0 10px 0;">{prod['price_str']}</p>
                <p style="color: #555; margin: 0 0 15px 0; font-weight: 500;">Vendido por: <strong>{prod['source']}</strong> | {verification_badge}</p>
                <a href="{prod['link']}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600;">Ver Producto en {prod['source']}</a>
            </div>
            <div style="flex: 1 1 100%; font-size: 12px; color: #666; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <strong>Puntuación de Relevancia:</strong> {int(prod.get('relevance_score',0))} | <strong>Puntuación Final:</strong> {prod.get('final_score',0):.2f} | <strong>Query usada:</strong> {prod.get('query_used', 'N/A')}
            </div>
        </div>'''
    content = f'''
    <div style="max-width: 900px; margin: 0 auto;">
        <h1 style="color: #333; text-align: center; margin-bottom: 20px;">Resultados para: "{query}"</h1>
        <div style="text-align: center; margin-bottom: 30px;"><a href="/search" style="background: white; border: 1px solid #ccc; color: #333; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: 600;">Nueva Búsqueda</a></div>
        {products_html}
    </div>'''
    return render_page(f'Resultados para "{query}"', content, use_layout=False)

def render_page(title, content, use_layout=True):
    if not use_layout: return content # Para la página de resultados que tiene su propio layout
    return f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }}
            h1 {{ text-align: center; color: #1a73e8; }} p {{ line-height: 1.6; }}
            input[type="text"], input[type="password"] {{ width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }}
            button {{ width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; }}
            button:hover {{ background: #1557b0; }}
            .error {{ background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; }}
            .loading {{ text-align: center; padding: 40px; display: none; }}
            .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1a73e8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg) }} 100% {{ transform: rotate(360deg) }} }}
        </style></head><body>{content}</body></html>'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("--- 🧠 BÚSQUEDA UNIVERSAL v4.1 MEJORADA ---")
    print(f"✅ Servidor listo y escuchando en http://localhost:{port}")
    # Cambiar a debug=False para producción
    app.run(host='0.0.0.0', port=port, debug=False)
