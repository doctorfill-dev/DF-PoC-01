# DF-POC-01
Ce PoC a pour but de tester la possibilité de traiter une grande quantité d'informations avec une configuration locale raisonnable.

Le but global du projet est de construire une application locale qui remplit automatiquement un formulaire PDF à partir d’un contexte documentaire (principalement des rapports médicaux). Le contexte peut être volumineux (~80’000 tokens). L’application doit proposer une extraction fiable, traçable (sources/citations) et produire une sortie exploitable pour remplir le PDF.

Par grande quantité d'information, il est entendu un contexte allant jusqu'à 100k de tokens (en input) avec des performance raisonnnable. Ces performances sont calculées sur le temps de traitement (<5 min), et par le taux de remplissage / la précision des informations. Ces précisions ont d'abord été évaluées @chatgpt/@perplexity (cycle rapide), puis lorsque les résultats ont été jugés comme bons, par des professionnels de la santé.  

## Stack utilisée

- Hardware : gpu = RTX 4080 SUPER 16Go ; cpu = intel i9-14900k ; ram = 64 Go ; 
- Software : LM Studio 0.3.36
- LLM : [qwen2.5-14b-instruct](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF)
- EMBD : text-embedding-nomic-embed-text-v1.5
- Reranking : cross-encoder/ms-marco-MiniLM-L-6-v2
- Language : Python 3.13.5

## Configuration
0) Créer un environnement virtuel python (`python -m venv venv`) et l'activer (macos/linux: `source venv/bin/activate`, win11: `DF-PoC-01\Scripts\activate`)
1) installer le modèle (qwen2.5-14b-instruct), puis lancer le serveur LM Studio (https://lmstudio.ai/docs/developer/core/server)
```txt
# configuration du serveur
- contexte mis à 8192 (au lieu de ~130k)
Le reste est laisser par défaut
```
2) Changer la variable `LM_STUDIO_URL` si l'IP et le port ne sont pas : `192.168.1.170:1734`. 
3) Utiliser/créer une template QA (le format est relativement libre, il faut cependant adapter le prompt dans ce cas) et ajouter un contexte (format `.txt`)
4) Changer les variables PATH si nécessaire
5) Exéuter l'app : `python pipeline.py`

## Résultats

### first pass
First pass [commit: 9c817bb0951ad559d7e1ef5baa381223c7de9365] - [doc](tmp/output/resultat_final_v01.json) :
```bash
📂 Chargement des données...
✂️  Découpage terminé : 9 documents extraits.
⏳ Indexation des documents en cours...
✅ 9 segments indexés dans ChromaDB.

🚀 Démarrage de l'extraction en mode BATCH (77 champs valides)...

100%|██████████| 16/16 [14:11<00:00, 53.23s/batch]

✅ Extraction terminée. 76 champs traités.
📁 Résultats dans 'resultat_final.json'
```

✅ Extraction terminée avec Reranking. 75 champs traités.
```
