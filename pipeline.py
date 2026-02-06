import json
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import uuid
import re
from tqdm import tqdm
import tiktoken
from sentence_transformers import CrossEncoder

# --- CONFIGURATION ---
LM_STUDIO_URL = "http://192.168.1.170:1734/v1"
API_KEY = "lm-studio"
MODEL_NAME = "qwen2.5-14b-instruct"
BATCH_SIZE = 5

DEBUG = False

PATH_CONTEXT="./mnt/s-data/merged_output_05.txt"
PATH_TEMPLATE="./mnt/ask/04_01_v01.json"
PATH_OUTPUT="./out/02.01_v01.json"


# --- CONFIGURATION CONTEXTE ---
MAX_CONTEXT_WINDOW = 8192  # Réduit pour éviter la saturation VRAM
SAFETY_MARGIN = 1500  # Espace gardé pour la réponse
MAX_INPUT_TOKENS = MAX_CONTEXT_WINDOW - SAFETY_MARGIN


# --- 1. FONCTIONS UTILITAIRES ---
def get_embedding(text, client):
    """Récupère l'embedding via LM Studio"""
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-nomic-embed-text-v1.5").data[0].embedding


def count_tokens(text):
    """Compte les tokens (estimation rapide)"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def process_raw_data(raw_data_list):
    """Découpe avec overlap"""
    full_text = "\n".join(raw_data_list)
    CHUNK_SIZE = 2000
    CHUNK_OVERLAP = 300
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)

    chunks = []
    start = 0
    text_len = len(full_text)

    while start < text_len:
        end = start + CHUNK_SIZE
        if end < text_len:
            search_zone = full_text[end - 100: end]
            match = list(re.finditer(r'\n\n', search_zone))
            if match:
                end = (end - 100) + match[-1].end()
            else:
                match = list(re.finditer(r'(?<=[.?!])\s', search_zone))
                if match:
                    end = (end - 100) + match[-1].end()

        chunk = full_text[start:end].strip()
        if chunk: chunks.append(chunk)
        start = end - CHUNK_OVERLAP
        if start >= end: start = end

    print(f"✂️  Découpage terminé : {len(chunks)} segments générés.")
    return chunks


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        # turns a function into a function generator
        yield lst[i:i + n]


def create_vector_db(documents_list, openai_client):
    print("⏳ Indexation des documents en cours...")
    chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
    collection = chroma_client.create_collection(name="medical_reports_" + str(uuid.uuid4())[:8])
    ids = [str(uuid.uuid4()) for _ in range(len(documents_list))]
    embeddings = [get_embedding(doc, openai_client) for doc in documents_list]
    collection.add(documents=documents_list, embeddings=embeddings, ids=ids)
    print(f"✅ {len(documents_list)} segments indexés.")
    return collection


# --- 2. EXÉCUTION ---
def main():
    client = OpenAI(base_url=LM_STUDIO_URL, api_key=API_KEY)

    print("⚖️  Chargement du modèle de Reranking...")
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    print("📂 Chargement des données...")
    try:
        with open(PATH_CONTEXT, 'r', encoding='utf-8') as file:
            RAW_CONTEXT_DATA = [file.read()]
        with open(PATH_TEMPLATE, 'r', encoding='utf-8') as file:
            SCHEMA_JSON = json.load(file)
    except Exception as e:
        print(f"❌ Erreur lecture fichiers : {e}")
        return

    full_text_chunks = process_raw_data(RAW_CONTEXT_DATA)
    if not full_text_chunks: return
    vector_db = create_vector_db(full_text_chunks, client)

    # --- TEST DE DIAGNOSTIC ---
    if DEBUG:
        print("\n🕵️‍♂️ --- DÉBUT DIAGNOSTIC METFORMINE ---")

        # 1. Vérifier si le mot est dans les chunks bruts
        found_in_chunks = False
        for i, chunk in enumerate(full_text_chunks):
            if "Metformine" in chunk:
                print(f"✅ TROUVÉ dans le chunk #{i} (taille: {len(chunk)} chars)")
                print(f"contenu partiel : {chunk[:100]}...")
                found_in_chunks = True
                break

        if not found_in_chunks:
            print("❌ CRITIQUE : Le mot 'Metformine' n'est nulle part dans les chunks générés !")
            print("Vérifie ton fichier source ou ta fonction process_raw_data.")
        else:
            # 2. Vérifier si ChromaDB le remonte avec une requête directe
            print("🔍 Test de récupération ChromaDB pour 'médication metformine'...")
            test_query = "Quelle est la médication actuelle Metformine ?"
            results = vector_db.query(
                query_embeddings=[get_embedding(test_query, client)],
                n_results=5
            )

            found_in_db = False
            for doc in results['documents'][0]:
                if "Metformine" in doc:
                    found_in_db = True
                    print("✅ ChromaDB remonte bien le document quand on pose la question précise.")
                    break

            if not found_in_db:
                print("⚠️ ChromaDB a le document mais NE LE REMONTE PAS (problème d'embedding ou de score).")
                print("Documents remontés à la place :")
                for j, doc in enumerate(results['documents'][0]):
                    print(f"   Doc #{j}: {doc[:50]}...")

        print("🕵️‍♂️ --- FIN DIAGNOSTIC ---\n")
    # --------------------------

    # --- PRÉPARATION ---
    raw_fields = SCHEMA_JSON.get('fields', [])
    valid_fields = []
    for f in raw_fields:
        # Je vérifie juste qu'on a un ID et une question (le name n'est plus la pk ici).
        if 'id' in f and 'question' in f:
            if str(f.get('skip')).lower() != "true":
                valid_fields.append(f)

    # liste qui stocke tous les résultats
    accumulated_fields = []

    print(f"\n🚀 Démarrage Extraction ({len(valid_fields)} champs)...\n")
    batches = list(chunk_list(valid_fields, BATCH_SIZE))

    for batch in tqdm(batches, unit="batch"):

        # --- 1. RETRIEVAL OPTIMISÉ (MULTI-QUERY) ---
        # On crée un set pour stocker les documents uniques trouvés pour chaque question
        candidate_docs_set = set()

        # On itère sur chaque question du batch individuellement
        for f in batch:
            try:
                # Recherche spécifique pour cette question
                q_embedding = get_embedding(f['question'], client)
                results = vector_db.query(
                    query_embeddings=[q_embedding],
                    n_results=4  # Top 4 par question pour capturer les infos noyées
                )
                # Ajout des résultats au set (gère automatiquement les doublons)
                for doc in results['documents'][0]:
                    candidate_docs_set.add(doc)
            except Exception as e:
                print(f"⚠️ Erreur retrieval sur '{f['id']}': {e}")

        unique_candidate_docs = list(candidate_docs_set)

        # Sécurité : Si aucun document trouvé
        if not unique_candidate_docs:
            context_str = ""
        else:
            # --- 2. RERANKING ---
            # On rerank l'ensemble des documents uniques par rapport au contexte global du batch
            combined_questions = " ".join([f['question'] for f in batch])

            pairs = [[combined_questions, doc] for doc in unique_candidate_docs]
            scores = reranker.predict(pairs)

            # Tri des documents par pertinence décroissante
            scored_docs = sorted(zip(unique_candidate_docs, scores), key=lambda x: x[1], reverse=True)

            # --- 3. CONSTRUCTION DU CONTEXTE (token guard)
            final_context = []
            current_tokens = 0
            limit = MAX_INPUT_TOKENS  # Doit être ~6500-7000 (8192 - marge)

            for doc, score in scored_docs:
                doc_tokens = count_tokens(doc)
                if current_tokens + doc_tokens < limit:
                    final_context.append(doc)
                    current_tokens += doc_tokens
                else:
                    break  # arrêt si la fenêtre est dépassée

            context_str = "\n---\n".join(final_context)

            # --- DEBUG SPÉCIFIQUE (Pour vérifier ton problème) ---
            # Affiche si Metformine est présent quand on traite la question des médicaments
            if any(q['id'] == '4.5' for q in batch):
                is_present = 'Metformine' in context_str
                print(
                    f"\n👀 CHECKPOINT Q4.5: 'Metformine' présent dans le contexte final ? {'✅ OUI' if is_present else '❌ NON'}")

        # --- 4. PRÉPARATION DU PROMPT LLM ---
        fields_prompt_list = [{"id": f['id'], "question": f['question']} for f in batch]

        system_prompt = """Tu es un assistant expert en extraction de données médicales.

            INSTRUCTIONS :
            1. Analyse le contexte fourni ci-dessous.
            2. Renvoie un JSON contenant une liste sous la clé "fields".
            3. Pour chaque question reçue, crée un objet avec :
               - "id": L'identifiant fourni dans la question.
               - "value": La réponse extraite précise (null si introuvable).
               - "type_guided": le type de retour attendu.
               - "source_quote": La phrase exacte du texte qui justifie la réponse (null si introuvable).
            4. Si une liste est demandée (ex: médicaments), inclus tous les éléments.

            FORMAT DE RÉPONSE ATTENDU (JSON uniquement) :
            {
              "fields": [
                { "id": "X.Y", "value": "Réponse...", "source_quote": "Citation..." }
              ]
            }
            """

        user_prompt = f"""
            CONTEXTE DOCUMENTAIRE :
            \"\"\"
            {context_str}
            \"\"\"

            QUESTIONS À TRAITER :
            {json.dumps(fields_prompt_list, indent=2, ensure_ascii=False)}

            Renvoie uniquement le JSON valide.
            """

        try:
            # --- 5. APPEL LLM ---
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Température basse pour la rigueur
                max_tokens=2000
            )

            content = response.choices[0].message.content

            # si le LLM ajoute du MD -> nettoyage
            content = content.replace("```json", "").replace("```", "").strip()
            content = re.sub(r'(?<!\\)\n', ' ', content)

            # --- 6. PARSING & ACCUMULATION ---
            import json_repair
            batch_data = json_repair.loads(content)

            if "fields" in batch_data and isinstance(batch_data["fields"], list):
                accumulated_fields.extend(batch_data["fields"])
            else:
                print(f"⚠️ Structure inattendue sur ce batch : {batch_data.keys()}")
                # Fallback pour ne pas casser la liste finale
                for f in batch:
                    accumulated_fields.append({"id": f['id'], "value": None, "error": "Structure invalide"})

        except Exception as e:
            print(f"❌ Erreur critique sur le batch : {e}")
            for f in batch:
                accumulated_fields.append({
                    "id": f['id'],
                    "value": None,
                    "source_quote": None,
                    "error": str(e)
                })

    # 5. SAUVEGARDE FINALE
    final_output = {"fields": accumulated_fields}

    with open(PATH_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Extraction terminée. {len(accumulated_fields)} champs sauvegardés.")


if __name__ == "__main__":
    main()