#annuaire_scraper.py
import asyncio
from playwright.async_api import async_playwright
import time
import re
import os
import json
import hashlib

def generate_acronym(title):
    """Génère un acronyme à partir des lettres majuscules du titre."""
    acronym = ''.join(char for char in title if char.isupper())
    return acronym if acronym else title[:3].upper()  # Fallback si pas de majuscules

def html_escape(text):
    """Échappe les caractères spéciaux HTML"""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def markdown_to_html(markdown_content, target_url):
    """
    Convertit le contenu Markdown en HTML simplifié compatible avec le pipeline.
    Version améliorée qui gère les attributs multilignes.
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>{target_url}</title>
</head>
<body>
"""
    
    # Liste pour suivre l'état du parsing
    in_service = False
    current_attr = None
    attr_content = []
    
    # Parcourir le contenu Markdown ligne par ligne
    lines = markdown_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Titre principal (h1)
        if line.startswith('# '):
            html += f"  <h1>{line[2:]}</h1>\n"
        
        # Sous-titre d'un service (h2)
        elif line.startswith('## '):
            if in_service:
                html += "  </div>\n"
            in_service = True
            html += f"  <div class=\"service\">\n    <h2>{line[3:]}</h2>\n"
        
        # Ligne avec un attribut gras (comme **Adresse :** ou **Téléphone :**)
        elif line.startswith('**') and '**' in line[2:]:
            # Si nous étions en train de collecter un attribut, finalisons-le
            if current_attr is not None:
                html += process_multiline_attribute(current_attr, attr_content)
                attr_content = []
            
            # Extraction du nouvel attribut
            attr_end = line.find('**', 2)
            current_attr = line[2:attr_end]
            
            # S'il y a du contenu après l'attribut sur la même ligne
            content_start = line[attr_end+2:].strip()
            if content_start:
                attr_content.append(content_start)
            else:
                # Sinon, commencer à collecter le contenu des lignes suivantes
                j = i + 1
                while j < len(lines) and not lines[j].startswith('**') and not lines[j].startswith('#') and not lines[j].startswith('---'):
                    if lines[j].strip():  # Ne pas ajouter les lignes vides
                        attr_content.append(lines[j].strip())
                    j += 1
                i = j - 1  # Ajuster i pour le prochain cycle (il sera incrémenté à la fin)
        
        # Ligne italique (introduction)
        elif line.startswith('_') and line.endswith('_'):
            html += f"  <p>{line[1:-1]}</p>\n"
            
        # Séparateur
        elif line.startswith('---'):
            # Finaliser l'attribut en cours si nécessaire
            if current_attr is not None:
                html += process_multiline_attribute(current_attr, attr_content)
                current_attr = None
                attr_content = []
            
            if in_service:
                html += "  </div>\n"
                html += "  <hr>\n"
                in_service = False
        
        i += 1
    
    # Finaliser le dernier attribut si nécessaire
    if current_attr is not None:
        html += process_multiline_attribute(current_attr, attr_content)
    
    # Fermer la dernière div si nécessaire
    if in_service:
        html += "  </div>\n"
    
    # Fermer le HTML
    html += "</body>\n</html>"
    
    return html

def process_multiline_attribute(attr_name, content_lines):
    """
    Traite un attribut multilignes et retourne le HTML correspondant.
    Gère spécifiquement les liens et les contenus sur plusieurs lignes.
    """
    if not content_lines:
        return f'    <p><strong>{attr_name}</strong> </p>\n'
    
    content = content_lines[0]
    
    # Cas spécial pour les liens
    if content.startswith('[') and '](' in content:
        link_text_start = content.find('[')
        link_text_end = content.find(']', link_text_start)
        link_url_start = content.find('(', link_text_end)
        link_url_end = content.find(')', link_url_start)
        
        if link_text_start >= 0 and link_text_end > 0 and link_url_start > 0 and link_url_end > 0:
            link_text = content[link_text_start+1:link_text_end]
            link_url = content[link_url_start+1:link_url_end]
            
            return f'    <p><strong>{attr_name}</strong> <a href="{link_url}">{link_text}</a></p>\n'
    elif content == "Information non disponible" or content == "Information not available":
        return f'    <p><strong>{attr_name}</strong> {content}</p>\n'
    
    # Cas multilignes (comme une adresse)
    if len(content_lines) > 1:
        html_content = "<br>".join(content_lines)
        return f'    <p><strong>{attr_name}</strong><br>{html_content}</p>\n'
    
    # Cas standard (une seule ligne)
    return f'    <p><strong>{attr_name}</strong> {content}</p>\n'

async def process_service(page, service_id, source_url, is_english=False, retry_timeout=60000):
    """Traite un seul service de manière asynchrone"""
    try:
        # Construit l'URL avec le paramètre entity
        url_with_entity = f"{source_url}?entity={service_id}"
        
        # Navigue vers cette URL avec timeout configurable
        await page.goto(url_with_entity, timeout=retry_timeout)
        await page.wait_for_load_state('networkidle')
        
        # Extrais les informations
        nom_element = await page.query_selector("div.text-xl.font-bold")
        nom = await nom_element.inner_text() if nom_element else ("Information not available" if is_english else "Information non disponible")
        
        # Génère l'acronyme
        acronyme = generate_acronym(nom)
        
        adresse_element = await page.query_selector("div.text-secondary > p")
        adresse = await adresse_element.inner_text() if adresse_element else ("Information not available" if is_english else "Information non disponible")
        
        horaires_element = await page.query_selector("p.font-normal.text-secondary.pr-16")
        horaires = await horaires_element.inner_text() if horaires_element else ("Information not available" if is_english else "Information non disponible")
        
        telephone_element = await page.query_selector("div.font-semibold.text-interaction > a[href^='tel:']")
        telephone = await telephone_element.inner_text() if telephone_element else ("Information not available" if is_english else "Information non disponible")
        
        # Correction: utilisation correcte du locator
        nous_ecrire = "Information not available" if is_english else "Information non disponible"
        page_entite = "Information not available" if is_english else "Information non disponible"
        
        # Chercher les liens par leur texte - méthode correcte avec locator
        for link in await page.query_selector_all("a"):
            link_text = await link.inner_text()
            if ("Contact us" in link_text if is_english else "Nous écrire" in link_text):
                nous_ecrire = await link.get_attribute("href") or ("Information not available" if is_english else "Information non disponible")
            elif ("View organization page" in link_text if is_english else "Voir la page de l'entité" in link_text):
                page_entite = await link.get_attribute("href") or ("Information not available" if is_english else "Information non disponible")
        
        # Stocke les informations dans la liste
        return {
            'nom': nom,
            'acronyme': acronyme,
            'adresse': adresse,
            'horaires': horaires,
            'telephone': telephone,
            'lien_nous_ecrire': nous_ecrire,
            'lien_page_entite': page_entite
        }
        
    except Exception as e:
        print(f"[ERREUR] Traitement du service {service_id}: {e}")
        # Enregistre une entrée avec un message d'erreur
        error_msg = "Error extracting data" if is_english else "Erreur lors de l'extraction des données"
        not_available = "Information not available" if is_english else "Information non disponible"
        return {
            'nom': f"Service {service_id}",
            'acronyme': f"S{service_id[:2] if isinstance(service_id, str) else service_id}",
            'adresse': error_msg,
            'horaires': error_msg,
            'telephone': error_msg,
            'lien_nous_ecrire': not_available,
            'lien_page_entite': not_available
        }

async def scrape_annuaire_async(url):
    """Version asynchrone du scraper d'annuaire"""
    # Détecter si c'est la version anglaise
    is_english = "/en/" in url
    
    if is_english:
        source_url = "https://monservicepublic.gouv.mc/en/directory-of-government-services"
    else:
        source_url = "https://monservicepublic.gouv.mc/annuaire-des-services-administratifs"
    
    target_url = url
    
    print(f"[INFO] Début du scraping spécialisé de l'annuaire {'(EN)' if is_english else '(FR)'}: {target_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Créer un contexte de navigateur
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        
        # Obtenir la liste des services
        main_page = await context.new_page()
        await main_page.goto(source_url, timeout=60000)
        await main_page.wait_for_load_state('networkidle')
        
        # Sélecteur des services
        service_selector = "div.space-y-2 a"
        services = await main_page.query_selector_all(service_selector)
        
        service_ids = []
        for service in services:
            service_id = await service.get_attribute('id')
            if service_id:
                service_ids.append(service_id)
            else:
                print("[AVERT] Un service sans ID a été trouvé.")
        
        total_services = len(service_ids)
        print(f"[INFO] Nombre de services trouvés : {total_services}")
        
        # Traiter les services en parallèle
        services_data = []
        
        # Nombre de requêtes simultanées
        concurrent_limit = 8
        
        # Diviser les services en groupes pour limiter les requêtes simultanées
        for i in range(0, total_services, concurrent_limit):
            batch = service_ids[i:i+concurrent_limit]
            
            # Créer des pages pour chaque service dans ce groupe
            pages = []
            for _ in range(len(batch)):
                pages.append(await context.new_page())
            
            # Traiter chaque service de ce groupe
            tasks = []
            for j, service_id in enumerate(batch):
                tasks.append(process_service(pages[j], service_id, source_url, is_english))
            
            # Attendre que toutes les tâches de ce groupe soient terminées
            batch_results = await asyncio.gather(*tasks)
            services_data.extend(batch_results)
            
            # Fermer les pages après utilisation
            for page in pages:
                await page.close()
            
            print(f"[INFO] Traitement terminé: {min(i+len(batch), total_services)}/{total_services} services")
        
        # Fermer le navigateur
        await browser.close()
    
    # Générer le Markdown
    if is_english:
        markdown_content = "# Directory of Government Services\n\n"
        markdown_content += "_Complete list of Monaco's government services._\n\n"
    else:
        markdown_content = "# Annuaire des Services Administratifs\n\n"
        markdown_content += "_Liste complète des services administratifs de Monaco._\n\n"
    
    for service in services_data:
        # Formatage du titre avec l'acronyme
        markdown_content += f"## {service['nom']} - ({service['acronyme']})\n\n"
        
        # Ajout de l'acronyme comme champ séparé au-dessus de l'adresse
        acronym_label = 'Acronym' if is_english else 'Acronyme'
        markdown_content += f"**{acronym_label} :** {service['acronyme']}\n\n"
        
        address_label = 'Address' if is_english else 'Adresse'
        markdown_content += f"**{address_label} :**\n{service['adresse']}\n\n"
        
        hours_label = 'Opening hours' if is_english else "Horaires d'ouverture"
        markdown_content += f"**{hours_label} :**\n{service['horaires']}\n\n"
        
        phone_label = 'Phone' if is_english else 'Téléphone'
        markdown_content += f"**{phone_label} :** {service['telephone']}\n\n"
        
        contact_label = 'Contact us' if is_english else 'Nous écrire'
        markdown_content += f"**{contact_label} :** "
        if service['lien_nous_ecrire'] not in ["Information non disponible", "Information not available"]:
            markdown_content += f"[{contact_label}]({service['lien_nous_ecrire']})\n\n"
        else:
            markdown_content += f"{service['lien_nous_ecrire']}\n\n"
        
        org_page_label = 'View organization page' if is_english else "Voir la page de l'entité"
        markdown_content += f"**{org_page_label} :** "
        if service['lien_page_entite'] not in ["Information non disponible", "Information not available"]:
            link_text = 'Organization page' if is_english else "Page de l'entité"
            markdown_content += f"[{link_text}]({service['lien_page_entite']})\n\n"
        else:
            markdown_content += f"{service['lien_page_entite']}\n\n"
        markdown_content += "---\n\n"
    
    # Convertir le Markdown en HTML
    html_output = markdown_to_html(markdown_content, target_url)
    
    # Pour debug, enregistrer les fichiers intermédiaires
    lang_suffix = "_en" if is_english else ""
    with open(f"annuaire_services{lang_suffix}.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    with open(f"annuaire_services{lang_suffix}.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    
    print(f"[INFO] HTML généré avec {len(services_data)} services")
    return html_output

def scrape_annuaire(url):
    """Point d'entrée principal qui exécute la version asynchrone"""
    return asyncio.run(scrape_annuaire_async(url))

def clean_name(name):
    """Nettoie le nom du service pour le système de fichiers"""
    # Supprimer les caractères spéciaux et remplacer les espaces par des underscores
    clean = re.sub(r'[^\w\s-]', '', name).strip()
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean[:50]  # Limiter la longueur

async def scrape_french_services():
    """Scrape les services français et construit le cache des acronymes"""
    print("[INFO] Phase 1: Scraping des services français...")
    
    source_url = "https://monservicepublic.gouv.mc/annuaire-des-services-administratifs"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        
        # Obtenir la liste des services
        main_page = await context.new_page()
        await main_page.goto(source_url, timeout=60000)
        await main_page.wait_for_load_state('networkidle')
        
        # Sélecteur des services
        service_selector = "div.space-y-2 a"
        services = await main_page.query_selector_all(service_selector)
        
        service_ids = []
        for service in services:
            service_id = await service.get_attribute('id')
            if service_id:
                service_ids.append(service_id)
        
        print(f"[INFO] Nombre de services français trouvés : {len(service_ids)}")
        
        # Traiter les services français
        fr_services = {}
        cache_acronymes = {}
        failed_services = []
        concurrent_limit = 8
        
        for i in range(0, len(service_ids), concurrent_limit):
            batch = service_ids[i:i+concurrent_limit]
            
            # Créer des pages pour ce batch
            pages = []
            for _ in range(len(batch)):
                pages.append(await context.new_page())
            
            # Traiter le batch
            tasks = []
            for j, service_id in enumerate(batch):
                tasks.append(process_service(pages[j], service_id, source_url, False))
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Traiter les résultats
                for service_id, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        failed_services.append((service_id, str(result)))
                        print(f"[WARNING] Échec service FR {service_id}: {result}")
                    elif result:
                        fr_services[service_id] = result
                        cache_acronymes[service_id] = {
                            "nom_fr": result['nom'],
                            "acronyme": result['acronyme'],
                            "processed": True
                        }
                
            except Exception as e:
                print(f"[ERROR] Erreur lors du traitement du batch FR: {e}")
                for service_id in batch:
                    failed_services.append((service_id, str(e)))
            
            # Fermer les pages
            for page in pages:
                await page.close()
            
            print(f"[INFO] Services FR traités: {min(i+len(batch), len(service_ids))}/{len(service_ids)}")
        
        # Retry des services qui ont échoué (individuellement)
        if failed_services:
            print(f"[INFO] Retry individuel de {len(failed_services)} services FR échoués...")
            for service_id, error_msg in failed_services:
                try:
                    # Créer une nouvelle page pour le retry
                    retry_page = await context.new_page()
                    print(f"[RETRY] Tentative individuelle pour service FR {service_id}")
                    
                    # Retry avec timeout plus long
                    result = await process_service(retry_page, service_id, source_url, False, retry_timeout=120000)
                    if result and 'nom' in result:
                        fr_services[service_id] = result
                        cache_acronymes[service_id] = {
                            "nom_fr": result['nom'],
                            "acronyme": result['acronyme'],
                            "processed": True
                        }
                        print(f"[SUCCESS] Service FR {service_id} récupéré lors du retry")
                    else:
                        print(f"[FAILED] Service FR {service_id} toujours en échec après retry")
                    
                    await retry_page.close()
                    
                    # Pause entre les tentatives individuelles
                    await asyncio.sleep(2)
                    
                except Exception as retry_error:
                    print(f"[ERROR] Retry échoué pour service FR {service_id}: {retry_error}")
        
        await browser.close()
    
    print(f"[INFO] Phase 1 terminée: {len(fr_services)} services français scrapés")
    return fr_services, cache_acronymes

async def scrape_english_services_with_fr_cache(cache_acronymes):
    """Scrape les services anglais en utilisant le cache français"""
    print("[INFO] Phase 2: Scraping des services anglais...")
    
    source_url = "https://monservicepublic.gouv.mc/en/directory-of-government-services"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        
        en_services = {}
        failed_services = []
        service_ids = list(cache_acronymes.keys())
        
        concurrent_limit = 8
        
        for i in range(0, len(service_ids), concurrent_limit):
            batch = service_ids[i:i+concurrent_limit]
            
            # Créer des pages pour ce batch
            pages = []
            for _ in range(len(batch)):
                pages.append(await context.new_page())
            
            # Traiter le batch
            tasks = []
            for j, service_id in enumerate(batch):
                tasks.append(process_service(pages[j], service_id, source_url, True))
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Traiter les résultats
                for service_id, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        failed_services.append((service_id, str(result)))
                        print(f"[WARNING] Échec service EN {service_id}: {result}")
                    elif result:
                        en_services[service_id] = result
                
            except Exception as e:
                print(f"[ERROR] Erreur lors du traitement du batch: {e}")
                for service_id in batch:
                    failed_services.append((service_id, str(e)))
            
            # Fermer les pages
            for page in pages:
                await page.close()
            
            print(f"[INFO] Services EN traités: {min(i+len(batch), len(service_ids))}/{len(service_ids)}")
        
        # Retry des services qui ont échoué (individuellement)
        if failed_services:
            print(f"[INFO] Retry individuel de {len(failed_services)} services EN échoués...")
            for service_id, error_msg in failed_services:
                try:
                    # Créer une nouvelle page pour le retry
                    retry_page = await context.new_page()
                    print(f"[RETRY] Tentative individuelle pour service {service_id}")
                    
                    # Retry avec timeout plus long
                    result = await process_service(retry_page, service_id, source_url, True, retry_timeout=120000) # Increased timeout for retry
                    if result and 'nom' in result:
                        en_services[service_id] = result
                        print(f"[SUCCESS] Service {service_id} récupéré lors du retry")
                    else:
                        print(f"[FAILED] Service {service_id} toujours en échec après retry")
                    
                    await retry_page.close()
                    
                    # Pause entre les tentatives individuelles
                    await asyncio.sleep(2)
                    
                except Exception as retry_error:
                    print(f"[ERROR] Retry échoué pour {service_id}: {retry_error}")
        
        await browser.close()
    
    print(f"[INFO] Services EN traités: {len(en_services)}/{len(cache_acronymes)}")
    if failed_services:
        print(f"[INFO] Services EN échoués: {len(failed_services)}")
        for service_id, error in failed_services[:5]:  # Montrer seulement les 5 premiers
            fr_name = cache_acronymes[service_id]["nom_fr"]
            print(f"  - {service_id} ({fr_name}): {error}")
        if len(failed_services) > 5:
            print(f"  ... et {len(failed_services) - 5} autres")
    
    return en_services

def create_service_file(service_id, service_data, langue, base_url, acronyme_fr=None, output_dir="output/Annuaire"):
    """Crée un fichier individuel pour un service"""
    # Pour EN, utiliser l'acronyme FR du cache
    acronyme = acronyme_fr if langue == "EN" else service_data["acronyme"]
    
    # Générer le contenu HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <title>{base_url}?entity={service_id}</title>
</head>
<body>
  <h1>{base_url}?entity={service_id}</h1>
  <h2>{service_data['nom']} - ({acronyme})</h2>
  
  <div class="service">
    <p><strong>{'Acronym' if langue == 'EN' else 'Acronyme'} :</strong> {acronyme}</p>
    
    <p><strong>{'Address' if langue == 'EN' else 'Adresse'} :</strong><br>{service_data['adresse']}</p>
    
    <p><strong>{'Opening hours' if langue == 'EN' else "Horaires d'ouverture"} :</strong><br>{service_data['horaires']}</p>
    
    <p><strong>{'Phone' if langue == 'EN' else 'Téléphone'} :</strong> {service_data['telephone']}</p>
    
    <p><strong>{'Contact us' if langue == 'EN' else 'Nous écrire'} :</strong> """
    
    # Ajouter le lien nous écrire
    if service_data['lien_nous_ecrire'] not in ["Information non disponible", "Information not available"]:
        contact_label = 'Contact us' if langue == 'EN' else 'Nous écrire'
        html_content += f'<a href="{service_data["lien_nous_ecrire"]}">{contact_label}</a></p>\n'
    else:
        html_content += f'{service_data["lien_nous_ecrire"]}</p>\n'
    
    # Ajouter le lien page entité
    org_page_label = 'View organization page' if langue == 'EN' else "Voir la page de l'entité"
    html_content += f'    <p><strong>{org_page_label} :</strong> '
    if service_data['lien_page_entite'] not in ["Information non disponible", "Information not available"]:
        link_text = 'Organization page' if langue == 'EN' else "Page de l'entité"
        html_content += f'<a href="{service_data["lien_page_entite"]}">{link_text}</a></p>\n'
    else:
        html_content += f'{service_data["lien_page_entite"]}</p>\n'
    
    html_content += """  </div>
</body>
</html>"""
    
    # Créer le nom de fichier : ACRONYME_NOM_LANGUE_annuaire-services.txt
    clean_nom = clean_name(service_data['nom'])
    filename = f"{acronyme}_{clean_nom}_{langue}_annuaire-services.txt"
    
    # S'assurer que le dossier existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Écrire le fichier
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[OK] Fichier créé: {filename}")
    return filepath

def generate_individual_files(fr_services, en_services, cache_acronymes, output_dir="output/Annuaire"):
    """Génère les fichiers individuels pour tous les services"""
    print("[INFO] Phase 3: Génération des fichiers individuels...")
    
    total_files = 0
    
    for service_id, fr_data in fr_services.items():
        # Fichier FR
        create_service_file(
            service_id, fr_data, "FR", 
            base_url="https://monservicepublic.gouv.mc/annuaire-des-services-administratifs",
            output_dir=output_dir
        )
        total_files += 1
        
        # Fichier EN (si disponible)
        if service_id in en_services:
            create_service_file(
                service_id, en_services[service_id], "EN",
                base_url="https://monservicepublic.gouv.mc/en/directory-of-government-services",
                acronyme_fr=cache_acronymes[service_id]["acronyme"],
                output_dir=output_dir
            )
            total_files += 1
        else:
            print(f"[WARNING] Service {service_id} ({fr_data['nom']}) - Version EN non disponible, fichier EN ignoré")
    
    print(f"[INFO] Phase 3 terminée: {total_files} fichiers générés")

async def scrape_annuaire_individualized(output_dir="output/Annuaire"):
    """Fonction principale pour scraper et générer les fichiers individuels"""
    start_time = time.time()
    
    try:
        # Phase 1: Scraper FR et construire le cache
        fr_services, cache_acronymes = await scrape_french_services()
        
        # Phase 2: Scraper EN avec cache FR
        en_services = await scrape_english_services_with_fr_cache(cache_acronymes)
        
        # Phase 3: Générer fichiers individuels
        generate_individual_files(fr_services, en_services, cache_acronymes, output_dir)
        
        # Phase 4: Nettoyage
        cleanup_cache_and_temp_files()
        
        # Statistiques finales
        elapsed_time = time.time() - start_time
        print(f"\n[SUCCESS] Scraping individualisé terminé en {elapsed_time:.2f} secondes")
        print(f"[INFO] Services FR: {len(fr_services)}")
        print(f"[INFO] Services EN: {len(en_services)}")
        print(f"[INFO] Fichiers dans: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Erreur lors du scraping individualisé: {e}")
        return False

# Fonction de test
def test_annuaire_individualized():
    """Fonction de test pour le scraping individualisé"""
    print("=== TEST SCRAPING ANNUAIRE INDIVIDUALISÉ ===")
    return asyncio.run(scrape_annuaire_individualized())

def cleanup_cache_and_temp_files():
    """Supprime cache et fichiers temporaires après traitement"""
    files_to_remove = [
        "cache_acronymes.json",
        "annuaire_services.md",
        "annuaire_services_en.md", 
        "annuaire_services.html",
        "annuaire_services_en.html"
    ]
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"[CLEANUP] Supprimé: {file}")

def validate_service_data(service_data, service_id, langue):
    """Valide les données extraites avant génération fichier"""
    required_fields = ['nom', 'acronyme', 'adresse', 'telephone']
    
    for field in required_fields:
        if not service_data.get(field):
            print(f"[WARNING] Service {service_id} ({langue}): champ '{field}' manquant")
    
    return True  # Continue même avec des champs manquants

# Pour les tests indépendants
if __name__ == "__main__":
    import sys
    
    # Vérifier si un argument est passé
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        html_output = scrape_annuaire(test_url)
        print(f"Scraping terminé pour {test_url}")
    else:
        # Test FR
        test_url_fr = "https://monservicepublic.gouv.mc/annuaire-des-services-administratifs"
        print(f"Test FR: {test_url_fr}")
        html_output_fr = scrape_annuaire(test_url_fr)
        
        # Test EN
        test_url_en = "https://monservicepublic.gouv.mc/en/directory-of-government-services"
        print(f"Test EN: {test_url_en}")
        html_output_en = scrape_annuaire(test_url_en)
        
        print("Tests de scraping terminés, fichiers générés.")

cache_acronymes = {
    "service_id_123": {
        "nom_fr": "Direction des Services Informatiques",
        "acronyme": "DSI",
        "processed": True
    }
}