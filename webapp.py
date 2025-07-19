# HTML Templates
INDEX_HTML = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇺🇸 Price Finder USA</title>
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
        .setup-card {{ 
            background: white; border-radius: 16px; padding: 40px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 600px; margin: 0 auto;
        }}
        .input-group {{ margin-bottom: 20px; }}
        .input-group label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #374151; }}
        .input-group input {{ 
            width: 100%; padding: 16px; border: 2px solid #e5e7eb; border-radius: 12px; 
            font-size: 16px; transition: all 0.3s ease;
        }}
        .input-group input:focus {{ outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }}
        .btn {{ 
            background: #3b82f6; color: white; border: none; padding: 16px 24px; 
            border-radius: 12px; cursor: pointer; font-size: 16px; font-weight: 600; 
            transition: all 0.3s ease; text-decoration: none; display: inline-block;
        }}
        .btn:hover {{ background: #2563eb; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3); }}
        .btn-secondary {{ background: #6b7280; }}
        .btn-secondary:hover {{ background: #4b5563; }}
        .features {{ background: #f0f9ff; padding: 25px; border-radius: 12px; border-left: 4px solid #3b82f6; margin-top: 20px; }}
        .error {{ background: #fef2f2; border: 2px solid #fecaca; color: #991b1b; padding: 20px; border-radius: 12px; margin: 20px 0; }}
        .hidden {{ display: none !important; }}
        .loading {{ text-align: center; padding: 20px; }}
        .spinner {{ width: 30px; height: 30px; border: 3px solid #e5e7eb; border-left: 3px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
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
                    <li>🎯 <strong>NUEVO:</strong> Búsquedas ultra específicas</li>
                    <li>🔑 <strong>NUEVO:</strong> Cambia API key cuando se agoten créditos</li>
                </ul>
            </div>
        </div>

        <div id="loading" class="loading hidden">
            <div class="spinner"></div>
            <p>Configurando API key...</p>
        </div>

        <div id="error" class="error hidden"></div>
    </div>

    {API_KEY_MODAL}

    <script>
        document.getElementById('setupForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const apiKey = formData.get('api_key').trim();
            
            if (!apiKey) {{
                showError('Por favor ingresa tu API key');
                return;
            }}
            
            showLoading();
            
            fetch('/setup', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    window.location.href = '/search';
                }} else {{
                    showError(data.error || 'Error al configurar API key');
                }}
            }})
            .catch(error => {{
                showError('Error de conexión: ' + error.message);
            }});
        }});

        function showLoading() {{
            document.getElementById('setupCard').style.display = 'none';
            document.getElementById('loading').classList.remove('hidden');
        }}

        function showError(message) {{
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('setupCard').style.display = 'block';
            
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
            
            setTimeout(() => {{
                errorDiv.classList.add('hidden');
            }}, 5000);
        }}
    </script>
</body>
</html>
"""

SEARCH_HTML = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Búsqueda - Price Finder USA</title>
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
        .search-card {{ 
            background: white; border-radius: 16px; padding: 40px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); max-width: 600px; margin: 0 auto;
        }}
        .search-bar {{ display: flex; gap: 12px; margin-bottom: 20px; }}
        .search-bar input {{ 
            flex: 1; padding: 16px; border: 2px solid #e5e7eb; border-radius: 12px; 
            font-size: 16px; transition: all 0.3s ease;
        }}
        .btn {{ 
            background: #3b82f6; color: white; border: none; padding: 16px 24px; 
            border-radius: 12px; cursor: pointer; font-size: 16px; font-weight: 600; 
        }}
        .btn:hover {{ background: #2563eb; transform: translateY(-2px); }}
        .btn-secondary {{ background: #6b7280; }}
        .btn-secondary:hover {{ background: #4b5563; }}
        .loading {{ text-align: center; padding: 40px; background: white; border-radius: 16px; margin: 20px 0; }}
        .spinner {{ width: 50px; height: 50px; border: 5px solid #e5e7eb; border-left: 5px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .hidden {{ display: none !important; }}
        .error {{ background: #fef2f2; border: 2px solid #fecaca; color: #991b1b; padding: 20px; border-radius: 12px; margin: 20px 0; }}
        .progress-bar {{ background: #e5e7eb; border-radius: 10px; margin: 20px 0; height: 8px; }}
        .progress-fill {{ background: #3b82f6; height: 100%; border-radius: 10px; transition: width 0.5s ease; width: 0%; }}
        .tips {{ background: #fef3c7; padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 4px solid #f59e0b; }}
        .api-key-button {{
            position: fixed; bottom: 20px; right: 20px; background: #f59e0b; color: white;
            border: none; padding: 12px 16px; border-radius: 50px; cursor: pointer;
            font-weight: 600; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
            transition: all 0.3s ease; z-index: 100;
        }}
        .api-key-button:hover {{
            background: #d97706; transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Buscar Productos</h1>
            <p>Búsqueda ultra específica en tiendas de EE.UU.</p>
        </div>

        <div class="search-card" id="searchCard">
            <form id="searchForm">
                <div class="search-bar">
                    <input type="text" id="searchQuery" placeholder="Ej: cinta adhesiva papel azul 2 pulgadas, iPhone 15 Pro azul 128GB..." required>
                    <button type="submit" class="btn">🎯 Buscar</button>
                </div>
            </form>

            <div class="tips">
                <h4>💡 Tips para búsquedas más específicas:</h4>
                <ul style="margin: 10px 0 0 20px; color: #92400e;">
                    <li><strong>Incluye el color:</strong> "azul", "rojo", "negro"</li>
                    <li><strong>Especifica medidas:</strong> "2 pulgadas", "1/2 inch"</li>
                    <li><strong>Menciona el material:</strong> "papel", "tela", "plástico"</li>
                    <li><strong>Ejemplo:</strong> "cinta adhesiva papel azul 2 pulgadas"</li>
                </ul>
            </div>

            <p style="text-align: center; color: #6b7280; margin-top: 20px;">
                🏪 Buscaremos en: Amazon, Walmart y más tiendas de EE.UU.<br>
                ⏱️ Búsqueda inteligente puede tomar 2-3 minutos.
            </p>
        </div>

        <div id="searchLoading" class="loading hidden">
            <div class="spinner"></div>
            <h3>🎯 Realizando búsqueda específica...</h3>
            <p id="loadingMessage">Analizando tu consulta...</p>
            
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p id="progressText">0% completado</p>

            <button type="button" class="btn btn-secondary" style="margin-top: 20px;" onclick="cancelSearch()">
                ❌ Cancelar búsqueda
            </button>
        </div>

        <div id="searchError" class="error hidden"></div>
    </div>

    <!-- Botón flotante para cambiar API key -->
    <button class="api-key-button" onclick="openApiModal()" title="Cambiar API Key">
        🔑 Cambiar API
    </button>

    {API_KEY_MODAL}

    <script>
        let searchInProgress = false;

        document.getElementById('searchForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            if (searchInProgress) return;

            const query = document.getElementById('searchQuery').value.trim();
            if (!query) return;

            startSearch(query);
        }});

        function startSearch(query) {{
            searchInProgress = true;
            document.getElementById('searchCard').style.display = 'none';
            document.getElementById('searchLoading').classList.remove('hidden');
            
            simulateProgress();

            fetch('/api/search', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ query: query }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    window.location.href = '/results';
                }} else {{
                    showError(data.error || 'Error en la búsqueda');
                }}
            }})
            .catch(error => {{
                showError('Error de conexión: ' + error.message);
            }});
        }}

        function simulateProgress() {{
            const messages = [
                'Analizando tu consulta específica...',
                'Generando consultas inteligentes...',
                'Buscando en Google Shopping...',
                'Consultando Walmart...',
                'Buscando en Amazon...',
                'Calculando relevancia de productos...',
                'Validando vendedores de EE.UU...',
                'Organizando resultados por relevancia...'
            ];

            let currentStep = 0;
            let progress = 0;

            const interval = setInterval(() => {{
                progress += Math.random() * 10 + 5;
                if (progress > 95) progress = 95;

                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressText').textContent = Math.round(progress) + '% completado';

                if (currentStep < messages.length) {{
                    document.getElementById('loadingMessage').textContent = messages[currentStep];
                    currentStep++;
                }}

                if (progress >= 95) {{
                    clearInterval(interval);
                }}
            }}, 1000);
        }}

        function showError(message) {{
            searchInProgress = false;
            document.getElementById('searchLoading').classList.add('hidden');
            document.getElementById('searchCard').style.display = 'block';
            
            const errorDiv = document.getElementById('searchError');
            errorDiv.innerHTML = message;
            errorDiv.classList.remove('hidden');
            
            // Si el error es sobre créditos, mostrar botón para cambiar API
            if (message.includes('créditos') || message.includes('credits')) {{
                errorDiv.innerHTML += '<br><br><button onclick="openApiModal()" class="btn" style="margin-top: 10px;">🔑 Cambiar API Key</button>';
            }}
        }}

        function cancelSearch() {{
            searchInProgress = false;
            document.getElementById('searchLoading').classList.add('hidden');
            document.getElementById('searchCard').style.display = 'block';
        }}
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
    
    # Probar la API key antes de guardarla
    try:
        price_finder = PriceFinder(api_key)
        test_result = price_finder.test_api_key()
        
        if not test_result['valid']:
            return jsonify({'error': f"API key inválida: {test_result['message']}"}), 400
        
        session['api_key'] = api_key
        return jsonify({
            'success': True, 
            'message': 'API key configurada correctamente',
            'api_info': test_result.get('message', '')
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar API key: {str(e)}'}), 400

@app.route('/api/change-key', methods=['POST'])
def change_api_key():
    """Endpoint para cambiar la API key"""
    data = request.get_json()
    new_api_key = data.get('new_api_key', '').strip()
    
    if not new_api_key:
        return jsonify({'error': 'Nueva API key requerida'}), 400
    
    # Probar la nueva API key
    try:
        price_finder = PriceFinder(new_api_key)
        test_result = price_finder.test_api_key()
        
        if not test_result['valid']:
            return jsonify({
                'success': False,
                'error': f"API key inválida: {test_result['message']}"
            }), 400
        
        # Si es válida, actualizarla en la sesión
        session['api_key'] = new_api_key
        
        return jsonify({
            'success': True,
            'message': 'API key cambiada exitosamente',
            'api_info': test_result.get('message', '')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al verificar nueva API key: {str(e)}'
        }), 400

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
        error_message = str(e)
        if "créditos" in error_message or "credits" in error_message or "quota" in error_message:
            return jsonify({
                'error': '❌ Se agotaron los créditos de tu API key. Haz clic en "🔑 Cambiar API" para usar una nueva API key.'
            }), 400
        
        return jsonify({'error': f'Error en la búsqueda: {error_message}'}), 500

@app.route('/results')
def results_page():
    if 'last_search' not in session:
        return redirect(url_for('search_page'))
    
    search_data = session['last_search']
    products = search_data['products']
    query = search_data['query']
    
    # Crear HTML de productos con score de relevancia
    products_html = ""
    if products:
        for i, product in enumerate(products):
            title = product['title'][:80] + ("..." if len(product['title']) > 80 else "")
            price = f"${product['price_numeric']:.2f}"
            source = product['source']
            link = product['link']
            rating = product.get('rating', '')
            reviews = product.get('reviews', '')
            relevance = product.get('relevance_score', 0)
            
            # Escapar caracteres especiales para HTML
            title = title.replace("'", "&#39;").replace('"', "&quot;")
            source = source.replace("'", "&#39;").replace('"', "&quot;")
            
            # Icono de relevancia
            relevance_icon = "🎯" if relevance >= 50 else "✅" if relevance >= 30 else "👍"
            relevance_text = "Muy relevante" if relevance >= 50 else "Relevante" if relevance >= 30 else "Relacionado"
            
            # Badge de posición para los primeros 3
            position_badge = ""
            if i == 0:
                position_badge = '<div style="position: absolute; top: -10px; left: 15px; background: #f59e0b; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥇 MÁS RELEVANTE</div>'
            elif i == 1:
                position_badge = '<div style="position: absolute; top: -10px; left: 15px; background: #6b7280; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥈 2º LUGAR</div>'
            elif i == 2:
                position_badge = '<div style="position: absolute; top: -10px; left: 15px; background: #cd7c0e; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">🥉 3º LUGAR</div>'
            
            products_html += f"""
                <div class="product-card" style="position: relative;">
                    {position_badge}
                    <div class="verified-badge">🇺🇸 Verificado</div>
                    <div class="product-title">{title}</div>
                    <div class="product-price">{price}</div>
                    <div class="product-source">{source}</div>
                    <div style="color: #6b7280; margin-bottom: 15px;">
                        {relevance_icon} {relevance_text} ({relevance:.0f}%)
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
                <h3>😔 No se encontraron productos específicos</h3>
                <p style="margin: 15px 0; color: #6b7280;">
                    No se encontraron productos que coincidan específicamente con tu búsqueda.<br>
                    Intenta ser más específico con colores, medidas o materiales.
                </p>
                <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h4>💡 Sugerencias:</h4>
                    <ul style="text-align: left; color: #92400e; margin: 10px 0 0 20px;">
                        <li>Incluye el color específico</li>
                        <li>Menciona las medidas exactas</li>
                        <li>Especifica el material</li>
                        <li>Usa marcas conocidas si las conoces</li>
                    </ul>
                </div>
                <a href="/search" class="btn">🔍 Intentar Nueva Búsqueda</a>
            </div>
        """
    
    # Crear resumen si hay productos
    summary_html = ""
    if products:
        min_price = min(p['price_numeric'] for p in products)
        max_price = max(p['price_numeric'] for p in products)
        avg_relevance = sum(p.get('relevance_score', 0) for p in products) / len(products)
        
        summary_html = f"""
            <div class="results-summary">
                <h3>✅ Búsqueda Específica Completada</h3>
                <p><strong>{len(products)} productos relevantes</strong> encontrados de vendedores de EE.UU.</p>
                <p>💰 Rango de precios: ${min_price:.2f} - ${max_price:.2f}</p>
                <p>🎯 Relevancia promedio: {avg_relevance:.0f}% - Ordenados por relevancia</p>
            </div>
        """
    
    # HTML completo de resultados
    results_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultados Específicos - Price Finder USA</title>
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
            .api-key-button {{
                position: fixed; bottom: 20px; right: 20px; background: #f59e0b; color: white;
                border: none; padding: 12px 16px; border-radius: 50px; cursor: pointer;
                font-weight: 600; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
                transition: all 0.3s ease; z-index: 100;
            }}
            .api-key-button:hover {{
                background: #d97706; transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
            }}
            @media (max-width: 768px) {{
                .container {{ padding: 15px; }}
                .header h1 {{ font-size: 2rem; }}
                .actions {{ flex-direction: column; }}
                .product-card {{ padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Resultados Específicos</h1>
                <p>"{query}" - {len(products)} productos altamente relevantes</p>
            </div>

            {summary_html}

            <div class="actions">
                <a href="/search" class="btn">🔍 Nueva Búsqueda</a>
                <button onclick="window.print()" class="btn btn-secondary">📄 Imprimir Resultados</button>
                <button onclick="openApiModal()" class="btn" style="background: #f59e0b;">🔑 Cambiar API Key</button>
            </div>

            {products_html}
        </div>

        <!-- Botón flotante para cambiar API key -->
        <button class="api-key-button" onclick="openApiModal()" title="Cambiar API Key si se agotaron créditos">
            🔑 Cambiar API
        </button>

        {API_KEY_MODAL}
    </body>
    </html>"""
    
    return results_html

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'OK', 'message': 'Price Finder USA está funcionando'})

@app.route('/api/test')
def test_endpoint():
    """Endpoint de prueba para verificar que la app funciona"""
    return jsonify({
        'status': 'SUCCESS',
        'message': '🇺🇸 Price Finder USA con cambio de API key está funcionando!',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1 - Con cambio de API Key'
    })

@app.route('/api/key-status')
def api_key_status():
    """Endpoint para verificar el estado de la API key actual"""
    if 'api_key' not in session:
        return jsonify({'error': 'No hay API key configurada'}), 400
    
    try:
        price_finder = PriceFinder(session['api_key'])
        test_result = price_finder.test_api_key()
        
        return jsonify({
            'valid': test_result['valid'],
            'message': test_result['message'],
            'api_key_preview': session['api_key'][:8] + '...' if session['api_key'] else 'No configurada'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': f'Error al verificar API key: {str(e)}',
            'api_key_preview': session['api_key'][:8] + '...' if session['api_key'] else 'No configurada'
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)from flask import Flask, request, jsonify, session, redirect, url_for
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
    relevance_score: float = 0.0

class QueryProcessor:
    """Procesador avanzado de consultas para búsquedas más específicas"""
    
    def __init__(self):
        # Palabras clave importantes que deben mantenerse
        self.important_keywords = {
            # Colores
            'colors': ['azul', 'rojo', 'verde', 'amarillo', 'negro', 'blanco', 'rosa', 'morado', 
                      'naranja', 'gris', 'blue', 'red', 'green', 'yellow', 'black', 'white', 
                      'pink', 'purple', 'orange', 'gray', 'grey'],
            
            # Medidas y tamaños
            'measurements': ['pulgada', 'pulgadas', 'inch', 'inches', 'cm', 'mm', 'metro', 'metros',
                           'pie', 'pies', 'foot', 'feet', 'yarda', 'yardas', 'yard', 'yards'],
            
            # Números (importantes para medidas)
            'numbers': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '½', '1/2', '1/4', '3/4'],
            
            # Materiales
            'materials': ['papel', 'tela', 'plastico', 'metal', 'aluminio', 'paper', 'fabric', 
                         'plastic', 'aluminum', 'vinyl', 'vinilo'],
            
            # Tipos de productos específicos
            'product_types': ['cinta', 'tape', 'adhesiva', 'adhesive', 'masking', 'duct', 'scotch']
        }
    
    def extract_key_attributes(self, query: str) -> Dict:
        """Extrae atributos clave de la consulta"""
        query_lower = query.lower()
        attributes = {
            'colors': [],
            'measurements': [],
            'numbers': [],
            'materials': [],
            'product_types': [],
            'original_query': query
        }
        
        # Buscar cada tipo de atributo
        for attr_type, keywords in self.important_keywords.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    attributes[attr_type].append(keyword)
        
        return attributes
    
    def generate_specific_queries(self, original_query: str) -> List[str]:
        """Genera consultas más específicas basadas en los atributos"""
        attributes = self.extract_key_attributes(original_query)
        queries = []
        
        # Consulta original
        queries.append(original_query)
        
        # Si tiene color + medida, hacer búsqueda muy específica
        if attributes['colors'] and attributes['measurements']:
            for color in attributes['colors'][:2]:  # Máximo 2 colores
                for measurement in attributes['measurements'][:2]:  # Máximo 2 medidas
                    specific_query = f"{color} {measurement} {original_query}"
                    queries.append(specific_query)
        
        # Si tiene números + tipo de producto
        if attributes['numbers'] and attributes['product_types']:
            for number in attributes['numbers'][:3]:
                for product_type in attributes['product_types'][:2]:
                    specific_query = f"{number} {product_type} {original_query}"
                    queries.append(specific_query)
        
        # Búsquedas con comillas para frases exactas (más específicas)
        if len(original_query.split()) >= 3:
            queries.append(f'"{original_query}"')
        
        # Consultas con atributos específicos
        if attributes['colors']:
            for color in attributes['colors'][:2]:
                queries.append(f"{original_query} {color}")
        
        if attributes['materials']:
            for material in attributes['materials'][:2]:
                queries.append(f"{material} {original_query}")
        
        # Remover duplicados manteniendo orden
        unique_queries = []
        for q in queries:
            if q not in unique_queries:
                unique_queries.append(q)
        
        return unique_queries[:8]  # Máximo 8 consultas para no sobrecargar

class ProductMatcher:
    """Matcher avanzado para calcular relevancia de productos"""
    
    def __init__(self):
        self.query_processor = QueryProcessor()
    
    def calculate_relevance_score(self, product_title: str, original_query: str) -> float:
        """Calcula score de relevancia de 0-100"""
        title_lower = product_title.lower()
        query_lower = original_query.lower()
        
        score = 0.0
        
        # Extraer atributos de la consulta original
        query_attributes = self.query_processor.extract_key_attributes(original_query)
        
        # 1. Coincidencia exacta de frase (peso alto: 40 puntos)
        if query_lower in title_lower:
            score += 40
        
        # 2. Palabras clave individuales (peso medio: 5 puntos por palabra)
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 2 and word in title_lower:  # Ignorar palabras muy cortas
                score += 5
        
        # 3. Atributos específicos (peso alto)
        # Colores (15 puntos por color encontrado)
        for color in query_attributes['colors']:
            if color.lower() in title_lower:
                score += 15
        
        # Medidas (15 puntos por medida encontrada)
        for measurement in query_attributes['measurements']:
            if measurement.lower() in title_lower:
                score += 15
        
        # Números (10 puntos por número encontrado)
        for number in query_attributes['numbers']:
            if number in title_lower or number in product_title:
                score += 10
        
        # Materiales (10 puntos por material)
        for material in query_attributes['materials']:
            if material.lower() in title_lower:
                score += 10
        
        # Tipos de producto (10 puntos)
        for product_type in query_attributes['product_types']:
            if product_type.lower() in title_lower:
                score += 10
        
        # 4. Penalización por productos irrelevantes
        irrelevant_terms = ['unrelated', 'different', 'other', 'various', 'mixed']
        for term in irrelevant_terms:
            if term in title_lower:
                score -= 10
        
        # 5. Bonus por marca conocida
        known_brands = ['3m', 'scotch', 'gorilla', 'duck', 'frogtape', 'tesa']
        for brand in known_brands:
            if brand in title_lower:
                score += 5
        
        return min(score, 100)  # Máximo 100 puntos

class USLinkValidator:
    def __init__(self):
        self.blacklisted_domains = {
            'alibaba.com', 'aliexpress.com', 'temu.com', 'dhgate.com',
            'banggood.com', 'gearbest.com', 'lightinthebox.com',
            'wish.com', 'joom.com', 'shein.com', 'chinabrands.com'
        }
        
        self.trusted_us_domains = {
            'amazon.com', 'walmart.com', 'target.com', 'bestbuy.com',
            'homedepot.com', 'lowes.com', 'costco.com', 'samsclub.com',
            'lumberliquidators.com', 'llflooring.com', 'harborfreight.com',
            'menards.com', 'acehardware.com', 'tapemanblue.com', 'uline.com',
            'staples.com', 'officedepot.com', 'grainger.com'
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
        self.query_processor = QueryProcessor()
        self.product_matcher = ProductMatcher()
        
    def test_api_key(self) -> Dict:
        """Prueba si la API key es válida"""
        test_params = {
            'engine': 'google',
            'q': 'test',
            'api_key': self.api_key,
            'num': 1
        }
        
        try:
            response = requests.get(self.base_url, params=test_params, timeout=10)
            data = response.json()
            
            if 'error' in data:
                return {
                    'valid': False,
                    'error': data['error'],
                    'message': 'API key inválida o sin créditos'
                }
            
            # Verificar si tiene créditos
            if 'search_metadata' in data:
                return {
                    'valid': True,
                    'message': 'API key válida y con créditos disponibles',
                    'credits_info': data.get('search_metadata', {})
                }
            
            return {'valid': True, 'message': 'API key válida'}
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'message': 'Error al verificar API key'
            }
        
    def _validate_and_filter_products(self, products: List[Product], original_query: str) -> List[Product]:
        """Valida productos y calcula relevancia"""
        valid_products = []
        
        for product in products:
            # Validar link
            validation = self.link_validator.validate_us_link(product.link, product.title)
            
            if validation['is_valid'] and validation['is_us_seller']:
                product.is_us_seller = True
                product.link_verified = True
                product.link = validation['final_url']
                
                # Calcular relevancia
                product.relevance_score = self.product_matcher.calculate_relevance_score(
                    product.title, original_query
                )
                
                # Solo agregar productos con relevancia mínima
                if product.relevance_score >= 10:  # Mínimo 10 puntos de relevancia
                    valid_products.append(product)
        
        return valid_products
        
    def search_google_shopping(self, query: str, location: str = "United States") -> List[Product]:
        """Búsqueda mejorada en Google Shopping"""
        all_products = []
        
        # Generar consultas específicas
        specific_queries = self.query_processor.generate_specific_queries(query)
        
        for search_query in specific_queries:
            params = {
                'engine': 'google_shopping',
                'q': search_query,
                'location': location,
                'api_key': self.api_key,
                'num': 30  # Menos resultados por consulta pero más consultas específicas
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                # Verificar si hay error de créditos
                if 'error' in data:
                    raise Exception(f"Error de API: {data['error']}")
                
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
                
                time.sleep(1.5)  # Pausa más larga entre consultas
                
            except requests.RequestException as e:
                if "credits" in str(e).lower() or "quota" in str(e).lower():
                    raise Exception("Se agotaron los créditos de tu API key. Cambia a una nueva API key.")
                continue
        
        return all_products
    
    def search_walmart(self, query: str) -> List[Product]:
        """Búsqueda específica en Walmart"""
        all_products = []
        
        # Usar consultas específicas también para Walmart
        specific_queries = self.query_processor.generate_specific_queries(query)[:3]  # Solo 3 para Walmart
        
        for search_query in specific_queries:
            params = {
                'engine': 'walmart',
                'query': search_query,
                'api_key': self.api_key
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                # Verificar si hay error de créditos
                if 'error' in data:
                    raise Exception(f"Error de API: {data['error']}")
                
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
                                all_products.append(product)
                        except Exception:
                            continue
                
                time.sleep(1)
                
            except requests.RequestException as e:
                if "credits" in str(e).lower() or "quota" in str(e).lower():
                    raise Exception("Se agotaron los créditos de tu API key. Cambia a una nueva API key.")
                continue
        
        return all_products
    
    def search_amazon_specific(self, query: str) -> List[Product]:
        """Búsqueda específica en Amazon"""
        all_products = []
        
        # Consultas más específicas para Amazon
        amazon_queries = self.query_processor.generate_specific_queries(query)[:4]
        
        for search_query in amazon_queries:
            params = {
                'engine': 'amazon',
                'amazon_domain': 'amazon.com',
                'q': search_query,
                'api_key': self.api_key
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                # Verificar si hay error de créditos
                if 'error' in data:
                    raise Exception(f"Error de API: {data['error']}")
                
                if 'search_results' in data:
                    for item in data['search_results']:
                        try:
                            price_str = item.get('price', '0')
                            price_numeric = self._extract_price(price_str)
                            
                            if price_numeric > 0:
                                product = Product(
                                    title=item.get('title', 'Sin título'),
                                    price=price_str,
                                    price_numeric=price_numeric,
                                    source='Amazon',
                                    link=item.get('link', ''),
                                    rating=str(item.get('rating', '')),
                                    reviews=str(item.get('reviews_count', '')),
                                    is_us_seller=False,
                                    link_verified=False
                                )
                                all_products.append(product)
                        except Exception:
                            continue
                
                time.sleep(1)
                
            except requests.RequestException as e:
                if "credits" in str(e).lower() or "quota" in str(e).lower():
                    raise Exception("Se agotaron los créditos de tu API key. Cambia a una nueva API key.")
                continue
        
        return all_products
    
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
    
    def find_best_deals(self, query: str, max_results: int = 25) -> List[Product]:
        """Búsqueda mejorada con mayor precisión"""
        all_products = []
        
        print(f"🔍 Búsqueda específica para: {query}")
        
        try:
            # Buscar en Google Shopping con consultas específicas
            print("📱 Buscando en Google Shopping...")
            google_products = self.search_google_shopping(query)
            all_products.extend(google_products)
            print(f"   ✅ Google Shopping: {len(google_products)} productos encontrados")
            
            # Buscar en Walmart
            print("🏪 Buscando en Walmart...")
            walmart_products = self.search_walmart(query)
            all_products.extend(walmart_products)
            print(f"   ✅ Walmart: {len(walmart_products)} productos encontrados")
            
            # Buscar en Amazon
            print("📦 Buscando en Amazon...")
            amazon_products = self.search_amazon_specific(query)
            all_products.extend(amazon_products)
            print(f"   ✅ Amazon: {len(amazon_products)} productos encontrados")
            
        except Exception as e:
            if "créditos" in str(e) or "credits" in str(e) or "quota" in str(e):
                raise Exception("❌ Se agotaron los créditos de tu API key. Ve a 'Cambiar API Key' para usar una nueva.")
            raise e
        
        print(f"\n📊 TOTAL ANTES DE FILTRAR: {len(all_products)} productos")
        
        # Validar productos y calcular relevancia
        print("\n🇺🇸 VALIDANDO Y CALCULANDO RELEVANCIA...")
        validated_products = self._validate_and_filter_products(all_products, query)
        
        # Filtrar duplicados
        unique_products = self._remove_duplicates(validated_products)
        
        # Ordenar por relevancia primero, luego por precio
        sorted_products = sorted(unique_products, 
                               key=lambda x: (-x.relevance_score, x.price_numeric))
        
        print(f"\n🎯 PRODUCTOS FINALES RELEVANTES: {len(sorted_products)}")
        
        if sorted_products:
            print(f"💡 Producto más relevante: {sorted_products[0].title[:50]}... (Score: {sorted_products[0].relevance_score})")
            print(f"💰 Rango de precios: ${sorted_products[0].price_numeric:.2f} - ${sorted_products[-1].price_numeric:.2f}")
        
        return sorted_products[:max_results]
    
    def _remove_duplicates(self, products: List[Product]) -> List[Product]:
        """Remueve productos duplicados mejorado"""
        seen_products = set()
        unique_products = []
        
        for product in products:
            # Normalizar título para comparación
            title_normalized = re.sub(r'[^\w\s]', '', product.title.lower())
            title_words = set(title_normalized.split()[:8])  # Usar más palabras para comparación
            
            price_rounded = round(product.price_numeric, 2)
            
            # Crear clave más específica
            key = (frozenset(title_words), price_rounded, product.source.lower())
            
            if key not in seen_products:
                seen_products.add(key)
                unique_products.append(product)
        
        return unique_products

# Componente de cambio de API key
API_KEY_MODAL = """
<!-- Modal para cambiar API key -->
<div id="apiKeyModal" class="modal hidden">
    <div class="modal-content">
        <div class="modal-header">
            <h3>🔑 Cambiar API Key</h3>
            <span class="close" onclick="closeApiModal()">&times;</span>
        </div>
        <div class="modal-body">
            <p style="margin-bottom: 15px; color: #6b7280;">
                Ingresa una nueva API key de SerpAPI:
            </p>
            <div class="input-group">
                <input type="text" id="newApiKey" placeholder="Nueva API key..." style="width: 100%; padding: 12px; border: 2px solid #e5e7eb; border-radius: 8px;">
            </div>
            <div style="text-align: center; margin: 15px 0;">
                <a href="https://serpapi.com/" target="_blank" style="color: #3b82f6; font-size: 14px;">
                    📝 Obtener nueva API key gratuita →
                </a>
            </div>
            <div class="modal-actions">
                <button onclick="changeApiKey()" class="btn">✅ Cambiar API Key</button>
                <button onclick="closeApiModal()" class="btn btn-secondary">❌ Cancelar</button>
            </div>
        </div>
    </div>
</div>

<style>
.modal {
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
}

.modal-content {
    background: white;
    border-radius: 16px;
    max-width: 500px;
    width: 90%;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 25px;
    border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
    color: #1f2937;
    margin: 0;
}

.close {
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
    color: #6b7280;
}

.close:hover {
    color: #1f2937;
}

.modal-body {
    padding: 25px;
}

.modal-actions {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin-top: 20px;
}

.api-key-button {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #f59e0b;
    color: white;
    border: none;
    padding: 12px 16px;
    border-radius: 50px;
    cursor: pointer;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    transition: all 0.3s ease;
    z-index: 100;
}

.api-key-button:hover {
    background: #d97706;
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
}

@media (max-width: 768px) {
    .modal-content {
        width: 95%;
        margin: 20px;
    }
    
    .api-key-button {
        bottom: 10px;
        right: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }
}
</style>

<script>
function openApiModal() {
    document.getElementById('apiKeyModal').classList.remove('hidden');
}

function closeApiModal() {
    document.getElementById('apiKeyModal').classList.add('hidden');
    document.getElementById('newApiKey').value = '';
}

function changeApiKey() {
    const newKey = document.getElementById('newApiKey').value.trim();
    
    if (!newKey) {
        alert('Por favor ingresa una API key válida');
        return;
    }
    
    // Mostrar loading
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '⏳ Verificando...';
    btn.disabled = true;
    
    fetch('/api/change-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_api_key: newKey })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✅ API key cambiada exitosamente!');
            closeApiModal();
            // Recargar la página después de un momento
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            alert('❌ Error: ' + (data.error || 'API key inválida'));
        }
    })
    .catch(error => {
        alert('❌ Error de conexión: ' + error.message);
    })
    .finally(() => {
        btn.textContent = originalText;
        btn.disabled = false;
    });
}

// Cerrar modal al hacer clic fuera
document.addEventListener('click', function(e) {
    const modal = document.getElementById('apiKeyModal');
    if (e.target === modal) {
        closeApiModal();
    }
});
</script>
"""

# HTML Templates
INDEX_HTML = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇺🇸 Price Finder USA</title>
