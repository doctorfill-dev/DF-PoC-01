# DF-POC-01
<div align="center">
  <img src="doctorfill-banner.svg" alt="Doctorfill logo" width="600">
</div>


Ce PoC a pour but de tester la possibilité de traiter une grande quantité d'informations avec une configuration locale raisonnable, avec des performances raisonnables. 

Le but global du projet nommé Doctorfill est de construire une application locale qui remplit automatiquement un formulaire PDF à partir d’un contexte documentaire (principalement des rapports médicaux). Le contexte peut être volumineux (~80’000 tokens). L’application doit proposer une extraction fiable, traçable (sources/citations) et produire une sortie exploitable pour remplir le PDF.

Par grande quantité d'information, il est entendu un contexte allant jusqu'à 100k de tokens (en input). Et par performance raisonnnable, il est calculé sur le temps de traitement (<5 min), et par le taux de remplissage / la précision des informations. Ces KPI sont évaluées dans les premiers essais, par @chatgpt, puis lorsque les résultats semblent bons, par des professionnels de la santé. 

## Stack utilisée

- Hardware : gpu = RTX 4080 SUPER 16Go ; cpu = intel i9-14900k ; ram = 64 Go ; 
- Software : LM Studio 0.3.36
- LLM : [qwen2.5-14b-instruct](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF)
- EMBD : text-embedding-nomic-embed-text-v1.5
- Reranking : cross-encoder/ms-marco-MiniLM-L-6-v2
- Language : Python 3.13.5

## Configuration

1) lancer le serveur LM Studio (https://lmstudio.ai/docs/developer/core/server)
```txt
# configuration du serveur
- contexte mis à 8192 (au lieu de ~130k)
Le reste est laisser par défaut
```
2) Changer la variable `LM_STUDIO_URL` si l'IP et le port ne sont pas : `192.168.1.170:1734`
3) Utiliser/créer une template QA et ajouter un contexte (format .txt)
4) Changer les variables PATH si nécessaire
5) Exéuter l'app v

## Résultats

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

Second pass [commit: e18a30e625068c2decffc3457c25985190cd2177] - [doc](tmp/output/resultat_final_v02.json):
```bash
 88%|████████▊ | 14/16 [13:49<02:17, 68.81s/batch]⚠️ Erreur JSON sur ce batch : Expecting ':' delimiter: line 1 column 661 (char 660)
100%|██████████| 16/16 [15:17<00:00, 57.34s/batch]
```

Third pass [commit: 09f25bbb0ee150e2031d0553da07574f560fe080] - [doc](tmp/output/resultat_final_v03.json):
- changement des réglages dans LM Studio :
  - `8192` de longueur de contexte (ancienne valeur : `131072`)

```bash
100%|██████████| 16/16 [01:33<00:00,  5.84s/batch]
```

Fourth pass [commit: 214ba6762dd1e3f3c8d00c4e3e1e3608e0b56eef] - [doc](tmp/output/resultat_final_v04.json):
- context window : 8192
- Nouveauté: reranking

```bash
⚖️  Chargement du modèle de Reranking (Cross-Encoder)...
📂 Chargement des données...
✂️  Découpage terminé : 9 documents extraits.
⏳ Indexation des documents en cours...
  0%|          | 0/16 [00:00<?, ?batch/s]✅ 9 segments indexés dans ChromaDB.

🚀 Démarrage Extraction (Mode: Batching + Reranking + TokenGuard)

100%|██████████| 16/16 [01:52<00:00,  7.03s/batch]

✅ Extraction terminée avec Reranking. 75 champs traités.
```
