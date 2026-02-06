# DF-PoC-01
Prototype local de RAG pour extraire des champs structurés depuis un contexte médical volumineux, avec traçabilité (citations) et sortie JSON prête à être utilisée pour remplir un formulaire PDF.

## Objectif et périmètre
- Valider la faisabilité d'une extraction fiable et rapide sur des contextes très longs (jusqu'à ~100k tokens en entrée).
- Tout exécuter localement avec un modèle open-source et un serveur LM Studio.
- PoC technique, pas un produit.

## Ce que fait le pipeline
- Ingestion d'un fichier texte unique (contexte documentaire).
- Découpage en segments avec overlap.
- Embeddings et indexation dans ChromaDB.
- Retrieval multi-requête puis reranking.
- Appel LLM pour répondre aux questions du template.
- Export JSON avec `value` et `source_quote`.

## Ce que le projet ne fait pas (encore)
- Remplissage automatique d'un PDF.
- UI, API ou orchestration.
- Évaluation et tests automatisés.

## Stack utilisée
- Python 3.13.5 (testé)
- LM Studio 0.3.36 (API OpenAI-compatible)
- LLM `qwen2.5-14b-instruct`
- Embeddings `text-embedding-nomic-embed-text-v1.5`
- Reranking `cross-encoder/ms-marco-MiniLM-L-6-v2`
- ChromaDB, Sentence-Transformers, Tiktoken

## Prérequis matériel (testé)
- GPU RTX 4080 SUPER 16 Go
- CPU i9-14900k
- RAM 64 Go

## Installation
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Configuration
Éditer `pipeline.py` selon votre environnement. Les chemins par défaut pointent vers des fichiers locaux non versionnés, adaptez-les.
- `LM_STUDIO_URL` (host:port + `/v1`)
- `MODEL_NAME`
- `PATH_CONTEXT` (fichier texte source)
- `PATH_TEMPLATE` (JSON des questions)
- `PATH_OUTPUT` (JSON de sortie)
- `MAX_CONTEXT_WINDOW`, `SAFETY_MARGIN`, `BATCH_SIZE`, `DEBUG`

Assurez-vous que le dossier de sortie de `PATH_OUTPUT` existe.

Paramètres LM Studio (testés) :
- Contexte max à 8192
- Le reste par défaut

## Formats d'entrée
Contexte documentaire :
- Un fichier `.txt` UTF-8 contenant l'ensemble des documents à analyser.
- Si vous avez plusieurs documents, concaténez-les en un seul fichier.

Template de questions :
- Un fichier JSON avec la clé `fields` qui contient une liste d'objets.
- Chaque objet doit contenir `id` et `question`.
- Le champ optionnel `skip: "true"` permet d'ignorer une question.

Exemple minimal :
```json
{
  "fields": [
    { "id": "2.1", "question": "Quel est le prénom du patient ?" }
  ]
}
```

## Exécution
```bash
python pipeline.py
```

Sortie attendue :
- Fichier JSON à l'emplacement `PATH_OUTPUT`.
- Chaque entrée contient `id`, `value` et `source_quote` (ou `null` si introuvable).

## Réglages qualité/performance
- `MAX_CONTEXT_WINDOW` et `SAFETY_MARGIN` contrôlent la taille du contexte transmis au LLM.
- `BATCH_SIZE` influe sur la latence et la cohérence inter-questions.
- `CHUNK_SIZE` et `CHUNK_OVERLAP` sont définis dans `process_raw_data`.

## Dépannage
- Erreur de connexion : vérifier que le serveur LM Studio est démarré et que `LM_STUDIO_URL` est correct.
- OOM/VRAM : réduire `MAX_CONTEXT_WINDOW` ou `BATCH_SIZE`.
- `ModuleNotFoundError: json_repair` : installer la dépendance manquante avec `pip install json-repair`.

## Structure du repo
- `pipeline.py` : pipeline principal d'extraction et d'indexation.
- `requirements.txt` : dépendances Python.
- `lesson-learned.md` : notes internes.

## Contribution
Les PRs sont bienvenues si vous respectez la confidentialité des données médicales.
Avant toute contribution, proposez une issue décrivant le changement.

## Licence
MIT