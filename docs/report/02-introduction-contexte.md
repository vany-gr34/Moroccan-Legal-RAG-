# 2. Introduction et Contexte

---

## 2.1 Problematique Juridique au Maroc

Le systeme juridique marocain repose sur un ensemble de textes legislatifs
publies principalement en arabe, avec certaines dispositions en francais.
L'acces a ces textes presente plusieurs defis :

1. **Dispersion des sources** : Les lois sont publiees dans le Bulletin Officiel,
   sur des sites gouvernementaux, et dans des recueils prives, sans portail unifie.

2. **Format non structure** : La majorite des textes historiques existe uniquement
   au format PDF scanne, rendant la recherche plein-texte impossible.

3. **Barriere linguistique** : L'arabe juridique utilise un vocabulaire specialise
   et des formulations complexes, creant un fosse entre la langue du citoyen et
   celle du legislateur.

4. **Absence d'outils intelligents** : Il n'existe pas de systeme de
   question-reponse permettant a un citoyen ou un professionnel de poser une
   question en langage naturel et d'obtenir une reponse fondee sur les textes.

```
+---------------------------+     +---------------------------+
|         CITOYEN           |     |      PROFESSIONNEL        |
| "Quelle est la peine      |     | "Quels sont les articles  |
|  pour le vol ?"           |     |  sur la SARL ?"           |
+------------+--------------+     +------------+--------------+
             |                                  |
             v                                  v
+----------------------------------------------------------+
|                   PROBLEME ACTUEL                         |
|                                                          |
|  1. Chercher manuellement dans des PDF lourds             |
|  2. Lire des textes en arabe juridique complexe           |
|  3. Croiser plusieurs lois manuellement                   |
|  4. Risque d'interpretation erronee                       |
|                                                          |
|  -> Pas d'assistant automatise disponible                 |
+----------------------------------------------------------+
```

## 2.2 Objectifs du Projet

Ce projet vise a construire un systeme de **Question-Reponse Juridique**
fonde sur l'architecture RAG (Retrieval-Augmented Generation) avec les
objectifs suivants :

1. **Constituer un corpus juridique marocain structure**
   Extraire, nettoyer et structurer les textes de loi a partir de PDF
   scannes en utilisant l'OCR et la correction par VLM.

2. **Permettre la recherche semantique multilingue**
   Indexer les articles juridiques sous forme de vecteurs semantiques
   (embeddings) pour permettre une recherche par similarite de sens,
   au-dela des mots-cles exacts.

3. **Generer des reponses juridiques fondees**
   Utiliser un LLM (Large Language Model) pour generer des reponses
   en arabe, ancrees exclusivement dans les textes officiels retrouves,
   reduisant ainsi le risque d'hallucination.

4. **Evaluer scientifiquement les performances**
   Mener des benchmarks systematiques des modeles d'embedding et des
   strategies de recherche pour l'arabe juridique marocain.

## 2.3 Perimetre    

### Domaines juridiques couverts

| Domaine                      | Lois principales                                   | Articles |
|------------------------------|---------------------------------------------------|----------|
| Droit Penal                  | Code Penal Marocain, Code des Sanctions            | ~800     |
| Circulation                  | Code de la Route Marocain                          | ~230     |
| Droit Civil                  | Code des Obligations et Contrats, Procedure Civile | ~500     |
| Droit Commercial             | Registre du Commerce, Loi sur les Societes         | ~360     |
| Droit de la Famille          | Moudawana                                          | ~400     |
| Organisation Judiciaire      | Loi 38.15, Decret sur la Carte Judiciaire          | ~35      |
| Droit Fiscal                 | Code General des Impots 2024                       | ~210     |

### Formats sources

- **PDF scannes** : Bulletins officiels numerises (OCR necessaire)
- **PDF texte** : Documents avec texte selectionnable (extraction directe)
- **Ressources web** : Textes publies sur les sites gouvernementaux

### Langues

- **Arabe** : Langue principale des textes de loi et des requetes
- **Francais** : Certains textes et terminologie juridique
