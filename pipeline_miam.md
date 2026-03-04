# PoC - Ingestion et traitement des données

Le but de ce pipeline est d'ingérer et traiter des données issues de documents PDF.

## Workflow initial
1. Répartition + ingestion
2. Extraction des métadonnées sur le CPU
3. Parsing visuel + conversion du PDF en .md
4. Nettoyage des mots manquants avec un modèle
5. Semantic chunking (cf. LangChain / LlamaIndex)
6. Embedding
7. Stockage vector DB

# 1. Répartition et ingestion

But : Spark lit le folder contenant les PDF, puis chaque worker Spark prend un lot de PDF.

Mesurable : à définir

### 2. Extraction des formulaires & métadonnées (CPU)

But : avant de faire de la vision lourde, un script Python extrait les métadonnées du document.

Mesurable : un dictionnaire JSON contenant :
```json
{
  "file_name": "",
  "author": "",
  "date_last_update":"",
  "number_of_pages":""
}
```

### 3. Parsing visuel et conversion en markdown (GPU)

But : utilisation d'un outil comme Marker ou un VLM pour convertir le PDF en markdown.

Mesurable : un texte formaté en markdown, où les tablaux sont de vrais tableaux markdown, et les titres sont labellisés (si applicable).

### 4. Nettoyage des données

But : compléter les éventuels mots manquants avec des modèles comme [ClinicalBERT](https://huggingface.co/medicalai/ClinicalBERT)

Mesurable : à définir

### 5. Semantic chunking

But A) : au lieu de couper le texte tous les 500 mots, utilisation d'un algorithme (eg LangChain ou LlamaIndex) qui découpe le texte en se basant sur les balises markdown.

But B) : à chaque chunk, les métadonnées JSON de l'étape 2 sont injectées.

Mesurable : à définir

### 6. Embedding

But : passer tous les chunks à un modèle d'embedding pour transformer le texte en vecteurs.

Mesurable : à définir

### 7. Stockage

But : persister les vecteurs dans une base de données vectorielles.

Mesurable : à définir