#upsert.py
import requests
from bs4 import BeautifulSoup
import urllib3
import re
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import shutil
from tqdm import tqdm
import sys
import io

# Importation de la configuration centralisée
from config import PRIMARY_PATTERNS, FIXED_URLS, BASE_DOMAIN, PARENT_NAMESPACE, ANNUAIRE_URL_PATTERNS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Fonctions de nettoyage du HTML ---
def remove_cookie_banner(soup):
    cookie_div = soup.find("div", id="cmplz-cookiebanner-container")
    if cookie_div:
        cookie_div.decompose()

    for el in soup.find_all(lambda tag: any(
        (val and "cmplz" in val.lower())
        for val in tag.attrs.values() if isinstance(val, str)
    )):
        el.decompose()

    for btn in soup.find_all("button"):
        if "gérer le consentement" in btn.get_text(strip=True).lower():
            btn.decompose()

def remove_footer_shortcodes(soup):
    FOOTER_KEYWORDS = []  # À compléter si nécessaire
    for sc in soup.find_all("div", class_="elementor-shortcode"):
        txt = sc.get_text(strip=True).lower()
        if any(kw in txt for kw in FOOTER_KEYWORDS):
            sc.decompose()

    for sec in soup.find_all("section", class_=lambda c: c and "elementor-top-section" in c):
        txt = sec.get_text(strip=True).lower()
        if any(kw in txt for kw in FOOTER_KEYWORDS):
            sec.decompose()

def remove_useless_tags(soup):
    """
    Supprime uniquement les éléments vraiment inutiles, 
    en préservant le contenu interactif et structuré
    """
    # Supprimer les scripts, styles et méta
    for tag in soup(["script", "style", "meta", "noscript", "link"]):
        tag.decompose()
    
    # Supprimer les SVG et iframes (généralement décoratifs)
    for tag in soup(["svg", "iframe"]):
        tag.decompose()
    
    # Pour les images, vérifier si elles ont un alt text informatif
    for img in soup.find_all("img"):
        alt_text = img.get("alt", "").strip()
        # Garder seulement les images avec un alt text informatif
        if not alt_text or len(alt_text) < 5:
            img.decompose()
    
    # Analyser headers, footers, nav et aside individuellement
    for tag_name in ["header", "footer", "nav", "aside"]:
        for element in soup.find_all(tag_name):
            # Compter le contenu textuel significatif
            text_content = element.get_text(strip=True)
            # Compter les liens utiles (non navigation)
            useful_links = 0
            for link in element.find_all("a", href=True):
                href = link.get("href", "")
                link_text = link.get_text(strip=True)
                # Ignorer les liens de navigation typiques
                if not any(nav_word in link_text.lower() for nav_word in ["accueil", "home", "menu", "connexion", "login", "contact"]):
                    if len(link_text) > 10:  # Lien avec du texte substantiel
                        useful_links += 1
            
            # Garder si contient du texte substantiel ou des liens utiles
            if len(text_content) < 100 and useful_links == 0:
                element.decompose()
    
    # Supprimer les éléments vides
    remove_empty_elements(soup)

def remove_empty_elements(soup):
    """
    Supprime les éléments vides qui n'apportent pas de structure
    """
    # Tags qui peuvent être supprimés s'ils sont vides
    removable_if_empty = ["div", "span", "section", "article", "aside"]
    
    # Continuer jusqu'à ce qu'il n'y ait plus de changements
    changed = True
    while changed:
        changed = False
        for tag_name in removable_if_empty:
            for element in soup.find_all(tag_name):
                # Vérifier si l'élément est vraiment vide (pas de texte, pas d'enfants avec contenu)
                if not element.get_text(strip=True) and not element.find_all(["img", "input", "button"]):
                    element.decompose()
                    changed = True
    
    # Supprimer les <br> multiples
    br_tags = soup.find_all("br")
    for i in range(len(br_tags)-1, 0, -1):
        if br_tags[i].find_previous_sibling() and br_tags[i].find_previous_sibling().name == "br":
            br_tags[i].decompose()

def clean_attributes(soup):
    """
    Supprime tous les attributs sauf href pour les liens
    """
    for tag in soup.find_all(True):
        if tag.name == "a":
            # Garder seulement href pour les liens
            keep = {}
            if "href" in tag.attrs:
                keep["href"] = tag.attrs["href"]
            tag.attrs = keep
        else:
            # Supprimer tous les attributs pour les autres tags
            tag.attrs = {}

def simplify_structure(soup):
    """
    Simplifie la structure HTML en supprimant les div imbriqués inutiles
    """
    # Remplacer les divs imbriqués par leur contenu quand c'est possible
    changed = True
    while changed:
        changed = False
        for div in soup.find_all("div"):
            # Si le div n'a qu'un seul enfant direct qui est aussi un div
            children = [child for child in div.children if child.name]
            if len(children) == 1 and children[0].name == "div":
                # Remplacer le parent par l'enfant
                child_div = children[0]
                div.replace_with(child_div)
                changed = True
    
    # Convertir les buttons avec du texte en simples textes (pour les accordéons)
    for button in soup.find_all("button"):
        button_text = button.get_text(strip=True)
        if button_text:
            # Ajouter un espace après les numéros au début
            import re
            # Rechercher les numéros au début du texte et ajouter un espace
            button_text = re.sub(r'^(\d+)([A-Za-z])', r'\1 \2', button_text)
            
            # Créer un h3 pour les titres d'accordéon
            new_h3 = soup.new_tag("h3")
            new_h3.string = button_text
            button.replace_with(new_h3)

def convert_relative_urls(soup, base_url):
    for tag in soup.find_all(True):
        if tag.has_attr("href"):
            tag['href'] = urljoin(base_url, tag['href'])
        if tag.has_attr("src"):
            tag['src'] = urljoin(base_url, tag['src'])
    return soup

def extract_main_content_only(soup):
    """
    Extrait uniquement le contenu principal en supprimant complètement
    navigation, header, footer et autres éléments non informatifs
    """
    # Supprimer complètement tous les éléments de navigation
    for element in soup.find_all(['nav', 'header', 'footer']):
        element.decompose()
    
    # Supprimer les éléments avec des rôles de navigation
    for element in soup.find_all(attrs={'role': ['navigation', 'banner', 'contentinfo']}):
        element.decompose()
    
    # Supprimer les éléments avec des classes/ids typiques de navigation
    nav_patterns = [
        'nav', 'navigation', 'menu', 'header', 'footer', 'sidebar', 'aside',
        'breadcrumb', 'skip', 'search', 'lang', 'cookie', 'banner'
    ]
    
    for pattern in nav_patterns:
        # Supprimer par classe
        for element in soup.find_all(class_=lambda x: x and pattern in str(x).lower()):
            element.decompose()
        
        # Supprimer par id  
        for element in soup.find_all(id=lambda x: x and pattern in str(x).lower()):
            element.decompose()
    
    # Chercher le contenu principal dans l'ordre de priorité
    main_selectors = [
        'main',
        '[role="main"]',
        '.main-content',
        '.content',
        '.page-content',
        'article',
        '.article-content'
    ]
    
    main_content = None
    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    if main_content:
        return main_content
    
    # Si pas de contenu principal identifié, chercher le plus gros bloc de contenu
    # en excluant les éléments de petite taille
    content_blocks = []
    nav_words = ['accueil', 'menu', 'navigation', 'connexion', 'rechercher', 'thematiques', 'actualités', 'evenements']
    
    for div in soup.find_all('div'):
        text = div.get_text(strip=True)
        if len(text) > 500:  # Seuil minimum de contenu plus élevé
            # Vérifier que ce n'est pas principalement de la navigation
            text_lower = text.lower()
            # Si moins de 3 mots de navigation détectés, c'est probablement du contenu
            nav_count = sum(1 for word in nav_words if word in text_lower)
            if nav_count < 3:
                content_blocks.append((div, len(text)))
    
    if content_blocks:
        # Prendre le bloc avec le plus de contenu
        content_blocks.sort(key=lambda x: x[1], reverse=True)
        return content_blocks[0][0]
    
    return soup

def remove_breadcrumbs_and_navigation(soup):
    """
    Supprime les fils d'Ariane et autres éléments de navigation 
    qui peuvent rester dans le contenu principal
    """
    # Supprimer les listes de navigation (souvent des fils d'Ariane)
    for ul in soup.find_all('ul'):
        links = ul.find_all('a')
        if len(links) >= 3:  # Probable fil d'Ariane si 3+ liens
            # Vérifier si contient des mots typiques de navigation
            ul_text = ul.get_text().lower()
            if any(word in ul_text for word in ['accueil', 'thématiques', 'home']):
                ul.decompose()
                continue
    
    # Supprimer les éléments avec peu de contenu mais beaucoup de liens
    for div in soup.find_all('div'):
        text = div.get_text(strip=True)
        links = div.find_all('a')
        if len(text) < 200 and len(links) > 2:
            # Plus de liens que de contenu = probablement navigation
            div.decompose()
    
    # Supprimer les divs qui ne contiennent que des spans avec peu de texte
    for div in soup.find_all('div'):
        spans = div.find_all('span')
        other_elements = [tag for tag in div.find_all() if tag.name != 'span']
        if len(spans) > 0 and len(other_elements) == 0:
            text = div.get_text(strip=True)
            if len(text) < 100 and any(word in text.lower() for word in ['démarche', 'mise à jour', 'transports']):
                div.decompose()

def clean_html_content(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    
    # Nettoyages basiques
    remove_cookie_banner(soup)
    remove_footer_shortcodes(soup)
    
    # NOUVEAU: Extraire uniquement le contenu principal
    main_content = extract_main_content_only(soup)
    
    # Créer un nouveau document avec seulement le contenu principal
    new_soup = BeautifulSoup("", "html.parser")
    new_html = new_soup.new_tag("html")
    new_head = new_soup.new_tag("head")
    new_title = new_soup.new_tag("title")
    new_title.string = page_url
    new_head.append(new_title)
    new_body = new_soup.new_tag("body")
    
    if main_content:
        # Copier le contenu principal
        new_body.append(main_content)
    
    new_html.append(new_head)
    new_html.append(new_body)
    new_soup.append(new_html)
    
    # Appliquer les nettoyages sur le nouveau document
    remove_useless_tags(new_soup)
    remove_breadcrumbs_and_navigation(new_soup)  # NOUVEAU: Nettoyage des fils d'Ariane
    clean_attributes(new_soup)
    simplify_structure(new_soup)
    convert_relative_urls(new_soup, page_url)

    minimal_html = (
        "<!DOCTYPE html>\n"
        f"{new_soup.prettify()}\n"
    )
    return minimal_html

def sanitize_url(url):
    return re.sub(r'\W+', '_', url)

try:
    from annuaire_scraper import scrape_annuaire
    annuaire_scraper_loaded = True
except ImportError:
    annuaire_scraper_loaded = False
    print("[INFO] Module annuaire_scraper non disponible. Le scraping spécifique d'annuaire est désactivé.")

# --- Fonction de scraping d'une URL ---
def process_single_url(url, output_folder, silent=False):
    os.makedirs(output_folder, exist_ok=True)
    
    # Point d'extension pour l'annuaire 
    if annuaire_scraper_loaded and any(pattern in url for pattern in ANNUAIRE_URL_PATTERNS):
        try:
            html_content = scrape_annuaire(url) 
            filename = sanitize_url(url) + ".txt"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            if not silent:
                print(f"[OK] Fichier annuaire enregistré : {filepath}")
            return  # Sortie anticipée
        except Exception as e:
            if not silent:
                print(f"[ERREUR] Échec du scraping d'annuaire pour {url}: {e}")
            # Continuer avec le scraping normal en cas d'échec
    
    try:
        resp = requests.get(url, verify=False)
        if resp.status_code == 200:
            cleaned_html = clean_html_content(resp.content, url)
            filename = sanitize_url(url) + ".txt"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
            if not silent:
                print(f"[OK] Fichier enregistré : {filepath}")
        else:
            if not silent:
                print(f"[ERREUR] HTTP {resp.status_code} en accédant à {url}")
    except Exception as e:
        if not silent:
            print(f"[ERREUR] En traitant {url} : {e}")

# --- Détermination du groupe / namespace ---
def determine_group(url):
    from config import FIXED_URLS, PRIMARY_PATTERNS, PARENT_NAMESPACE, ANNUAIRE_URL_PATTERNS, ANNUAIRE_NAMESPACE
    
    # Traitement spécial pour l'annuaire basé sur la config
    if any(pattern in url for pattern in ANNUAIRE_URL_PATTERNS):
        return ANNUAIRE_NAMESPACE # "child" pour l'annuaire
    
    # Vérifier si l'URL figure dans FIXED_URLS (pour les autres)
    for fixed in FIXED_URLS:
        if url == fixed["url"]:
            return PARENT_NAMESPACE  
    
    # Logique normale pour le reste
    for category, patterns in PRIMARY_PATTERNS.items():
        for pattern in patterns:
            if pattern in url:
                return category
    return None


# --- Traitement multiple des URLs ---
def process_multiple_urls(url_list, output_base_folder, max_workers=4):
    # Supprimer le dossier de sortie s'il existe déjà
    if os.path.exists(output_base_folder):
        print(f"[INFO] Suppression du dossier existant : {output_base_folder}")
        shutil.rmtree(output_base_folder)
    
    # Créer le dossier de sortie
    os.makedirs(output_base_folder, exist_ok=True)
    
    # Filtrer les URLs valides
    valid_urls = []
    skipped_urls = []
    
    for url in url_list:
        group = determine_group(url)
        if group is None:
            skipped_urls.append(url)
            continue
        valid_urls.append((url, group))
    
    # Afficher les statistiques
    print(f"[INFO] {len(valid_urls)} URLs à traiter, {len(skipped_urls)} URLs ignorées")
    
    # Créer les dossiers pour chaque groupe
    groups = set(group for _, group in valid_urls)
    for group in groups:
        output_folder = os.path.join(output_base_folder, group)
        os.makedirs(output_folder, exist_ok=True)
    
    # Traiter les URLs avec une barre de progression
    with tqdm(total=len(valid_urls), desc="Traitement global", unit="page") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            # Soumettre toutes les tâches avec le mode silencieux
            for url, group in valid_urls:
                output_folder = os.path.join(output_base_folder, group)
                future = executor.submit(process_single_url, url, output_folder, True)  # Passer silent=True
                futures.append((future, url))
            
            # Attendre les résultats et mettre à jour la progression
            for future, url in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"[ERREUR] Échec du traitement de {url}: {e}")
                finally:
                    pbar.update(1)
    
    print(f"[INFO] Traitement terminé. Résultats sauvegardés dans {output_base_folder}")

# --- Chargement des URLs depuis plusieurs sitemaps XML ---
def load_urls_from_sitemaps(sitemaps):
    urls = set()
    
    for sitemap in sitemaps:
        try:
            if sitemap.startswith("http"):
                response = requests.get(sitemap, verify=False)
                response.raise_for_status()
                xml_content = response.content
            else:
                with open(sitemap, "rb") as f:
                    xml_content = f.read()

            root = ET.fromstring(xml_content)
            for elem in root.iter():
                if elem.tag.endswith("loc") and elem.text:
                    urls.add(elem.text.strip())
        except Exception as e:
            print(f"[ERREUR] Lecture/parsing du sitemap {sitemap} : {e}")
    return list(urls)

# --- Fonction principale d'exécution du scraping ---
def run_upsert(sitemaps, output_folder, workers=4):
    url_list = load_urls_from_sitemaps(sitemaps)
    print(f"[INFO] {len(url_list)} URLs chargées depuis les sitemaps.")
    process_multiple_urls(url_list, output_folder, max_workers=workers)

# Si on souhaite exécuter directement ce script
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrape des URLs depuis plusieurs sitemaps XML et enregistre dans des dossiers dédiés."
    )
    parser.add_argument("--sitemaps", "-s", nargs="+", required=True,
                        help="Liste de liens ou chemins vers des sitemaps XML.")
    parser.add_argument("--output", "-o", required=True,
                        help="Dossier de base pour sauvegarder les pages scrappées.")
    parser.add_argument("--workers", "-w", type=int, default=4,
                        help="Nombre de workers pour le traitement parallèle.")
    args = parser.parse_args()
    run_upsert(args.sitemaps, args.output, workers=args.workers)