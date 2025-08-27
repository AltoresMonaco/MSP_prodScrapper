#embedding_pipeline.py
import os
import glob
import re
import logging
import sys
import uuid
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from tqdm import tqdm

# Import for OpenAI embeddings
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Importation du package officiel pinecone V2
from pinecone import Pinecone, ServerlessSpec

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement depuis .env
load_dotenv()

# API keys et configurations
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENV = os.getenv('PINECONE_ENV')  # Exemple : "us-east1-gcp"
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')

if not all([OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENV, PINECONE_INDEX_NAME]):
    logger.error("Une ou plusieurs variables d'environnement sont manquantes. Vérifiez votre fichier .env.")
    sys.exit(1)

# Initialisation de Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Vérifier si l'index existe, sinon le créer
try:
    indexes = pc.list_indexes().names()
    if PINECONE_INDEX_NAME not in indexes:
        logger.info(f"L'index '{PINECONE_INDEX_NAME}' n'existe pas. Création en cours...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,  # Dimension pour text-embedding-ada-002
            metric='cosine',
            spec=ServerlessSpec(cloud="gcp", region=PINECONE_ENV)
        )
        logger.info(f"L'index '{PINECONE_INDEX_NAME}' a été créé.")
    else:
        logger.info(f"L'index '{PINECONE_INDEX_NAME}' existe déjà.")

    index = pc.Index(PINECONE_INDEX_NAME)
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de Pinecone: {e}")
    sys.exit(1)

def enhanced_html_to_text(html_content, base_url="https://monservicepublic.gouv.mc"):
    """
    Convertit HTML en texte enrichi en préservant les liens et la structure.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Supprimer les scripts, styles, et autres éléments non pertinents
    for tag in soup.find_all(['script', 'style', 'meta', 'noscript']):
        tag.decompose()
    
    # Traitement des liens (a href)
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href', '')
        
        # Convertir les URLs relatives en URLs absolues
        if href and not href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            if href.startswith('/'):
                href = base_url + href
            else:
                href = f"{base_url}/{href}"
        
        # Format du texte: Texte du lien [URL]
        link_text = a_tag.get_text(strip=True)
        if link_text and href:
            # Remplacer le contenu du lien par texte + URL entre crochets
            new_text = f"{link_text} [{href}]"
            a_tag.string = new_text
    
    # Traitement des en-têtes (h1, h2, h3...)
    for i in range(1, 7):
        for header in soup.find_all(f'h{i}'):
            header_text = header.get_text(strip=True)
            # Ajouter des # pour les en-têtes
            prefix = '#' * i
            header.string = f"\n\n{prefix} {header_text}\n\n"
    
    # Traitement des paragraphes
    for p in soup.find_all('p'):
        p_text = p.get_text(strip=True)
        if p_text:
            # Ajouter des sauts de ligne autour des paragraphes
            p.string = f"\n{p_text}\n"
    
    # Traitement des listes
    for ul in soup.find_all('ul'):
        for i, li in enumerate(ul.find_all('li', recursive=False)):
            li_text = li.get_text(strip=True)
            if li_text:
                li.string = f"\n- {li_text}"
    
    for ol in soup.find_all('ol'):
        for i, li in enumerate(ol.find_all('li', recursive=False)):
            li_text = li.get_text(strip=True)
            if li_text:
                li.string = f"\n{i+1}. {li_text}"
    
    # Obtenir le texte complet avec les espaces préservés
    text = soup.get_text(separator="\n")
    
    # Nettoyer les espaces multiples et les sauts de ligne excessifs
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()

def load_and_split_documents(base_folder, fixed_thematique):
    """
    Parcourt le dossier base_folder pour charger les fichiers scrappés (.txt),
    convertit le HTML en texte enrichi pour préserver les liens et la structure,
    déduit le namespace et applique le text splitting.
    """
    import config  # pour accéder à config.FIXED_URLS et ANNUAIRE_URL_PATTERNS
    document_paths = glob.glob(os.path.join(base_folder, '**', '*.txt'), recursive=True)
    documents = []
    
    # Debug: Afficher le nombre total de fichiers trouvés
    logger.info(f"Nombre total de fichiers trouvés: {len(document_paths)}")
    
    for file_path in document_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extraire l'URL via BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        url_extracted = soup.title.string.strip() if soup.title and soup.title.string else "unknown"
        
        # Utiliser la fonction améliorée pour préserver les liens
        enriched_text = enhanced_html_to_text(html_content, base_url=url_extracted)
        
        # Déduire le namespace à partir du chemin relatif
        rel_path = os.path.relpath(file_path, base_folder)
        parts = rel_path.split(os.sep)
        
        # Logique améliorée pour le namespace
        if len(parts) > 1:
            folder_name = parts[0]
            # Si c'est dans le dossier "Annuaire", forcer le namespace "child"
            if folder_name == "Annuaire":
                namespace = "child"
            elif folder_name == "general":
                namespace = "general"
            else:
                # Tous les autres dossiers (catégories) vont dans "child"
                namespace = "child"
        else:
            namespace = "general"
        
        # Extraire le nom de fichier sans chemin complet
        filename = os.path.basename(file_path)
        
        metadata = {
            "filename": filename,  # Nom du fichier au lieu du chemin complet
            "url": url_extracted,
            "namespace": namespace,
            "format": "enriched_text"  # Indique que le contenu est du texte enrichi
        }
        
        # Déterminer la thématique
        # Si c'est l'annuaire, définir une thématique spécifique
        is_annuaire = any(pattern in url_extracted for pattern in config.ANNUAIRE_URL_PATTERNS)
        if is_annuaire:
            metadata["thematique"] = "Annuaire administratif"
        else:
            # Vérifier si l'URL extraite figure dans FIXED_URLS pour ajouter la thématique associée
            fixed_them = None
            for fixed in config.FIXED_URLS:
                if url_extracted == fixed["url"]:
                    fixed_them = fixed["thematique"]
                    break
            metadata["thematique"] = fixed_them if fixed_them is not None else fixed_thematique
        
        # Debug: Afficher un échantillon du texte enrichi pour le premier document
        if len(documents) == 0:
            sample = enriched_text[:500] + "..."
            logger.info(f"Échantillon du texte enrichi: {sample}")
        
        # Découpage du texte en chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=20000,
            chunk_overlap=5000,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_text(enriched_text)
        
        # Créer des documents pour chaque chunk
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk"] = i  # Ajouter un numéro de chunk
            chunk_doc = Document(page_content=chunk, metadata=chunk_metadata)
            documents.append(chunk_doc)
    
    logger.info(f"{len(documents)} chunks générés après splitting.")
    return documents

def namespace_exists(index, namespace):
    """Vérifie si un namespace existe et contient des données."""
    try:
        # Tente de faire une requête minimale pour voir si le namespace existe
        result = index.query(
            namespace=namespace,
            vector=[0] * 1536,  # Vecteur factice pour la requête
            top_k=1,
            include_values=False,
            include_metadata=False
        )
        # Si on obtient une réponse sans erreur, le namespace existe
        return True
    except Exception as e:
        if "namespace does not exist" in str(e).lower():
            return False
        # Si l'erreur est différente, on considère que le namespace peut exister
        # mais continuer quand même
        logger.warning(f"Erreur lors de la vérification du namespace '{namespace}': {e}")
        return False

def delete_namespace_vectors_with_rate_limit(index, namespace, batch_size=100, delay=1):
    """
    Supprime les vecteurs d'un namespace en gérant le rate limiting.
    
    Args:
        index: L'index Pinecone
        namespace: Le namespace à vider
        batch_size: Nombre de vecteurs à supprimer par lot
        delay: Délai en secondes entre chaque lot
    """
    try:
        stats = index.describe_index_stats()
        if 'namespaces' not in stats or namespace not in stats['namespaces']:
            logger.info(f"Le namespace '{namespace}' n'existe pas ou est vide.")
            return
        
        vector_count = stats['namespaces'][namespace]['vector_count']
        if vector_count == 0:
            logger.info(f"Le namespace '{namespace}' est déjà vide.")
            return
        
        logger.info(f"Suppression de {vector_count} vecteurs du namespace '{namespace}' par lots de {batch_size}...")
        
        deleted_count = 0
        while deleted_count < vector_count:
            try:
                # Requête pour obtenir un lot d'IDs
                query_result = index.query(
                    namespace=namespace,
                    vector=[0] * 1536,
                    top_k=min(batch_size, vector_count - deleted_count),
                    include_values=False,
                    include_metadata=False
                )
                
                if not query_result.matches:
                    logger.info("Plus de vecteurs à supprimer.")
                    break
                
                # Extraire les IDs
                ids_to_delete = [match.id for match in query_result.matches]
                
                if ids_to_delete:
                    # Supprimer le lot
                    index.delete(ids=ids_to_delete, namespace=namespace)
                    deleted_count += len(ids_to_delete)
                    logger.info(f"Progression: {deleted_count}/{vector_count} vecteurs supprimés")
                    
                    # Pause pour éviter le rate limiting
                    time.sleep(delay)
                else:
                    break
                    
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    logger.warning(f"Rate limit atteint. Pause de {delay * 2} secondes...")
                    time.sleep(delay * 2)
                else:
                    logger.error(f"Erreur lors de la suppression: {e}")
                    break
        
        logger.info(f"Suppression terminée. {deleted_count} vecteurs supprimés du namespace '{namespace}'.")
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du namespace '{namespace}': {e}")

def batch_documents(documents, batch_size=100):
    """Divise une liste de documents en lots de taille batch_size."""
    for i in range(0, len(documents), batch_size):
        yield documents[i:i + batch_size]

def create_pinecone_vectors(docs, embeddings_model):
    """
    Crée des vecteurs Pinecone à partir de documents et d'un modèle d'embeddings.
    Retourne une liste de tuples (id, vecteur, métadonnées).
    """
    # Extraire le texte et les métadonnées
    texts = [doc.page_content for doc in docs]
    metadatas = [doc.metadata for doc in docs]
    
    # Générer les embeddings
    embeddings = embeddings_model.embed_documents(texts)
    
    # Créer les vecteurs Pinecone
    vectors = []
    for i, (embedding, metadata) in enumerate(zip(embeddings, metadatas)):
        # Générer un ID unique
        vec_id = str(uuid.uuid4())
        
        # Ajouter le contenu du texte aux métadonnées (pour la recherche)
        metadata_copy = metadata.copy()
        metadata_copy["text"] = texts[i]
        
        # Ajouter le vecteur à la liste
        vectors.append((vec_id, embedding, metadata_copy))
    
    return vectors

def upsert_to_pinecone(index, vectors, namespace):
    """
    Insère des vecteurs dans Pinecone en utilisant l'API V2.
    """
    # Convertir au format attendu par Pinecone V2
    pinecone_vectors = []
    for vec_id, embedding, metadata in vectors:
        pinecone_vectors.append({
            "id": vec_id,
            "values": embedding,
            "metadata": metadata
        })
    
    # Upsert par lots pour éviter de dépasser les limites
    batch_size = 200
    for i in range(0, len(pinecone_vectors), batch_size):
        batch = pinecone_vectors[i:i + min(batch_size, len(pinecone_vectors) - i)]
        try:
            index.upsert(vectors=batch, namespace=namespace)
            logger.info(f"Lot de {len(batch)} vecteurs inséré dans le namespace '{namespace}'")
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion d'un lot dans Pinecone: {e}")
            # Attendre et réessayer en cas d'erreur de rate limiting
            if "rate" in str(e).lower():
                logger.info("Rate limit atteint, pause de 10 secondes...")
                time.sleep(10)
                # Réessayer
                try:
                    index.upsert(vectors=batch, namespace=namespace)
                    logger.info(f"Lot de {len(batch)} vecteurs inséré après pause")
                except Exception as retry_e:
                    logger.error(f"Échec de l'insertion après pause: {retry_e}")

def run_embedding(base_folder, fixed_thematique, skip_cleanup=False):
    base_folder = os.path.abspath(base_folder)
    if not os.path.exists(base_folder):
        logger.error(f"Le dossier '{base_folder}' n'existe pas.")
        return
    
    logger.info("Chargement et découpage des documents avec conversion HTML->texte enrichi...")
    documents = load_and_split_documents(base_folder, fixed_thematique)
    
    # Initialiser le modèle d'embeddings
    embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    # Regrouper les documents par namespace
    namespaces = set(doc.metadata["namespace"] for doc in documents)
    for ns in namespaces:
        docs_in_ns = [doc for doc in documents if doc.metadata["namespace"] == ns]
        if not docs_in_ns:
            continue
        
        logger.info(f"Traitement du namespace '{ns}' avec {len(docs_in_ns)} documents.")
        
        # Vérifier et nettoyer le namespace si nécessaire
        if not skip_cleanup and namespace_exists(index, ns):
            logger.info(f"Nettoyage du namespace '{ns}' existant...")
            delete_namespace_vectors_with_rate_limit(
                index, 
                ns, 
                batch_size=1000,  # Réduire la taille des lots pour éviter le rate limiting
                delay=1.5  # Augmenter le délai entre les lots
            )
        
        # Traiter les documents par lots
        logger.info(f"Génération des embeddings et insertion des documents dans le namespace '{ns}'...")
        batch_size = 20  # Revenu à 20 voir si 50 ? pour respecter la limite OpenAI de 300k tokens
        total_processed = 0
        
        # Traiter par lots pour éviter les limites d'API
        for batch in batch_documents(docs_in_ns, batch_size):
            # Créer les vecteurs pour ce lot
            vectors = create_pinecone_vectors(batch, embeddings_model)
            
            # Insérer dans Pinecone
            upsert_to_pinecone(index, vectors, ns)
            
            total_processed += len(batch)
            logger.info(f"Progression: {total_processed}/{len(docs_in_ns)} documents traités")
            
            # Petite pause pour éviter rate limiting
            time.sleep(0.5)
        
        logger.info(f"Total de {total_processed} documents insérés dans le namespace '{ns}'.")
    
    logger.info("Traitement des embeddings terminé.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        base_folder = sys.argv[1]
        fixed_thematique = sys.argv[2]
    else:
        base_folder = input("Indique le dossier de base contenant les fichiers scrappés: ")
        fixed_thematique = input("Indique le nom de la thématique pour les URL fixes: ")
    
    # Option pour ignorer le nettoyage (utile pour les tests)
    skip_cleanup = "--skip-cleanup" in sys.argv
    
    run_embedding(base_folder, fixed_thematique, skip_cleanup)