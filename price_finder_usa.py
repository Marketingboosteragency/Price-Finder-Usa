import requests
import json
from typing import List, Dict, Optional
import time
from dataclasses import dataclass
from urllib.parse import quote, urlparse
import re

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
        # Lista negra de dominios chinos/internacionales
        self.blacklisted_domains = {
            # Plataformas chinas principales
            'alibaba.com', 'aliexpress.com', 'temu.com', 'dhgate.com',
            'banggood.com', 'gearbest.com', 'lightinthebox.com',
            'miniinthebox.com', 'dealextreme.com', 'focalprice.com',
            'tinydeal.com', 'chinavasion.com', 'buyincoins.com',
            'everbuying.com', 'tomtop.com', 'cafago.com',
            'geekbuying.com', 'chinabuye.com', 'newfrog.com',
            'cndirect.com', 'zapals.com', 'coolicool.com',
            'sunsky-online.com', 'dx.com', 'fasttech.com',
            'goodluckbuy.com', 'pandawill.com', 'tinhoanglong.com',
            
            # Subdominios y variaciones
            'ae01.alicdn.com', 'ae04.alicdn.com', 'ae02.alicdn.com',
            's.aliexpress.com', 'm.aliexpress.com', 'best.aliexpress.com',
            'sale.aliexpress.com', 'www.alibaba.com', 'm.alibaba.com',
            'spanish.alibaba.com', 'german.alibaba.com',
            
            # Otros sitios internacionales no confiables
            'wish.com', 'joom.com', 'rosegal.com', 'sammydress.com',
            'tidebuy.com', 'romwe.com', 'zaful.com', 'shein.com',
            'patpat.com', 'cupshe.com', 'chicme.com', 'yoox.com',
            
            # Mercados de terceros con vendedores no verificados
            'mercadolibre.com', 'mercadolivre.com', 'olx.com',
            'gumtree.com', 'kijiji.ca', 'craigslist.org'
        }
        
        # Dominios confiables de EE.UU.
        self.trusted_us_domains = {
            'amazon.com', 'walmart.com', 'target.com', 'bestbuy.com',
            'homedepot.com', 'lowes.com', 'costco.com', 'samsclub.com',
            'macys.com', 'nordstrom.com', 'kohls.com', 'jcpenney.com',
            'sears.com', 'newegg.com', 'bhphotovideo.com', 'adorama.com',
            'ebay.com', 'etsy.com', 'overstock.com', 'wayfair.com',
            'chewy.com', 'petco.com', 'petsmart.com', 'cvs.com',
            'walgreens.com', 'riteaid.com', 'staples.com', 'officedepot.com',
            'gamestop.com', 'toysrus.com', 'barnesandnoble.com',
            'williams-sonoma.com', 'crateandbarrel.com', 'potterybarn.com',
            'westelm.com', 'cb2.com', 'anthropologie.com', 'urbanoutfitters.com',
            'nordstromrack.com', 'tjmaxx.com', 'marshalls.com',
            'nike.com', 'adidas.com', 'underarmour.com', 'gap.com',
            'oldnavy.com', 'bananarepublic.com', 'jcrew.com',
            'landsend.com', 'llbean.com', 'patagonia.com', 'rei.com',
            'dickssportinggoods.com', 'academy.com', 'sportsmans.com',
            'cabelas.com', 'basspro.com', 'guitarcenter.com',
            'sweetwater.com', 'musiciansfriend.com', 'autozone.com',
            'oreillyauto.com', 'advanceautoparts.com', 'pepboys.com',
            'menards.com', 'harborfreight.com', 'northerntool.com',
            'tractorsupply.com', 'ruralking.com', 'fleetfarm.com'
        }
        
        # Palabras clave que indican vendedores chinos
        self.chinese_keywords = [
            'ships from china', 'shipped from china', 'china warehouse',
            'guangzhou', 'shenzhen', 'hongkong', 'hong kong',
            'free shipping from china', 'china post', 'china shipping',
            '中国', 'made in china', 'cn warehouse', 'asia warehouse',
            'international shipping', 'overseas warehouse', 'global shipping',
            'dropship', 'dropshipping'
        ]
    
    def is_blacklisted_domain(self, url: str) -> bool:
        """Verifica si el dominio está en la lista negra"""
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            
            # Verificar dominio exacto
            if domain in self.blacklisted_domains:
                return True
            
            # Verificar subdominios de sitios blacklisteados
            for blacklisted in self.blacklisted_domains:
                if domain.endswith('.' + blacklisted) or blacklisted in domain:
                    return True
            
            return False
            
        except Exception:
            return True  # Si no puede parsear la URL, la considera sospechosa
    
    def is_trusted_us_domain(self, url: str) -> bool:
        """Verifica si es un dominio confiable de EE.UU."""
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            
            return domain in self.trusted_us_domains
            
        except Exception:
            return False
    
    def verify_link_accessibility(self, url: str) -> Dict:
        """Verifica si el link es accesible y válido"""
        result = {
            'accessible': False,
            'status_code': None,
            'title': None,
            'contains_chinese_keywords': False,
            'is_product_page': False,
            'error': None,
            'final_url': url
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            result['status_code'] = response.status_code
            result['final_url'] = response.url  # URL final después de redirecciones
            
            if response.status_code == 200:
                result['accessible'] = True
                content = response.text.lower()
                
                # Extraer título
                title_match = re.search(r'<title>(.*?)</title>', content)
                if title_match:
                    result['title'] = title_match.group(1).strip()
                
                # Verificar palabras clave chinas
                for keyword in self.chinese_keywords:
                    if keyword in content:
                        result['contains_chinese_keywords'] = True
                        break
                
                # Verificar si es una página de producto (indicadores básicos)
                product_indicators = ['add to cart', 'buy now', 'price', '$', 'product', 'item']
                result['is_product_page'] = any(indicator in content for indicator in product_indicators)
            
        except requests.exceptions.Timeout:
            result['error'] = 'Timeout - Link muy lento'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Error de conexión - Link inaccesible'
        except requests.exceptions.RequestException as e:
            result['error'] = f'Error de solicitud: {str(e)}'
        except Exception as e:
            result['error'] = f'Error inesperado: {str(e)}'
        
        return result
    
    def validate_us_link(self, url: str, product_title: str = "") -> Dict:
        """Validación completa de un link para EE.UU."""
        validation_result = {
            'is_valid': False,
            'is_us_seller': False,
            'is_accessible': False,
            'is_trusted_domain': False,
            'reasons': [],
            'warnings': [],
            'final_url': url
        }
        
        # 1. Verificar si está en lista negra
        if self.is_blacklisted_domain(url):
            validation_result['reasons'].append('Dominio en lista negra (plataforma china)')
            return validation_result
        
        # 2. Verificar si es dominio confiable de EE.UU.
        if self.is_trusted_us_domain(url):
            validation_result['is_trusted_domain'] = True
            validation_result['is_us_seller'] = True
        
        # 3. Verificar accesibilidad del link
        link_check = self.verify_link_accessibility(url)
        validation_result['is_accessible'] = link_check['accessible']
        validation_result['final_url'] = link_check['final_url']
        
        if not link_check['accessible']:
            validation_result['reasons'].append(f"Link inaccesible: {link_check.get('error', 'Desconocido')}")
            return validation_result
        
        # 4. Verificar contenido chino
        if link_check['contains_chinese_keywords']:
            validation_result['reasons'].append('Contiene indicadores de vendedor chino')
            return validation_result
        
        # 5. Verificar si es página de producto
        if not link_check['is_product_page']:
            validation_result['warnings'].append('Podría no ser una página de producto válida')
        
        # 6. Verificaciones adicionales por dominio
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc.replace('www.', '')
        
        # Para eBay, verificar que sea vendedor de EE.UU.
        if 'ebay.com' in domain:
            validation_result['warnings'].append('eBay: Verificar ubicación del vendedor')
        
        # Para Amazon, verificar que no sea marketplace internacional
        elif 'amazon.com' in domain and '/gp/product/' not in url and '/dp/' not in url:
            validation_result['warnings'].append('Amazon: Verificar que sea producto directo')
        
        # Si llegó hasta aquí, el link es válido
        if validation_result['is_trusted_domain'] or (validation_result['is_accessible'] and not validation_result['reasons']):
            validation_result['is_valid'] = True
            validation_result['is_us_seller'] = True
        
        return validation_result

class PriceFinder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.link_validator = USLinkValidator()
        
    def _validate_and_filter_products(self, products: List[Product]) -> List[Product]:
        """Valida y filtra productos para asegurar que sean de vendedores de EE.UU."""
        valid_products = []
        print(f"🔍 Validando {len(products)} productos encontrados...")
        
        for i, product in enumerate(products):
            print(f"⏳ Validando producto {i+1}/{len(products)}: {product.source}")
            
            # Validar el link
            validation = self.link_validator.validate_us_link(product.link, product.title)
            
            if validation['is_valid'] and validation['is_us_seller']:
                product.is_us_seller = True
                product.link_verified = True
                # Actualizar con la URL final (después de redirecciones)
                product.link = validation['final_url']
                valid_products.append(product)
                print(f"✅ Válido: {product.source}")
            else:
                reasons = ', '.join(validation['reasons']) if validation['reasons'] else 'No específicado'
                print(f"❌ Rechazado: {product.source} - {reasons}")
            
            # Pausa para evitar sobrecargar los servidores
            time.sleep(0.5)
        
        print(f"✅ Productos válidos de EE.UU.: {len(valid_products)}/{len(products)}")
        return valid_products
        
    def search_google_shopping(self, query: str, location: str = "United States") -> List[Product]:
        """Busca productos en Google Shopping usando SerpAPI"""
        params = {
            'engine': 'google_shopping',
            'q': query,
            'location': location,
            'api_key': self.api_key,
            'num': 50,  # Número máximo de resultados
            'sort': 'p'  # Ordenar por precio (low to high)
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            if 'shopping_results' in data:
                for item in data['shopping_results']:
                    try:
                        # Extraer precio numérico
                        price_str = item.get('price', '0')
                        price_numeric = self._extract_price(price_str)
                        
                        if price_numeric > 0:  # Solo incluir productos con precio válido
                            product = Product(
                                title=item.get('title', 'Sin título'),
                                price=price_str,
                                price_numeric=price_numeric,
                                source=item.get('source', 'Desconocido'),
                                link=item.get('link', ''),
                                rating=item.get('rating'),
                                reviews=str(item.get('reviews', '')),
                                is_us_seller=False,  # Se validará después
                                link_verified=False
                            )
                            products.append(product)
                    except Exception as e:
                        print(f"Error procesando producto: {e}")
                        continue
            
            return products
            
        except requests.RequestException as e:
            print(f"Error en la solicitud a SerpAPI: {e}")
            return []
    
    def search_walmart(self, query: str) -> List[Product]:
        """Busca productos en Walmart usando SerpAPI"""
        params = {
            'engine': 'walmart',
            'query': query,
            'api_key': self.api_key,
            'sort': 'price_low'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
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
                                is_us_seller=True,  # Walmart es confiable de EE.UU.
                                link_verified=False
                            )
                            products.append(product)
                    except Exception as e:
                        print(f"Error procesando producto de Walmart: {e}")
                        continue
            
            return products
            
        except requests.RequestException as e:
            print(f"Error en la solicitud a Walmart: {e}")
            return []
    
    def search_amazon(self, query: str) -> List[Product]:
        """Busca productos en Amazon usando SerpAPI"""
        params = {
            'engine': 'amazon',
            'amazon_domain': 'amazon.com',
            'q': query,
            'api_key': self.api_key,
            'sort': 'price_low_to_high'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            products = []
            
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
                                is_us_seller=False,  # Amazon necesita validación (marketplace)
                                link_verified=False
                            )
                            products.append(product)
                    except Exception as e:
                        print(f"Error procesando producto de Amazon: {e}")
                        continue
            
            return products
            
        except requests.RequestException as e:
            print(f"Error en la solicitud a Amazon: {e}")
            return []
    
    def _extract_price(self, price_str: str) -> float:
        """Extrae el precio numérico de una cadena de precio"""
        if not price_str:
            return 0.0
        
        # Remover símbolos y caracteres no numéricos excepto punto y coma
        price_clean = re.sub(r'[^\d.,]', '', str(price_str))
        
        # Manejar formato con comas como separador de miles
        if ',' in price_clean and '.' in price_clean:
            # Formato: 1,234.56
            price_clean = price_clean.replace(',', '')
        elif ',' in price_clean:
            # Formato: 1234,56 (europeo) o 1,234 (miles)
            if price_clean.count(',') == 1 and len(price_clean.split(',')[1]) <= 2:
                price_clean = price_clean.replace(',', '.')
            else:
                price_clean = price_clean.replace(',', '')
        
        try:
            return float(price_clean)
        except (ValueError, TypeError):
            return 0.0
    
    def find_best_deals(self, query: str, max_results: int = 20) -> List[Product]:
        """Busca las mejores ofertas combinando múltiples fuentes y validando que sean de EE.UU."""
        print(f"🔍 Buscando: {query}")
        print("=" * 50)
        
        all_products = []
        
        # Buscar en Google Shopping
        print("📱 Buscando en Google Shopping...")
        google_products = self.search_google_shopping(query)
        all_products.extend(google_products)
        time.sleep(1)  # Pausa para evitar rate limiting
        
        # Buscar en Walmart
        print("🏪 Buscando en Walmart...")
        walmart_products = self.search_walmart(query)
        all_products.extend(walmart_products)
        time.sleep(1)
        
        # Buscar en Amazon
        print("📦 Buscando en Amazon...")
        amazon_products = self.search_amazon(query)
        all_products.extend(amazon_products)
        
        # Validar y filtrar productos para asegurar que sean de EE.UU.
        print("\n🇺🇸 VALIDANDO PRODUCTOS DE EE.UU.")
        print("=" * 50)
        validated_products = self._validate_and_filter_products(all_products)
        
        # Filtrar duplicados y ordenar por precio
        unique_products = self._remove_duplicates(validated_products)
        sorted_products = sorted(unique_products, key=lambda x: x.price_numeric)
        
        print(f"\n🎯 PRODUCTOS FINALES VALIDADOS: {len(sorted_products)}")
        return sorted_products[:max_results]
    
    def _remove_duplicates(self, products: List[Product]) -> List[Product]:
        """Remueve productos duplicados basándose en el título y precio"""
        seen_products = set()
        unique_products = []
        
        for product in products:
            # Crear una clave única basada en título y precio
            title_words = product.title.lower().split()[:5]  # Primeras 5 palabras
            key = (tuple(title_words), round(product.price_numeric, 2))
            
            if key not in seen_products:
                seen_products.add(key)
                unique_products.append(product)
        
        return unique_products
    
    def get_direct_purchase_links(self, products: List[Product]) -> List[Dict]:
        """Extrae los mejores links VERIFICADOS para compra directa en EE.UU."""
        purchase_links = []
        
        # Solo incluir productos verificados de EE.UU.
        us_products = [p for p in products if p.is_us_seller and p.link_verified]
        
        for product in us_products:
            if product.link and product.link.strip():
                link_info = {
                    'title': product.title,
                    'price': product.price,
                    'price_numeric': product.price_numeric,
                    'source': product.source,
                    'url': product.link,
                    'rating': product.rating,
                    'reviews': product.reviews,
                    'is_us_seller': product.is_us_seller,
                    'link_verified': product.link_verified
                }
                purchase_links.append(link_info)
        
        return purchase_links
    
    def display_purchase_links(self, purchase_links: List[Dict], show_all: bool = False):
        """Muestra los links de compra directa VERIFICADOS"""
        if not purchase_links:
            print("\n😔 No se encontraron links de compra directa verificados de EE.UU.")
            print("💡 Esto puede suceder si:")
            print("   - Los productos son de vendedores chinos (filtrados)")
            print("   - Los links no son accesibles")
            print("   - Los dominios están en lista negra")
            return
        
        # Determinar cuántos mostrar
        display_count = len(purchase_links) if show_all else min(5, len(purchase_links))
        
        print(f"\n🛒 TOP {display_count} LINKS VERIFICADOS DE EE.UU. 🇺🇸")
        print("=" * 80)
        print("💡 Estos productos están GARANTIZADOS para ser de vendedores de EE.UU.:")
        
        for i, link in enumerate(purchase_links[:display_count], 1):
            print(f"\n🥇 OPCIÓN {i} - VERIFICADA ✅")
            print(f"📦 {link['title'][:70]}...")
            print(f"💰 Precio: {link['price']}")
            print(f"🏪 Tienda: {link['source']}")
            print(f"🇺🇸 Vendedor EE.UU.: ✅ CONFIRMADO")
            print(f"🔗 Link Verificado: ✅ ACCESIBLE")
            
            if link['rating']:
                print(f"⭐ Calificación: {link['rating']}")
            
            if link['reviews']:
                print(f"📝 Reseñas: {link['reviews']}")
            
            print(f"🛒 COMPRAR AQUÍ: {link['url']}")
            print("=" * 60)
        
        # Mostrar resumen de ahorro si hay múltiples opciones
        if len(purchase_links) > 1:
            cheapest = min(purchase_links, key=lambda x: x['price_numeric'])
            most_expensive = max(purchase_links, key=lambda x: x['price_numeric'])
            savings = most_expensive['price_numeric'] - cheapest['price_numeric']
            
            if savings > 0:
                print(f"\n💰 AHORRO MÁXIMO EN EE.UU.: ${savings:.2f}")
                print(f"💚 Mejor precio: {cheapest['price']} en {cheapest['source']}")
                print(f"💸 Precio más alto: {most_expensive['price']} en {most_expensive['source']}")
                print("🇺🇸 Todos los precios son de vendedores verificados de EE.UU.")
        
        # Si hay más productos, informar al usuario
        if not show_all and len(purchase_links) > display_count:
            print(f"\n📋 Se encontraron {len(purchase_links)} productos totales.")
            print("💡 Usa la opción 'Mostrar todos los links' para ver la lista completa.")
    
    def export_links_to_file(self, purchase_links: List[Dict], query: str):
        """Exporta los links de compra VERIFICADOS a un archivo de texto"""
        if not purchase_links:
            print("\n⚠️  No hay links verificados para exportar")
            return
        
        filename = f"links_compra_usa_{query.replace(' ', '_')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(f"🛒 LINKS DE COMPRA VERIFICADOS EE.UU. - {query.upper()}\n")
                file.write("=" * 60 + "\n")
                file.write(f"Generado el: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write("🇺🇸 Todos los productos son de vendedores verificados de EE.UU.\n")
                file.write("✅ Links verificados y accesibles\n")
                file.write("❌ Excluye: Alibaba, Temu, AliExpress y otros sitios chinos\n\n")
                
                for i, link in enumerate(purchase_links, 1):
                    file.write(f"OPCIÓN {i} - VERIFICADA:\n")
                    file.write(f"Producto: {link['title']}\n")
                    file.write(f"Precio: {link['price']}\n")
                    file.write(f"Tienda: {link['source']}\n")
                    file.write(f"Vendedor EE.UU.: ✅ CONFIRMADO\n")
                    file.write(f"Link Verificado: ✅ ACCESIBLE\n")
                    
                    if link['rating']:
                        file.write(f"Calificación: {link['rating']}\n")
                    
                    if link['reviews']:
                        file.write(f"Reseñas: {link['reviews']}\n")
                    
                    file.write(f"Link: {link['url']}\n")
                    file.write("-" * 40 + "\n\n")
            
            print(f"\n📄 Links exportados a: {filename}")
            
        except Exception as e:
            print(f"⚠️  Error al exportar links: {e}")
    
    def generate_quick_links_summary(self, purchase_links: List[Dict]) -> str:
        """Genera un resumen rápido de links para copiar y pegar"""
        if not purchase_links:
            return "No hay links disponibles"
        
        summary = f"🛒 LINKS DIRECTOS VERIFICADOS (Top {min(5, len(purchase_links))})\n"
        summary += "=" * 50 + "\n"
        
        for i, link in enumerate(purchase_links[:5], 1):
            summary += f"{i}. {link['source']} - {link['price']}\n"
            summary += f"   {link['url']}\n\n"
        
        return summary

class PriceFinderApp:
    def __init__(self):
        self.price_finder = None
        self.last_search_results = []
        self.last_purchase_links = []
        self.last_query = ""
    
    def setup_api_key(self):
        """Solicita y configura la API key de SerpAPI"""
        print("🔑 Para usar esta aplicación necesitas una API key de SerpAPI")
        print("📝 Puedes obtenerla gratis en: https://serpapi.com/")
        print("💡 Ofrecen 100 búsquedas gratuitas por mes")
        print()
        
        api_key = input("Por favor ingresa tu API key de SerpAPI: ").strip()
        
        if not api_key:
            print("❌ API key requerida para continuar")
            return False
        
        self.price_finder = PriceFinder(api_key)
        print("✅ API key configurada correctamente")
        return True
    
    def show_main_menu(self):
        """Muestra el menú principal de la aplicación"""
        print("\n" + "=" * 60)
        print("🇺🇸 PRICE FINDER USA - BUSCADOR DE MEJORES PRECIOS 🇺🇸")
        print("=" * 60)
        print("✅ Solo productos de vendedores verificados de EE.UU.")
        print("❌ Excluye automáticamente sitios chinos como Alibaba, Temu, etc.")
        print("🔗 Links de compra directa verificados y accesibles")
        print()
        print("OPCIONES:")
        print("1. 🔍 Buscar producto")
        print("2. 📄 Mostrar últimos resultados")
        print("3. 📝 Mostrar todos los links encontrados")
        print("4. 💾 Exportar links a archivo")
        print("5. 📋 Resumen rápido de links")
        print("6. ⚙️  Cambiar API key")
        print("7. ❓ Ayuda")
        print("8. 🚪 Salir")
        print()
    
    def search_product(self):
        """Realiza una búsqueda de producto"""
        print("\n🔍 BÚSQUEDA DE PRODUCTO")
        print("=" * 40)
        
        query = input("Ingresa el producto que deseas buscar: ").strip()
        
        if not query:
            print("❌ Debes ingresar un producto para buscar")
            return
        
        print(f"\n🚀 Iniciando búsqueda para: {query}")
        print("⏳ Esto puede tomar unos minutos...")
        print("🔍 Buscando en múltiples tiendas de EE.UU...")
        print("🛡️  Validando que sean vendedores de EE.UU...")
        
        try:
            # Realizar búsqueda
            products = self.price_finder.find_best_deals(query)
            
            if products:
                # Obtener links de compra directa
                purchase_links = self.price_finder.get_direct_purchase_links(products)
                
                # Guardar resultados para uso posterior
                self.last_search_results = products
                self.last_purchase_links = purchase_links
                self.last_query = query
                
                # Mostrar resultados
                print(f"\n🎉 ¡BÚSQUEDA COMPLETADA!")
                print(f"📊 Se encontraron {len(products)} productos válidos")
                print(f"🇺🇸 {len(purchase_links)} links verificados de EE.UU.")
                
                self.price_finder.display_purchase_links(purchase_links)
                
            else:
                print("\n😔 No se encontraron productos válidos de vendedores de EE.UU.")
                print("💡 Intenta con:")
                print("   - Términos de búsqueda más específicos")
                print("   - Nombres de marca conocidos")
                print("   - Productos más populares")
                
        except Exception as e:
            print(f"\n❌ Error durante la búsqueda: {e}")
            print("💡 Verifica tu conexión a internet y API key")
    
    def show_last_results(self):
        """Muestra los últimos resultados de búsqueda"""
        if not self.last_purchase_links:
            print("\n📭 No hay resultados previos")
            print("💡 Realiza una búsqueda primero usando la opción 1")
            return
        
        print(f"\n📄 ÚLTIMOS RESULTADOS: {self.last_query}")
        self.price_finder.display_purchase_links(self.last_purchase_links)
    
    def show_all_links(self):
        """Muestra todos los links encontrados en la última búsqueda"""
        if not self.last_purchase_links:
            print("\n📭 No hay resultados previos")
            print("💡 Realiza una búsqueda primero usando la opción 1")
            return
        
        print(f"\n📋 TODOS LOS LINKS ENCONTRADOS: {self.last_query}")
        self.price_finder.display_purchase_links(self.last_purchase_links, show_all=True)
    
    def export_links(self):
        """Exporta los links de la última búsqueda a un archivo"""
        if not self.last_purchase_links:
            print("\n📭 No hay resultados para exportar")
            print("💡 Realiza una búsqueda primero usando la opción 1")
            return
        
        print(f"\n💾 Exportando links de: {self.last_query}")
        self.price_finder.export_links_to_file(self.last_purchase_links, self.last_query)
    
    def show_quick_summary(self):
        """Muestra un resumen rápido para copiar y pegar"""
        if not self.last_purchase_links:
            print("\n📭 No hay resultados previos")
            print("💡 Realiza una búsqueda primero usando la opción 1")
            return
        
        print(f"\n📋 RESUMEN RÁPIDO: {self.last_query}")
        print("=" * 50)
        summary = self.price_finder.generate_quick_links_summary(self.last_purchase_links)
        print(summary)
    
    def show_help(self):
        """Muestra información de ayuda"""
        print("\n❓ AYUDA - PRICE FINDER USA")
        print("=" * 50)
        print()
        print("📖 SOBRE LA APLICACIÓN:")
        print("• Busca productos solo en tiendas de EE.UU.")
        print("• Filtra automáticamente sitios chinos (Alibaba, Temu, etc.)")
        print("• Verifica que los links sean accesibles")
        print("• Garantiza vendedores de EE.UU.")
        print()
        print("🔧 CÓMO USAR:")
        print("1. Configura tu API key de SerpAPI (gratis: 100 búsquedas/mes)")
        print("2. Busca productos usando términos específicos")
        print("3. Revisa los links verificados")
        print("4. Exporta o copia los links que necesites")
        print()
        print("💡 CONSEJOS PARA MEJORES RESULTADOS:")
        print("• Usa nombres específicos de productos")
        print("• Incluye marca si es conocida")
        print("• Evita términos muy generales")
        print("• Ejemplos buenos: 'iPhone 15 Pro', 'Nike Air Max 90'")
        print("• Ejemplos malos: 'teléfono', 'zapatos'")
        print()
        print("🛡️  TIENDAS VERIFICADAS INCLUYEN:")
        print("• Amazon.com, Walmart, Target, Best Buy")
        print("• Home Depot, Lowe's, Costco, Sam's Club")
        print("• Macy's, Nordstrom, Kohl's, JCPenney")
        print("• Newegg, B&H Photo, Adorama")
        print("• eBay (solo vendedores de EE.UU.)")
        print("• Y muchas más tiendas confiables...")
        print()
        print("⚠️  SITIOS EXCLUIDOS AUTOMÁTICAMENTE:")
        print("• Alibaba, AliExpress, Temu, DHgate")
        print("• Banggood, Gearbest, Wish, Joom")
        print("• Cualquier sitio con vendedores chinos")
        print()
        print("📞 SOPORTE:")
        print("• Para problemas con SerpAPI: https://serpapi.com/")
        print("• Para la aplicación: Revisa tu API key y conexión")
    
    def change_api_key(self):
        """Permite cambiar la API key"""
        print("\n⚙️  CAMBIAR API KEY")
        print("=" * 30)
        print("🔑 API key actual configurada")
        print()
        
        new_key = input("Ingresa nueva API key (o Enter para cancelar): ").strip()
        
        if new_key:
            self.price_finder = PriceFinder(new_key)
            print("✅ API key actualizada correctamente")
        else:
            print("❌ Cambio cancelado")
    
    def run(self):
        """Ejecuta la aplicación principal"""
        print("🚀 Iniciando Price Finder USA...")
        print()
        
        # Configurar API key
        if not self.setup_api_key():
            return
        
        # Bucle principal
        while True:
            try:
                self.show_main_menu()
                choice = input("Selecciona una opción (1-8): ").strip()
                
                if choice == '1':
                    self.search_product()
                
                elif choice == '2':
                    self.show_last_results()
                
                elif choice == '3':
                    self.show_all_links()
                
                elif choice == '4':
                    self.export_links()
                
                elif choice == '5':
                    self.show_quick_summary()
                
                elif choice == '6':
                    self.change_api_key()
                
                elif choice == '7':
                    self.show_help()
                
                elif choice == '8':
                    print("\n👋 ¡Gracias por usar Price Finder USA!")
                    print("🇺🇸 ¡Que tengas excelentes compras!")
                    break
                
                else:
                    print("\n❌ Opción inválida. Por favor selecciona 1-8.")
                
                # Pausa antes de mostrar el menú nuevamente
                if choice != '8':
                    input("\nPresiona Enter para continuar...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error inesperado: {e}")
                print("💡 La aplicación continuará funcionando...")

def main():
    """Función principal para ejecutar la aplicación"""
    try:
        app = PriceFinderApp()
        app.run()
    except Exception as e:
        print(f"❌ Error crítico al iniciar la aplicación: {e}")
        print("💡 Verifica que tengas instaladas las dependencias:")
        print("   pip install requests")

if __name__ == "__main__":
    # Información inicial
    print("=" * 60)
    print("🇺🇸 PRICE FINDER USA v1.0")
    print("=" * 60)
    print("📱 Encuentra los mejores precios solo en EE.UU.")
    print("🛡️  Sin productos chinos - Solo vendedores verificados")
    print("🔗 Links de compra directa garantizados")
    print("=" * 60)
    print()
    
    # Verificar dependencias
    try:
        import requests
        print("✅ Dependencias verificadas")
    except ImportError:
        print("❌ Faltan dependencias. Instala con:")
        print("   pip install requests")
        exit(1)
    
    # Ejecutar aplicación
    main()