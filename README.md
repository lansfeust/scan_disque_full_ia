Voici le contenu de `README.md` full IA :

---

# Scan Disque — détecteur de doublons

Deux scripts Python simples pour comparer deux disques durs et trouver les fichiers en double.

## Comment ça marche

1. `scan_disque.py` parcourt **TOUT** les fichiers d'un disque (textes, PDF, vidéos, photos, musiques, jeux, programmes... sans aucune exception) et écrit un fichier JSON contenant, pour chaque contenu unique :
   - les noms des fichiers,
   - la taille,
   - le hash (une "empreinte" du contenu, calculée en SHA-256),
   - la liste des emplacements de toutes les copies.

2. `compare_doublons.py` compare les deux JSON créés à l'étape 1 et détecte :
   - les copies présentes sur **les deux disques** ;
   - les copies qui existent plusieurs fois **sur un même disque**.

> Important : la comparaison se fait **uniquement sur la taille et le hash**. Le nom du fichier n'est pas utilisé, car un fichier renommé reste une copie exacte.

## Prérequis

- Python 3 (installé par défaut sur la plupart des systèmes).
- Aucune bibliothèque à installer : tout utilise le standard Python.

## Utilisation

### Étape 1 : scanner les deux disques

Remplacez `/media/disque1` et `/media/disque2` par vos propres disques (visibles dans le gestionnaire de fichiers, ou avec la commande `ls /media` / `ls /mnt`).

```bash
python3 scan_disque.py /media/disque1 -o disque1.json
python3 scan_disque.py /media/disque2 -o disque2.json
```

Le scan peut être long sur un gros disque car chaque fichier est entièrement lu pour calculer son hash. Un message de progression s'affiche tous les 500 fichiers.

### Étape 2 : comparer les deux scans

```bash
python3 compare_doublons.py disque1.json disque2.json -o rapport_doublons.json
```

Le terminal affiche un résumé (nombre de doublons, espace occupé en double, premiers emplacements), et le détail complet est écrit dans `rapport_doublons.json`.

## Exemple de JSON produit par le scan

```json
{
  "noms": ["doc.txt"],
  "taille": 22,
  "hash": "47d3ea68a42075d857946f9c4ba5f8e4afaeeaf1eb82d96db620c057188afcfc",
  "emplacements": ["/media/disque1/doc.txt", "/media/disque1/sauvegarde/doc.txt"]
}
```

## Détails utiles

- Les fichiers illisibles (protégés, système...) n'arrêtent pas le scan : ils sont listés dans la section `fichiers_non_lus` du JSON.
- Les "raccourcis" système (liens symboliques) sont ignorés pour ne pas compter plusieurs fois le même fichier.
- Les deux scans doivent être faits avec la même version du script : le comparateur refuse deux JSON incompatibles.

## Windows

Sous Windows, remplacez simplement les chemins : `python scan_disque.py D:\ -o disqueD.json` à lancer dans une invite de commandes (PowerShell ou cmd).

---

Souhaitez-vous que je modifie quelque chose dans ce README (par exemple ajouter une section « que faire des doublons trouvés », ou plus de détails sur un point) ? Et le push vers `lansfeust/scan_disque_full_ia` est toujours en attente : dès que vous accordez l'accès en écriture au dépôt (ré-authentification ou [installation de l'application GitHub](https://github.com/apps/mistralai/installations/new)), dites-le-moi et je pousse l'ensemble.
