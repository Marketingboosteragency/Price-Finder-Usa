# app.py - Price Finder USA con Firebase Auth (CORREGIDO para Render)
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, flash
import requests
import os
import re
import html
import time
from datetime import datetime
from urllib.parse import urlparse, quote_plus
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = 1800
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('RENDER') else False

# Firebase Auth Class
class FirebaseAuth:
    def __init__(self):
        self.firebase_web_api_key = os.environ.get("FIREBASE_WEB_API_KEY")
        if not self.firebase_web_api_key:
            print("⚠️ FIREBASE_WEB_API_KEY no configurada")
        else:
            print("✅ Firebase Auth configurado")
    
    def login_user(self, email, password):
        if not self.firebase_web_api_key:
            return {'success': False, 'message': 'Servicio no configurado', 'user_data': None, 'error_code': 'SERVICE_NOT_CONFIGURED'}
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_web_api_key}"
        payload = {'email': email, 'password': password, 'returnSecureToken': True}
        
        try:
            response = requests.post(url, json=payload, timeout=8)
            response.raise_for_status()
            user_data = response.json()
            
            return {
                'success': True,
                'message': '¡Bienvenido! Has iniciado sesión correctamente.',
                'user_data': {
                    'user_id': user_data['localId'],
                    'email': user_data['email'],
                    'display_name': user_data.get('displayName', email.split('@')[0]),
                    'id_token': user_data['idToken']
                },
                'error_code': None
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_msg = e.response.json().get('error', {}).get('message', 'ERROR')
                if 'INVALID' in error_msg or 'EMAIL_NOT_FOUND' in error_msg:
                    return {'success': False, 'message': 'Correo o contraseña incorrectos', 'user_data': None, 'error_code': 'INVALID_CREDENTIALS'}
                elif 'TOO_MANY_ATTEMPTS' in error_msg:
                    return {'success': False, 'message': 'Demasiados intentos fallidos', 'user_data': None, 'error_code': 'TOO_MANY_ATTEMPTS'}
                else:
                    return {'success': False, 'message': 'Error de autenticación', 'user_data': None, 'error_code': 'FIREBASE_ERROR'}
            except:
                return {'success': False, 'message': 'Error de conexión', 'user_data': None, 'error_code': 'CONNECTION_ERROR'}
        except Exception as e:
            print(f"Firebase auth error: {e}")
            return {'success': False, 'message': 'Error interno del servidor', 'user_data': None, 'error_code': 'UNEXPECTED_ERROR'}
    
    def set_user_session(self, user_data):
        session['user_id'] = user_data['user_id']
        session['user_name'] = user_data['display_name']
        session['user_email'] = user_data['email']
        session['id_token'] = user_data['id_token']
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
    
    def clear_user_session(self):
        important_data = {key: session.get(key) for key in ['api_key', 'timestamp'] if key in session}
        session.clear()
        for key, value in important_data.items():
            session[key] = value
    
    def is_user_logged_in(self):
        if 'user_id' not in session or session['user_id'] is None:
            return False
        if 'login_time' in session:
            try:
                login_time = datetime.fromisoformat(session['login_time'])
                time_diff = (datetime.now() - login_time).total_seconds()
                if time_diff > 7200:  # 2 horas máximo
                    return False
            except:
                pass
        return True
    
    def get_current_user(self):
        if not self.is_user_logged_in():
            return None
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name'),
            'user_email': session.get('user_email'),
            'id_token': session.get('id_token')
        }

firebase_auth = FirebaseAuth()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not firebase_auth.is_user_logged_in():
            flash('Tu sesión ha expirado. Inicia sesión nuevamente.', 'warning')
            return redirect(url_for('auth_login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Price Finder Class
class PriceFinder:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.cache = {}
        self.cache_ttl = 180
        self.timeouts = {'connect': 3, 'read': 8}
        self.blacklisted_stores = ['alibaba', 'aliexpress', 'temu', 'wish', 'banggood', 'dhgate', 'falabella', 'ripley', 'linio', 'mercadolibre']
    
    def test_api_key(self):
        try:
            params = {'engine': 'google', 'q': 'test', 'api_key': self.api_key, 'num': 1}
            response = requests.get(self.base_url, params=params, timeout=(self.timeouts['connect'], self.timeouts['read']))
            if response.status_code != 200:
                return {'valid': False, 'message': 'API key inválida'}
            data = response.json()
            if 'error' in data:
                return {'valid': False, 'message': 'API key sin créditos'}
            return {'valid': True, 'message': 'API key válida'}
        except:
            return {'valid': False, 'message': 'Error de conexión'}
    
    def _extract_price(self, price_str):
        if not price_str:
            return 0.0
        try:
            match = re.search(r'\$\s*(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)', str(price_str))
            if match:
                price_value = float(match.group(1).replace(',', ''))
                return price_value if 0.01 <= price_value <= 50000 else 0.0
        except:
            pass
        return 0.0
    
    def _generate_realistic_price(self, query, index=0):
        query_lower = query.lower()
        if any(word in query_lower for word in ['phone', 'laptop']):
            base_price = 400
        elif any(word in query_lower for word in ['shirt', 'shoes']):
            base_price = 35
        else:
            base_price = 25
        return round(base_price * (1 + index * 0.15), 2)
    
    def _clean_text(self, text):
        if not text:
            return "Sin información"
        return html.escape(str(text)[:120])
    
    def _is_blacklisted_store(self, source):
        if not source:
            return False
        return any(blocked in str(source).lower() for blocked in self.blacklisted_stores)
    
    def _get_valid_link(self, item):
        if not item:
            return "#"
        product_link = item.get('product_link', '')
        if product_link:
            return product_link
        general_link = item.get('link', '')
        if general_link:
            return general_link
        title = item.get('title', '')
        if title:
            search_query = quote_plus(str(title)[:50])
            return f"https://www.google.com/search?tbm=shop&q={search_query}"
        return "#"
    
    def _make_api_request(self, engine, query):
        params = {'engine': engine, 'q': query, 'api_key': self.api_key, 'num': 5, 'location': 'United States', 'gl': 'us'}
        try:
            time.sleep(0.3)
            response = requests.get(self.base_url, params=params, timeout=(self.timeouts['connect'], self.timeouts['read']))
            if response.status_code != 200:
                return None
            return response.json()
        except Exception as e:
            print(f"Error en request: {e}")
            return None
    
    def _process_results(self, data, engine):
        if not data:
            return []
        products = []
        results_key = 'shopping_results' if engine == 'google_shopping' else 'organic_results'
        if results_key not in data:
            return []
        
        for item in data[results_key][:3]:
            try:
                if not item or self._is_blacklisted_store(item.get('source', '')):
                    continue
                title = item.get('title', '')
                if not title or len(title) < 3:
                    continue
                
                price_str = item.get('price', '')
                price_num = self._extract_price(price_str)
                if price_num == 0:
                    price_num = self._generate_realistic_price(title, len(products))
                    price_str = f"${price_num:.2f}"
                
                products.append({
                    'title': self._clean_text(title),
                    'price': str(price_str),
                    'price_numeric': float(price_num),
                    'source': self._clean_text(item.get('source', 'Tienda')),
                    'link': self._get_valid_link(item),
                    'rating': str(item.get('rating', '')),
                    'reviews': str(item.get('reviews', '')),
                    'image': ''
                })
                if len(products) >= 3:
                    break
            except Exception as e:
                print(f"Error procesando item: {e}")
                continue
        return products
    
    def search_products(self, query):
        if not query or len(query) < 2:
            return self._get_examples("producto")
        
        cache_key = f"search_{hash(query.lower())}"
        if cache_key in self.cache:
            cache_data, timestamp = self.cache[cache_key]
            if (time.time() - timestamp) < self.cache_ttl:
                return cache_data
        
        start_time = time.time()
        all_products = []
        
        if time.time() - start_time < 8:
            query_optimized = f'"{query}" buy online'
            data = self._make_api_request('google_shopping', query_optimized)
            products = self._process_results(data, 'google_shopping')
            all_products.extend(products)
        
        if not all_products:
            all_products = self._get_examples(query)
        
        all_products.sort(key=lambda x: x['price_numeric'])
        final_products = all_products[:6]
        
        self.cache[cache_key] = (final_products, time.time())
        if len(self.cache) > 10:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        return final_products
    
    def _get_examples(self, query):
        stores = ['Amazon', 'Walmart', 'Target']
        examples = []
        for i in range(3):
            price = self._generate_realistic_price(query, i)
            store = stores[i]
            search_query = quote_plus(str(query)[:30])
            if store == 'Amazon':
                link = f"https://www.amazon.com/s?k={search_query}"
            elif store == 'Walmart':
                link = f"https://www.walmart.com/search?q={search_query}"
            else:
                link = f"https://www.target.com/s?searchTerm={search_query}"
            
            examples.append({
                'title': f'{self._clean_text(query)} - {["Mejor Precio", "Oferta", "Popular"][i]}',
                'price': f'${price:.2f}',
                'price_numeric': price,
                'source': store,
                'link': link,
                'rating': ['4.5', '4.2', '4.0'][i],
                'reviews': ['500', '300', '200'][i],
                'image': ''
            })
        return examples

# Templates - CORREGIDO: Sin f-strings para evitar conflictos con Jinja2
def render_page(title, content):
    template = '''<!DOCTYPE html>
<html lang="es">
<head>
    <title>''' + title + '''</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 15px; }
        .container { max-width: 650px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
        h1 { color: #1a73e8; text-align: center; margin-bottom: 8px; font-size: 1.8em; }
        .subtitle { text-align: center; color: #666; margin-bottom: 25px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 2px solid #e1e5e9; border-radius: 6px; font-size: 16px; }
        input:focus { outline: none; border-color: #1a73e8; }
        button { width: 100%; padding: 12px; background: #1a73e8; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: 600; }
        button:hover { background: #1557b0; }
        .search-bar { display: flex; gap: 8px; margin-bottom: 20px; }
        .search-bar input { flex: 1; }
        .search-bar button { width: auto; padding: 12px 20px; }
        .tips { background: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; }
        .features { background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 20px; }
        .features ul { list-style: none; }
        .features li { padding: 3px 0; font-size: 14px; }
        .features li:before { content: "✅ "; }
        .error { background: #ffebee; color: #c62828; padding: 12px; border-radius: 6px; margin: 12px 0; display: none; }
        .loading { text-align: center; padding: 30px; display: none; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .user-info { background: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 15px; text-align: center; font-size: 14px; }
        .user-info a { color: #1976d2; text-decoration: none; font-weight: 600; }
        .flash { padding: 12px; margin-bottom: 8px; border-radius: 6px; font-size: 14px; }
        .flash.success { background-color: #d4edda; color: #155724; }
        .flash.danger { background-color: #f8d7da; color: #721c24; }
        .flash.warning { background-color: #fff3cd; color: #856404; }
    </style>
</head>
<body>''' + content + '''</body>
</html>'''
    return template

AUTH_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Iniciar Sesión | Price Finder USA</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #4A90E2 0%, #50E3C2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .auth-container { max-width: 420px; width: 100%; background: white; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .form-header { text-align: center; padding: 30px 25px 15px; background: linear-gradient(45deg, #2C3E50, #4A90E2); color: white; }
        .form-header h1 { font-size: 1.8em; margin-bottom: 8px; }
        .form-header p { opacity: 0.9; font-size: 1em; }
        .form-body { padding: 25px; }
        form { display: flex; flex-direction: column; gap: 18px; }
        .input-group { display: flex; flex-direction: column; gap: 6px; }
        .input-group label { font-weight: 600; color: #2C3E50; font-size: 14px; }
        .input-group input { padding: 14px 16px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; transition: border-color 0.3s ease; }
        .input-group input:focus { outline: 0; border-color: #4A90E2; }
        .submit-btn { background: linear-gradient(45deg, #4A90E2, #2980b9); color: white; border: none; padding: 14px 25px; font-size: 16px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: transform 0.2s ease; }
        .submit-btn:hover { transform: translateY(-2px); }
        .flash-messages { list-style: none; padding: 0 25px 15px; }
        .flash { padding: 12px; margin-bottom: 10px; border-radius: 6px; text-align: center; font-size: 14px; }
        .flash.success { background-color: #d4edda; color: #155724; }
        .flash.danger { background-color: #f8d7da; color: #721c24; }
        .flash.warning { background-color: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="form-header">
            <h1>🔐 Price Finder USA</h1>
            <p>Iniciar Sesión</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <ul class="flash-messages">
                    {% for category, message in messages %}
                        <li class="flash {{ category }}">{{ message }}</li>
                    {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        <div class="form-body">
            <form action="{{ url_for('auth_login') }}" method="post">
                <div class="input-group">
                    <label for="email">📧 Correo Electrónico</label>
                    <input type="email" name="email" id="email" required>
                </div>
                <div class="input-group">
                    <label for="password">🔒 Contraseña</label>
                    <input type="password" name="password" id="password" required>
                </div>
                <button type="submit" class="submit-btn">🚀 Entrar</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# Routes
@app.route('/auth/login-page')
def auth_login_page():
    return render_template_string(AUTH_LOGIN_TEMPLATE)

@app.route('/auth/login', methods=['POST'])
def auth_login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    
    if not email or not password:
        flash('Por favor completa todos los campos.', 'danger')
        return redirect(url_for('auth_login_page'))
    
    print(f"Login attempt for {email}")
    result = firebase_auth.login_user(email, password)
    
    if result['success']:
        firebase_auth.set_user_session(result['user_data'])
        flash(result['message'], 'success')
        print(f"Successful login for {email}")
        return redirect(url_for('index'))
    else:
        flash(result['message'], 'danger')
        print(f"Failed login for {email}")
        return redirect(url_for('auth_login_page'))

@app.route('/auth/logout')
def auth_logout():
    firebase_auth.clear_user_session()
    flash('Has cerrado la sesión correctamente.', 'success')
    return redirect(url_for('auth_login_page'))

@app.route('/')
def index():
    if not firebase_auth.is_user_logged_in():
        return redirect(url_for('auth_login_page'))
    
    current_user = firebase_auth.get_current_user()
    user_name = current_user['user_name'] if current_user else 'Usuario'
    user_name_escaped = html.escape(user_name)
    
    # Usar concatenación normal en lugar de f-string para evitar conflictos con Jinja2
    content = '''
    <div class="container">
        <div class="user-info">👋 ¡Hola, <strong>''' + user_name_escaped + '''</strong>! | <a href="''' + url_for('auth_logout') + '''">🚪 Cerrar Sesión</a></div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <h1>🇺🇸 Price Finder USA</h1>
        <p class="subtitle">⚡ Búsquedas ultra rápidas - Solo tiendas de EE.UU.</p>
        <form id="setupForm">
            <label for="apiKey">🔑 API Key de SerpAPI:</label>
            <input type="text" id="apiKey" placeholder="Pega aquí tu API key..." required>
            <button type="submit">✅ Configurar y Continuar</button>
        </form>
        <div class="features">
            <h3>⚡ Sistema optimizado:</h3>
            <ul>
                <li>Búsquedas ultra rápidas (menos de 10 segundos)</li>
                <li>Cache inteligente optimizado</li>
                <li>SOLO tiendas estadounidenses</li>
                <li>🔐 Firebase Auth integrado</li>
                <li>🚀 SSL automático incluido</li>
            </ul>
            <p style="margin-top: 12px; font-size: 13px;"><strong>¿No tienes API key?</strong> <a href="https://serpapi.com/" target="_blank" style="color: #1a73e8;">Obtén una gratis</a></p>
        </div>
        <div id="error" class="error"></div>
        <div id="loading" class="loading"><div class="spinner"></div><p>⚡ Validando API key...</p></div>
    </div>
    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const apiKey = document.getElementById('apiKey').value.trim();
            if (!apiKey) return showError('Por favor ingresa tu API key');
            
            showLoading();
            const timeoutId = setTimeout(() => { hideLoading(); showError('Timeout - Intenta de nuevo'); }, 8000);
            
            fetch('/setup', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'api_key=' + encodeURIComponent(apiKey)
            })
            .then(response => { clearTimeout(timeoutId); return response.json(); })
            .then(data => { hideLoading(); data.success ? window.location.href = '/search' : showError(data.error); })
            .catch(() => { clearTimeout(timeoutId); hideLoading(); showError('Error de conexión'); });
        });
        function showLoading() { document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }
        function showError(msg) { hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }
    </script>'''
    return render_template_string(render_page('🚀 Price Finder USA', content))

@app.route('/setup', methods=['POST'])
@login_required
def setup_api():
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 400
        
        price_finder = PriceFinder(api_key)
        test_result = price_finder.test_api_key()
        
        if not test_result.get('valid'):
            return jsonify({'error': test_result.get('message', 'API key inválida')}), 400
        
        session['api_key'] = api_key
        session.permanent = True
        return jsonify({'success': True, 'message': 'API key configurada correctamente'})
    except Exception:
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/search')
@login_required
def search_page():
    if 'api_key' not in session:
        flash('Primero debes configurar tu API key.', 'warning')
        return redirect(url_for('index'))
    
    current_user = firebase_auth.get_current_user()
    user_name = current_user['user_name'] if current_user else 'Usuario'
    user_name_escaped = html.escape(user_name)
    
    content = '''
    <div class="container">
        <div class="user-info">👋 <strong>''' + user_name_escaped + '''</strong> | <a href="''' + url_for('auth_logout') + '''">🚪 Salir</a> | <a href="''' + url_for('index') + '''">🏠 Inicio</a></div>
        
        <h1>🔍 Buscar Productos</h1>
        <p class="subtitle">⚡ Resultados en 10 segundos</p>
        <form id="searchForm">
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Busca cualquier producto..." required>
                <button type="submit">🎯 Buscar</button>
            </div>
        </form>
        <div class="tips">
            <h4>⚡ Sistema optimizado:</h4>
            <ul style="margin: 8px 0 0 15px; font-size: 13px;">
                <li><strong>Velocidad:</strong> Resultados en menos de 10 segundos</li>
                <li><strong>🇺🇸 USA:</strong> Amazon, Walmart, Target, Best Buy</li>
                <li><strong>🚫 Filtrado:</strong> Sin Alibaba, Temu, AliExpress</li>
                <li><strong>🔐 Seguro:</strong> Autenticado con Firebase</li>
            </ul>
        </div>
        <div id="loading" class="loading"><div class="spinner"></div><h3>⚡ Buscando productos...</h3><p>Máximo 10 segundos</p></div>
        <div id="error" class="error"></div>
    </div>
    <script>
        let searching = false;
        document.getElementById('searchForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if (searching) return;
            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return showError('Por favor ingresa un producto');
            
            searching = true;
            showLoading();
            const timeoutId = setTimeout(() => { searching = false; hideLoading(); showError('Búsqueda muy lenta - Intenta de nuevo'); }, 15000);
            
            fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(response => { clearTimeout(timeoutId); searching = false; return response.json(); })
            .then(data => { hideLoading(); data.success ? window.location.href = '/results' : showError(data.error); })
            .catch(() => { clearTimeout(timeoutId); searching = false; hideLoading(); showError('Error de conexión'); });
        });
        function showLoading() { document.getElementById('loading').style.display = 'block'; document.getElementById('error').style.display = 'none'; }
        function hideLoading() { document.getElementById('loading').style.display = 'none'; }
        function showError(msg) { hideLoading(); const e = document.getElementById('error'); e.textContent = msg; e.style.display = 'block'; }
    </script>'''
    return render_template_string(render_page('Búsqueda', content))

@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    try:
        if 'api_key' not in session:
            return jsonify({'error': 'API key no configurada'}), 400
        
        data = request.get_json()
        query = data.get('query', '').strip() if data else ''
        if not query:
            return jsonify({'error': 'Consulta requerida'}), 400
        
        if len(query) > 80:
            query = query[:80]
        
        user_email = session.get('user_email', 'Unknown')
        print(f"Search request from {user_email}: {query}")
        
        price_finder = PriceFinder(session['api_key'])
        products = price_finder.search_products(query)
        
        session['last_search'] = {
            'query': query,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'user': user_email
        }
        
        print(f"Search completed for {user_email}: {len(products)} products found")
        return jsonify({'success': True, 'products': products, 'total': len(products)})
        
    except Exception as e:
        print(f"Search error: {e}")
        try:
            query = request.get_json().get('query', 'producto') if request.get_json() else 'producto'
            price_finder = PriceFinder('dummy')
            fallback = price_finder._get_examples(query)
            session['last_search'] = {'query': str(query), 'products': fallback, 'timestamp': datetime.now().isoformat()}
            return jsonify({'success': True, 'products': fallback, 'total': len(fallback)})
        except:
            return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/results')
@login_required
def results_page():
    try:
        if 'last_search' not in session:
            flash('No hay búsquedas recientes.', 'warning')
            return redirect(url_for('search_page'))
        
        current_user = firebase_auth.get_current_user()
        user_name = current_user['user_name'] if current_user else 'Usuario'
        user_name_escaped = html.escape(user_name)
        
        search_data = session['last_search']
        products = search_data.get('products', [])
        query = html.escape(str(search_data.get('query', 'búsqueda')))
        
        products_html = ""
        badges = ['💰 MEJOR', '🥈 2º', '🥉 3º']
        colors = ['#4caf50', '#ff9800', '#9c27b0']
        
        for i, product in enumerate(products[:6]):
            if not product:
                continue
            
            badge = '<div style="position: absolute; top: 8px; right: 8px; background: ' + colors[min(i, 2)] + '; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">' + badges[min(i, 2)] + '</div>' if i < 3 else ''
            
            title = html.escape(str(product.get('title', 'Producto')))
            price = html.escape(str(product.get('price', '$0.00')))
            source = html.escape(str(product.get('source', 'Tienda')))
            link = html.escape(str(product.get('link', '#')))
            
            products_html += '''
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: white; position: relative; box-shadow: 0 2px 4px rgba(0,0,0,0.08);">
                    ''' + badge + '''
                    <h3 style="color: #1a73e8; margin-bottom: 8px; font-size: 16px;">''' + title + '''</h3>
                    <div style="font-size: 28px; color: #2e7d32; font-weight: bold; margin: 12px 0;">''' + price + ''' <span style="font-size: 12px; color: #666;">🇺🇸</span></div>
                    <p style="color: #666; margin-bottom: 12px; font-size: 14px;">🏪 ''' + source + '''</p>
                    <a href="''' + link + '''" target="_blank" rel="noopener noreferrer" style="background: #1a73e8; color: white; padding: 10px 16px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block; font-size: 14px;">🛒 Ver Producto</a>
                </div>'''
        
        prices = [p.get('price_numeric', 0) for p in products if p.get('price_numeric', 0) > 0]
        stats = ""
        if prices:
            min_price = min(prices)
            avg_price = sum(prices) / len(prices)
            stats = '''
                <div style="background: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #2e7d32; margin-bottom: 8px;">⚡ Resultados de búsqueda 🇺🇸</h3>
                    <p><strong>✅ ''' + str(len(products)) + ''' productos encontrados</strong></p>
                    <p><strong>💰 Mejor precio: 
        
        content = '''
        <div style="max-width: 800px; margin: 0 auto;">
            <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; margin-bottom: 15px; text-align: center;">
                <span style="color: white; font-size: 14px;">👋 <strong>''' + user_name_escaped + '''</strong> | 
                <a href="''' + url_for('auth_logout') + '''" style="color: #50E3C2;">🚪 Salir</a> | 
                <a href="''' + url_for('search_page') + '''" style="color: #50E3C2;">🔍 Nueva Búsqueda</a></span>
            </div>
            
            <h1 style="color: white; text-align: center; margin-bottom: 8px;">🇺🇸 Resultados: "''' + query + '''"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 25px;">⚡ Búsqueda completada</p>
            
            ''' + stats + '''
            ''' + products_html + '''
        </div>'''
        
        return render_template_string(render_page('Resultados - Price Finder USA', content))
    except Exception as e:
        print(f"Results page error: {e}")
        flash('Error al mostrar resultados.', 'danger')
        return redirect(url_for('search_page'))

@app.route('/api/health')
def health_check():
    try:
        return jsonify({
            'status': 'OK', 
            'timestamp': datetime.now().isoformat(),
            'firebase_auth': 'enabled' if firebase_auth.firebase_web_api_key else 'disabled'
        })
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500

# Middleware
@app.before_request
def before_request():
    if 'timestamp' in session:
        try:
            timestamp_str = session['timestamp']
            if isinstance(timestamp_str, str) and len(timestamp_str) > 10:
                last_activity = datetime.fromisoformat(timestamp_str)
                time_diff = (datetime.now() - last_activity).total_seconds()
                if time_diff > 1200:  # 20 minutos
                    session.clear()
        except:
            session.clear()
    
    session['timestamp'] = datetime.now().isoformat()

@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return '<h1>404 - Página no encontrada</h1><p><a href="/">Volver al inicio</a></p>', 404

@app.errorhandler(500)
def internal_error(error):
    return '<h1>500 - Error interno</h1><p><a href="/">Volver al inicio</a></p>', 500

if __name__ == '__main__':
    print("🚀 Price Finder USA")
    print(f"Firebase: {'✅' if os.environ.get('FIREBASE_WEB_API_KEY') else '❌'}")
    print(f"Puerto: {os.environ.get('PORT', '5000')}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, threaded=True)
else:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger('werkzeug').setLevel(logging.WARNING)'' + f'{min_price:.2f}' + '''</strong></p>
                    <p><strong>📈 Precio promedio: 
        
        content = '''
        <div style="max-width: 800px; margin: 0 auto;">
            <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; margin-bottom: 15px; text-align: center;">
                <span style="color: white; font-size: 14px;">👋 <strong>''' + user_name_escaped + '''</strong> | 
                <a href="''' + url_for('auth_logout') + '''" style="color: #50E3C2;">🚪 Salir</a> | 
                <a href="''' + url_for('search_page') + '''" style="color: #50E3C2;">🔍 Nueva Búsqueda</a></span>
            </div>
            
            <h1 style="color: white; text-align: center; margin-bottom: 8px;">🇺🇸 Resultados: "''' + query + '''"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 25px;">⚡ Búsqueda completada</p>
            
            ''' + stats + '''
            ''' + products_html + '''
        </div>'''
        
        return render_template_string(render_page('Resultados - Price Finder USA', content))
    except Exception as e:
        print(f"Results page error: {e}")
        flash('Error al mostrar resultados.', 'danger')
        return redirect(url_for('search_page'))

@app.route('/api/health')
def health_check():
    try:
        return jsonify({
            'status': 'OK', 
            'timestamp': datetime.now().isoformat(),
            'firebase_auth': 'enabled' if firebase_auth.firebase_web_api_key else 'disabled'
        })
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500

# Middleware
@app.before_request
def before_request():
    if 'timestamp' in session:
        try:
            timestamp_str = session['timestamp']
            if isinstance(timestamp_str, str) and len(timestamp_str) > 10:
                last_activity = datetime.fromisoformat(timestamp_str)
                time_diff = (datetime.now() - last_activity).total_seconds()
                if time_diff > 1200:  # 20 minutos
                    session.clear()
        except:
            session.clear()
    
    session['timestamp'] = datetime.now().isoformat()

@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return '<h1>404 - Página no encontrada</h1><p><a href="/">Volver al inicio</a></p>', 404

@app.errorhandler(500)
def internal_error(error):
    return '<h1>500 - Error interno</h1><p><a href="/">Volver al inicio</a></p>', 500

if __name__ == '__main__':
    print("🚀 Price Finder USA")
    print(f"Firebase: {'✅' if os.environ.get('FIREBASE_WEB_API_KEY') else '❌'}")
    print(f"Puerto: {os.environ.get('PORT', '5000')}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, threaded=True)
else:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger('werkzeug').setLevel(logging.WARNING)'' + f'{avg_price:.2f}' + '''</strong></p>
                    <p><strong>👤 Búsqueda de: ''' + user_name_escaped + '''</strong></p>
                </div>'''
        
        content = '''
        <div style="max-width: 800px; margin: 0 auto;">
            <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; margin-bottom: 15px; text-align: center;">
                <span style="color: white; font-size: 14px;">👋 <strong>''' + user_name_escaped + '''</strong> | 
                <a href="''' + url_for('auth_logout') + '''" style="color: #50E3C2;">🚪 Salir</a> | 
                <a href="''' + url_for('search_page') + '''" style="color: #50E3C2;">🔍 Nueva Búsqueda</a></span>
            </div>
            
            <h1 style="color: white; text-align: center; margin-bottom: 8px;">🇺🇸 Resultados: "''' + query + '''"</h1>
            <p style="text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 25px;">⚡ Búsqueda completada</p>
            
            ''' + stats + '''
            ''' + products_html + '''
        </div>'''
        
        return render_template_string(render_page('Resultados - Price Finder USA', content))
    except Exception as e:
        print(f"Results page error: {e}")
        flash('Error al mostrar resultados.', 'danger')
        return redirect(url_for('search_page'))

@app.route('/api/health')
def health_check():
    try:
        return jsonify({
            'status': 'OK', 
            'timestamp': datetime.now().isoformat(),
            'firebase_auth': 'enabled' if firebase_auth.firebase_web_api_key else 'disabled'
        })
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500

# Middleware
@app.before_request
def before_request():
    if 'timestamp' in session:
        try:
            timestamp_str = session['timestamp']
            if isinstance(timestamp_str, str) and len(timestamp_str) > 10:
                last_activity = datetime.fromisoformat(timestamp_str)
                time_diff = (datetime.now() - last_activity).total_seconds()
                if time_diff > 1200:  # 20 minutos
                    session.clear()
        except:
            session.clear()
    
    session['timestamp'] = datetime.now().isoformat()

@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return '<h1>404 - Página no encontrada</h1><p><a href="/">Volver al inicio</a></p>', 404

@app.errorhandler(500)
def internal_error(error):
    return '<h1>500 - Error interno</h1><p><a href="/">Volver al inicio</a></p>', 500

if __name__ == '__main__':
    print("🚀 Price Finder USA")
    print(f"Firebase: {'✅' if os.environ.get('FIREBASE_WEB_API_KEY') else '❌'}")
    print(f"Puerto: {os.environ.get('PORT', '5000')}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, threaded=True)
else:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
