# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, session, redirect, url_for
import requests, os, re, html, time, math
from datetime import datetime
from urllib.parse import urlparse, unquote

# Importaciones opcionales para una mejor extracción, pero el código funcionará sin ellas.
try:
    from bs4 import BeautifulSoup
    import cloudscraper
    from price_parser import Price
    HAS_ENHANCED = True
except ImportError:
    HAS_ENHANCED = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-mucho-mejor')

# --- INICIO DE LA CLASE `IntelligentProductFinder` TOTALMENTE REESCRITA ---

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
        print(f"\n🧠 INICIANDO BÚSQUEDA INTELIGENTE Y FLEXIBLE PARA: '{query}'")
        
        # 1. Extraer especificaciones clave de la consulta.
        specs = self._extract_specifications(query)
        print(f"📋 Especificaciones detectadas: {specs}")

        # 2. Generar consultas de búsqueda más inteligentes y amplias.
        smart_queries = self._generate_smart_queries(query, specs)
        print(f"🔍 Queries generados: {smart_queries}")

        # 3. Recopilar una amplia gama de productos de todas las consultas.
        all_products = []
        for search_query in smart_queries:
            try:
                print(f"🔎 Buscando productos con la consulta: '{search_query}'")
                products = self._fetch_products_from_api(search_query)
                all_products.extend(products)
                if len(all_products) > 100: # Obtener una buena cantidad para analizar
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"❌ Error en la búsqueda para '{search_query}': {e}")

        if not all_products:
            print("🆘 La API no devolvió ningún producto para las consultas generadas.")
            return []
            
        print(f"📊 Total productos brutos encontrados: {len(all_products)}")

        # 4. Eliminar duplicados exactos basados en el enlace del producto.
        unique_products = list({p['link']: p for p in all_products if p.get('link')}.values())
        print(f"📦 Total productos únicos: {len(unique_products)}")
        
        # 5. Calificar cada producto en función de su relevancia, en lugar de un filtrado estricto.
        scored_products = self._score_and_enrich_products(unique_products, specs, query)
        print(f"⭐ Productos calificados: {len(scored_products)}")

        # 6. Filtrar productos con una puntuación de relevancia mínima para eliminar basura.
        relevant_products = [p for p in scored_products if p['relevance_score'] > 20]
        print(f"🎯 Productos relevantes (score > 20): {len(relevant_products)}")
        
        if not relevant_products:
            print("🆘 Ningún producto superó el umbral de relevancia mínimo.")
            return []

        # 7. Verificar que los enlaces de los productos más relevantes funcionen.
        verified_products = self._verify_real_links(relevant_products)
        print(f"✅ Productos con enlaces verificados: {len(verified_products)}")
        
        # 8. Ordenar por la puntuación final (que considera relevancia Y precio)
        final_products = sorted(verified_products, key=lambda x: x.get('final_score', 0), reverse=True)
        
        print(f"🏆 BÚSQUEDA COMPLETADA. Devolviendo {len(final_products)} productos ordenados.")
        return final_products[:30] # Devolver los mejores 30 resultados

    def _extract_specifications(self, query):
        specs = {}
        q_lower = query.lower()
        
        # Tamaños (más tolerante)
        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(pulgadas|pulgada|inch|in|")', q_lower)
        if size_match:
            specs['size_val'] = float(size_match.group(1))
            specs['size_unit'] = 'pulgada'
        
        # Colores
        colors = ['azul', 'rojo', 'verde', 'negro', 'blanco', 'plata', 'gris', 'amarillo']
        for color in colors:
            if color in q_lower:
                specs['color'] = color
                break
        
        # Marcas
        brands = ['3m', 'scotch', 'apple', 'samsung', 'hp', 'dell']
        for brand in brands:
            if brand in q_lower:
                specs['brand'] = brand
                break

        return specs

    def _generate_smart_queries(self, original_query, specs):
        # Crear una consulta base sin las especificaciones ya extraídas
        base_query = original_query.lower()
        if specs.get('color'): base_query = base_query.replace(specs['color'], '')
        if specs.get('size_val'): base_query = re.sub(r'(\d+(?:\.\d+)?)\s*(pulgadas|pulgada|inch|in|")', '', base_query)
        
        # Eliminar palabras comunes poco útiles
        stopwords = ['de', 'para', 'con', 'adhesiva', 'papel']
        for word in stopwords:
            base_query = base_query.replace(word, '')
        
        base_query = ' '.join(base_query.split()) # Normalizar espacios

        queries = {original_query} # Empezar con la consulta original
        
        # Añadir consulta base con especificaciones clave
        query_with_specs = base_query
        if specs.get('color'): query_with_specs += f" {specs['color']}"
        if specs.get('size_val'): query_with_specs += f" {specs['size_val']}{specs['size_unit']}"
        queries.add(query_with_specs)
        
        # Añadir una consulta más general
        queries.add(base_query)

        return list(queries)[:3]

    def _fetch_products_from_api(self, query):
        products = []
        params = {
            'engine': 'google_shopping',
            'q': query,
            'api_key': self.api_key,
            'num': 100,
            
            # --- ¡CONFIGURACIÓN CLAVE CORREGIDA! ---
            # Busca en un mercado de habla hispana como México.
            # Puedes cambiarlo a 'Spain', 'gl': 'es' para el mercado español.
            'location': 'Mexico',
            'gl': 'mx',
            'hl': 'es',
        }
        response = self.session.get(self.base_url, params=params, timeout=20)
        response.raise_for_status() # Lanza un error si la petición falla
        data = response.json()

        for item in data.get('shopping_results', []):
            price = self._extract_real_price(item)
            link = item.get('link')
            # Pre-filtro básico: debe tener título, enlace y precio para ser considerado
            if item.get('title') and link and price > 0:
                products.append({
                    'title': self._clean_text(item['title']),
                    'price_numeric': price,
                    'price_str': f"${price:,.2f} MXN", # Ajustar moneda según el mercado
                    'source': self._clean_text(item.get('source', 'Tienda')),
                    'link': link,
                    'thumbnail': item.get('thumbnail'),
                })
        return products
        
    def _score_and_enrich_products(self, products, specs, original_query):
        enriched_products = []
        query_words = set(original_query.lower().split())

        for product in products:
            score = 0
            title_lower = product['title'].lower()
            
            # Puntuación por coincidencia de especificaciones (MUY IMPORTANTE)
            if specs.get('color') and specs['color'] in title_lower:
                score += 50
            if specs.get('size_val') and self._size_matches(title_lower, specs['size_val']):
                score += 50
            if specs.get('brand') and specs['brand'] in title_lower:
                score += 30
            
            # Puntuación por palabras clave de la consulta original
            matched_words = query_words.intersection(set(title_lower.split()))
            score += len(matched_words) * 5

            product['relevance_score'] = score
            
            # Puntuación final: combina relevancia con precio.
            # Un producto muy relevante pero caro puede perder contra uno un poco menos relevante pero mucho más barato.
            # Se usa log(precio) para que la penalización por precio no sea tan drástica.
            product['final_score'] = score / (math.log(product['price_numeric'] + 1) + 1)

            enriched_products.append(product)
            
        return enriched_products

    def _size_matches(self, title_lower, spec_size_val):
        # Buscar todos los números en el título
        found_numbers = re.findall(r'(\d+(?:\.\d+)?)', title_lower)
        for num_str in found_numbers:
            try:
                num = float(num_str)
                # Tolerar pequeñas diferencias (ej. 1.88 pulgadas vs 2 pulgadas)
                if abs(num - spec_size_val) < 0.2:
                    # Comprobar si las unidades están cerca (ej. "in", "pulg")
                    if any(unit in title_lower for unit in ['in', 'pulg', '"']):
                        return True
            except ValueError:
                continue
        return False

    def _verify_real_links(self, products):
        verified = []
        # Solo verificar los 20 mejores candidatos para no hacer demasiadas peticiones
        for product in sorted(products, key=lambda p: p['final_score'], reverse=True)[:20]:
            try:
                response = self.session.head(product['link'], timeout=5, allow_redirects=True)
                if response.status_code < 400: # 2xx (OK) o 3xx (Redirect) son válidos
                    product['verified_link'] = True
                    verified.append(product)
                    print(f"✅ Enlace OK ({response.status_code}): {product['link'][:70]}")
                else:
                    print(f"❌ Enlace Roto ({response.status_code}): {product['link'][:70]}")
            except requests.exceptions.RequestException:
                print(f"❌ Error de Conexión: {product['link'][:70]}")
        return verified
    
    def _extract_real_price(self, item):
        price_str = str(item.get('extracted_price') or item.get('price', '0'))
        # Limpiar la cadena de cualquier símbolo de moneda, comas, etc.
        clean_price = re.sub(r'[^\d.]', '', price_str)
        try:
            return float(clean_price) if clean_price else 0.0
        except ValueError:
            return 0.0
            
    def _clean_text(self, text):
        return html.unescape(str(text)).strip()


# --- EL RESTO DE LA APLICACIÓN FLASK (SIN CAMBIOS SIGNIFICATIVOS) ---

# (El código HTML/CSS/JS de las plantillas se mantiene igual)
def render_page(title, content):
    return f'''<!DOCTYPE html><html><head><title>{title}</title><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}}.container{{max-width:700px;margin:0 auto;background:white;padding:30px;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}h1{{color:#1a73e8;text-align:center;margin-bottom:10px}}.subtitle{{text-align:center;color:#666;margin-bottom:30px}}input{{width:100%;padding:15px;margin:10px 0;border:2px solid #e1e5e9;border-radius:8px;font-size:16px}}input:focus{{outline:none;border-color:#1a73e8}}button{{width:100%;padding:15px;background:#1a73e8;color:white;border:none;border-radius:8px;cursor:pointer;font-size:16px;font-weight:600}}button:hover{{background:#1557b0}}.search-bar{{display:flex;gap:10px;margin-bottom:25px}}.search-bar input{{flex:1}}.search-bar button{{width:auto;padding:15px 25px}}.tips{{background:#e8f5e8;border:1px solid #4caf50;padding:20px;border-radius:8px;margin-bottom:20px}}.features{{background:#f8f9fa;padding:20px;border-radius:8px;margin-top:25px}}.features ul{{list-style:none}}.features li{{padding:5px 0}}.features li:before{{content:"🧠 "}}.error{{background:#ffebee;color:#c62828;padding:15px;border-radius:8px;margin:15px 0;display:none}}.loading{{text-align:center;padding:40px;display:none}}.spinner{{border:4px solid #f3f3f3;border-top:4px solid #1a73e8;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:0 auto 20px}}@keyframes spin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}.guarantee{{background:#e3f2fd;border:2px solid #2196f3;padding:20px;border-radius:8px;margin-top:20px;text-align:center}}</style>
    </head><body>{content}</body></html>'''

@app.route('/')
def index():
    content = '''<div class="container"><h1>🧠 Búsqueda Inteligente y Flexible</h1><p class="subtitle">🎯 Encuentra productos relevantes, baratos y con enlaces reales.</p>
    <form id="setupForm"><label for="apiKey">API Key de SerpAPI:</label><input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required><button type="submit">🧠 ACTIVAR INTELIGENCIA</button></form>
    <div class="features"><h3>⚡ Nueva Lógica de Búsqueda:</h3><ul><li>Busca en tu mercado local (configurable).</li><li>No más filtros rígidos, ahora usa un sistema de puntuación.</li><li>Prioriza productos baratos que coinciden con tu búsqueda.</li><li>Verifica los enlaces de los mejores resultados para ti.</li></ul></div>
    <div id="error" class="error"></div><div id="loading" class="loading"><div class="spinner"></div><p>Validando...</p></div></div>
    <script>document.getElementById('setupForm').addEventListener('submit',function(e){e.preventDefault();const apiKey=document.getElementById('apiKey').value.trim();if(!apiKey)return showError('Ingresa tu API key');showLoading();fetch('/setup',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'api_key='+encodeURIComponent(apiKey)}).then(response=>response.json()).then(data=>{hideLoading();data.success?window.location.href='/search':showError(data.error||'Error')}).catch(()=>{hideLoading();showError('Error de conexión')})});function showLoading(){document.getElementById('loading').style.display='block';document.getElementById('error').style.display='none'}function hideLoading(){document.getElementById('loading').style.display='none'}function showError(msg){hideLoading();const e=document.getElementById('error');e.textContent=msg;e.style.display='block'}</script>'''
    return render_page('🧠 Búsqueda INTELIGENTE', content)

@app.route('/setup', methods=['POST'])
def setup_api():
    api_key = request.form.get('api_key', '').strip()
    if not api_key: return jsonify({'error': 'API key requerida'}), 400
    finder = IntelligentProductFinder(api_key)
    test_result = finder.test_api_key()
    if not test_result.get('valid'):
        return jsonify({'error': test_result.get('message')}), 400
    session['api_key'] = api_key
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    if 'api_key' not in session: return redirect(url_for('index'))
    content = '''<div class="container"><h1>🎯 Búsqueda Inteligente</h1><p class="subtitle">Describe el producto que buscas. Sé tan específico como quieras.</p>
    <form id="searchForm"><div class="search-bar"><input type="text" id="searchQuery" placeholder="Ej: cinta azul 2 pulgadas, iPhone 14 Pro 256GB morado..." required><button type="submit">🔍 BUSCAR</button></div></form>
    <div class="tips"><h4>💡 Cómo funciona:</h4><ul style="margin:10px 0 0 20px"><li><strong>1.</strong> Analizamos tu búsqueda para entender qué es importante.</li><li><strong>2.</strong> Buscamos en tiendas locales para encontrar muchos candidatos.</li><li><strong>3.</strong> Calificamos cada producto por relevancia y precio.</li><li><strong>4.</strong> Te mostramos los mejores resultados, ¡con enlaces que sí funcionan!</li></ul></div>
    <div id="loading" class="loading"><div class="spinner"></div><h3>🧠 Analizando y calificando productos...</h3><p>Esto puede tardar unos segundos...</p></div><div id="error" class="error"></div></div>
    <script>let searching=false;document.getElementById('searchForm').addEventListener('submit',function(e){e.preventDefault();if(searching)return;const query=document.getElementById('searchQuery').value.trim();if(!query)return showError('Describe el producto que buscas.');searching=true;showLoading();fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query})}).then(res=>res.json()).then(data=>{if(data.success){sessionStorage.setItem('searchResults',JSON.stringify(data));window.location.href='/results'}else{showError(data.error||'Ocurrió un error')}}).catch(()=>{searching=false;hideLoading();showError('Error de conexión')}).finally(()=>searching=false)});function showLoading(){document.getElementById('loading').style.display='block';document.getElementById('error').style.display='none'}function hideLoading(){document.getElementById('loading').style.display='none'}function showError(msg){hideLoading();const e=document.getElementById('error');e.textContent=msg;e.style.display='block'}</script>'''
    return render_page('🎯 Búsqueda Inteligente', content)

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session: return jsonify({'error': 'API key no configurada'}), 401
    data = request.get_json()
    query = data.get('query', '').strip() if data else ''
    if not query: return jsonify({'error': 'La consulta no puede estar vacía'}), 400
    
    try:
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        session['last_search'] = {'query': query, 'products': products}
        return jsonify({'success': True, 'query': query, 'products': products})
    except Exception as e:
        print(f"[ERROR en /api/search]: {e}")
        return jsonify({'success': False, 'error': 'No se pudieron obtener resultados. Revisa la consola del servidor para más detalles.'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    query = html.escape(search_data.get('query', ''))
    products = search_data.get('products', [])

    if not products:
        content = f'''<div class="container" style="text-align:center;">
            <h1>Resultados para "{query}"</h1>
            <h2 style="color:#c62828;margin-top:20px;">No se encontraron resultados relevantes</h2>
            <p style="margin:20px 0;">Lo intentamos con varias consultas y no encontramos productos que coincidieran lo suficiente con tu búsqueda.</p>
            <h4>💡 Sugerencias:</h4>
            <ul style="text-align:left; max-width:400px; margin:10px auto 30px auto; list-style-position:inside;">
                <li>Intenta una búsqueda más simple (ej. "cinta azul" en vez de "cinta de papel adhesiva azul").</li>
                <li>Verifica la ortografía.</li>
                <li>El producto podría no estar disponible en las tiendas online del mercado seleccionado (México por defecto).</li>
            </ul>
            <a href="/search" style="display:inline-block; background:#1a73e8;color:white;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:600">Intentar Nueva Búsqueda</a>
        </div>'''
        return render_page(f'Sin Resultados para "{query}"', content)

    products_html = ""
    for prod in products:
        products_html += f'''
        <div style="border:1px solid #ddd; border-radius:12px; padding:20px; margin-bottom:20px; background:white; display:flex; gap:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <div style="flex-shrink:0;"><img src="{prod.get('thumbnail', 'https://via.placeholder.com/150')}" alt="{html.escape(prod['title'])}" style="width:150px; height:150px; object-fit:contain; border-radius:8px;"></div>
            <div>
                <h3 style="margin:0 0 10px 0; color:#1a73e8; font-size:18px;">{prod['title']}</h3>
                <p style="font-size:28px; color:#2e7d32; font-weight:bold; margin:0 0 10px 0;">{prod['price_str']}</p>
                <p style="color:#555; margin:0 0 15px 0; font-weight:500;">Vendido por: {prod['source']}</p>
                <div style="font-size:12px; color: #888; margin-bottom:15px;">
                    <span>Relevancia: {int(prod.get('relevance_score',0))}</span> | 
                    <span>Score Final (Relevancia/Precio): {prod.get('final_score',0):.2f}</span>
                </div>
                <a href="{prod['link']}" target="_blank" style="display:inline-block; background:#1a73e8;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:600">Ver Producto</a>
            </div>
        </div>'''

    content = f'''<div style="max-width:900px; margin:0 auto;">
        <h1 style="color:white;text-align:center;margin-bottom:20px;">Resultados para: "{query}"</h1>
        <div style="text-align:center; margin-bottom:30px;"><a href="/search" style="background:white;color:#1a73e8;padding:12px 25px;text-decoration:none;border-radius:25px;font-weight:600">Nueva Búsqueda</a></div>
        {products_html}
    </div>'''
    return render_page(f'Resultados para "{query}"', content)

if __name__ == '__main__':
    print("--- 🧠 BÚSQUEDA INTELIGENTE Y FLEXIBLE v2.0 ---")
    print("✅ LISTO PARA RECIBIR BÚSQUEDAS")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
