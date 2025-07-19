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
app.secret_key = os.environ.get('SECRET_KEY', 'v3-secret-key-super-robust')

# --- INICIO DE LA NUEVA CLASE v3.0 - "NIVEL EXPERTO" ---

class IntelligentProductFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        })

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
            model_match = re.search(r'(iphone\s?(\d+\s?(pro|max|plus|mini)?(\s?pro\s?max)?)?)', q_lower)
            if model_match:
                specs['model'] = model_match.group(1).strip().split()
        
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
        if specs.get('brand') and specs.get('model'):
            # Consulta "perfecta": Marca + Modelo + Color + Capacidad
            perfect_query = f"{specs['brand']} {' '.join(specs['model'])}"
            if specs.get('capacity'):
                perfect_query += f" {specs['capacity']}"
            if specs.get('color'):
                perfect_query += f" {specs['color']}"
            queries.add(perfect_query)
            # Consulta amplia: Marca + Modelo
            queries.add(f"{specs['brand']} {' '.join(specs['model'])}")
        return list(queries)

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
                model_words = set(specs['model'])
                title_words = set(title_lower.split())
                if model_words.issubset(title_words):
                    score += 50 # Puntuación alta por coincidencia de modelo
            
            # 2. Penalización por "Ruido" (elimina accesorios)
            # Penaliza por cada palabra en el título que NO estaba en la consulta original
            title_word_set = set(title_lower.split())
            noise_words = title_word_set - query_words
            # Palabras comunes en accesorios que queremos penalizar fuertemente
            accessory_words = {'funda', 'mica', 'protector', 'case', 'para', 'compatible', 'con'}
            penalty = 0
            for word in noise_words:
                if word in accessory_words:
                    penalty += 20 # Penalización fuerte
                else:
                    penalty += 2 # Penalización ligera
            
            score -= penalty
            
            product['relevance_score'] = score
            product['final_score'] = score / (math.log(product['price_numeric'] + 1, 10)) # Puntuación final balanceada por precio
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
                pass # Ignorar errores de conexión silenciosamente
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

# --- El resto de la app Flask se mantiene casi igual, con mejoras en la visualización ---

@app.route('/')
def index():
    # ... (código sin cambios)
    return flask.render_template_string('''...''') 

@app.route('/setup', methods=['POST'])
def setup_api():
    # ... (código sin cambios)
    return jsonify({'success': True})

@app.route('/search')
def search_page():
    # ... (código sin cambios)
    return flask.render_template_string('''...''') 

@app.route('/api/search', methods=['POST'])
def api_search():
    if 'api_key' not in session: return jsonify({'error': 'API key no configurada'}), 401
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query: return jsonify({'error': 'La consulta no puede estar vacía'}), 400
    
    try:
        finder = IntelligentProductFinder(session['api_key'])
        products = finder.search_products(query)
        session['last_search'] = {'query': query, 'products': products}
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR en /api/search]: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    query = html.escape(search_data.get('query', ''))
    products = search_data.get('products', [])

    if not products:
        # Página de "No resultados"
        # ... (código sin cambios)
        return flask.render_template_string('''...''') 

    # --- PÁGINA DE RESULTADOS MEJORADA ---
    products_html = ""
    for prod in products:
        products_html += f'''
        <div style="border:1px solid #ddd; border-radius:12px; padding:20px; margin-bottom:20px; background:white; display:flex; flex-wrap: wrap; gap:20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <div style="flex: 0 0 150px; text-align: center;">
                <img src="{prod.get('thumbnail', 'https://via.placeholder.com/150')}" alt="{html.escape(prod['title'])}" style="width:150px; height:150px; object-fit:contain; border-radius:8px;">
            </div>
            <div style="flex: 1; min-width: 300px;">
                <h3 style="margin:0 0 10px 0; color:#1a73e8; font-size:18px;">{prod['title']}</h3>
                <p style="font-size:28px; color:#2e7d32; font-weight:bold; margin:0 0 10px 0;">{prod['price_str']}</p>
                <p style="color:#555; margin:0 0 15px 0; font-weight:500;">Vendido por: <strong>{prod['source']}</strong></p>
                <a href="{prod['link']}" target="_blank" style="display:inline-block; background:linear-gradient(135deg, #2196F3, #1976D2);color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:600">Ver Producto</a>
            </div>
            <div style="flex: 1 1 100%; font-size:12px; color: #666; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 10px;">
                <strong>Puntuación de Relevancia:</strong> {int(prod.get('relevance_score',0))} | 
                <strong>Puntuación Final (Relevancia / Precio):</strong> {prod.get('final_score',0):.2f}
            </div>
        </div>'''

    content = f'''
    <!DOCTYPE html><html><head><title>Resultados para "{query}"</title><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>body{{font-family:system-ui,sans-serif;background:#f0f2f5;padding:20px;}}</style></head><body>
    <div style="max-width:900px; margin:0 auto;">
        <h1 style="color:#333;text-align:center;margin-bottom:20px;">Resultados para: "{query}"</h1>
        <div style="text-align:center; margin-bottom:30px;"><a href="/search" style="background:#fff; border: 1px solid #ccc; color:#333;padding:12px 25px;text-decoration:none;border-radius:25px;font-weight:600">Nueva Búsqueda</a></div>
        {products_html}
    </div></body></html>'''
    return content

# El resto de las rutas y la ejecución principal no necesitan cambios.
# Para brevedad, el código de las plantillas de index, setup y search se omite, pero sigue siendo el mismo.
if __name__ == '__main__':
    print("--- 🧠 BÚSQUEDA EXPERTA v3.0 ---")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
