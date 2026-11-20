#!/usr/bin/env python3
# =====================================================================
# SCAN DE DISQUE
# Ce programme parcourt TOUT les fichiers d'un disque ou d'un dossier :
# textes, PDF, vidéos, photos, musiques, jeux, programmes... sans
# aucune exception. Pour chaque fichier, il note :
#     - la taille du fichier
#     - le hash du fichier (une "empreinte" unique du contenu)
#     - où il se trouve sur le disque
# Puis il regroupe les fichiers identiques (même taille ET même hash)
# et écrit tout ça dans un fichier JSON.
# =====================================================================

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

# On lit les gros fichiers par morceaux de 1 Mo (sinon un fichier de
# plusieurs Go ne tiendrait pas en mémoire d'un seul coup).
TAILLE_D_UN_BLOC = 1024 * 1024


# ---------------------------------------------------------------------
# ÉTAPE A : calculer le hash d'un fichier
# ---------------------------------------------------------------------
# Le hash est une longue suite de lettres et chiffres qui représente
# le CONTENU du fichier. Deux fichiers ont le même hash uniquement
# s'ils contiennent exactement les mêmes octets, même si leurs noms
# ou leurs dossiers sont différents.
def calculer_hash(chemin_complet):
    empreinte = hashlib.sha256()
    with open(chemin_complet, "rb") as fichier:
        while True:
            morceau_lu = fichier.read(TAILLE_D_UN_BLOC)
            if morceau_lu == b"":          # b"" signifie "plus rien à lire"
                break
            empreinte.update(morceau_lu)
    return empreinte.hexdigest()


# ---------------------------------------------------------------------
# ÉTAPE B : parcourir le disque et décrire chaque fichier
# ---------------------------------------------------------------------
def scanner_tout_le_disque(dossier_de_depart):
    liste_des_fichiers = []     # la description de chaque fichier trouvé
    messages_d_erreur = []      # les fichiers impossibles à lire (mot de passe, etc.)

    # os.walk visite le dossier de départ, puis TOUS ses sous-dossiers,
    # et ainsi de suite jusqu'au dernier fichier. Aucun type de fichier
    # n'est filtré : tout est pris.
    for dossier_en_cours, sous_dossiers, noms_trouves in os.walk(
            dossier_de_depart, onerror=lambda erreur: messages_d_erreur.append(str(erreur))):
        for nom_du_fichier in noms_trouves:
            chemin_complet = os.path.join(dossier_en_cours, nom_du_fichier)

            # On saute les "raccourcis" (liens symboliques) pour éviter
            # de compter plusieurs fois le même fichier ou de tourner en rond.
            if os.path.islink(chemin_complet):
                continue

            try:
                taille = os.path.getsize(chemin_complet)
                hash_du_fichier = calculer_hash(chemin_complet)
            except OSError as erreur:
                # Fichier illisible : on le note et on continue le scan.
                messages_d_erreur.append(f"{chemin_complet} : {erreur}")
                continue

            liste_des_fichiers.append({
                "nom": nom_du_fichier,
                "chemin": os.path.abspath(chemin_complet),
                "taille": taille,
                "hash": hash_du_fichier,
            })

            # Petit message de progression dans le terminal (tous les 500 fichiers).
            if len(liste_des_fichiers) % 500 == 0:
                print(f"    ... {len(liste_des_fichiers)} fichiers déjà analysés")

    return liste_des_fichiers, messages_d_erreur


# ---------------------------------------------------------------------
# ÉTAPE C : regrouper les fichiers qui sont des copies l'un de l'autre
# ---------------------------------------------------------------------
# Deux fichiers sont "copies" s'ils ont la même taille ET le même hash.
# On les met donc dans une même boîte avec la liste de leurs emplacements.
def regrouper_les_copies(liste_des_fichiers):
    groupes = {}
    for fichier in liste_des_fichiers:
        cle = (fichier["taille"], fichier["hash"])
        if cle not in groupes:
            groupes[cle] = []
        groupes[cle].append(fichier["chemin"])
    return groupes


# ---------------------------------------------------------------------
# ÉTAPE D : écrire le résultat dans le fichier JSON
# ---------------------------------------------------------------------
def main():
    # On lit ce que l'utilisateur a tapé dans le terminal.
    parser = argparse.ArgumentParser(
        description="Scanne un disque et crée un JSON listant tous les fichiers (avec copies regroupées).")
    parser.add_argument("dossier", help="Le disque ou le dossier à scanner (exemple : /media/disque2)")
    parser.add_argument("-o", "--sortie", required=True,
                        help="Le nom du fichier JSON de résultat (exemple : disque2.json)")
    args = parser.parse_args()

    if not os.path.isdir(args.dossier):
        # Le chemin tapé n'existe pas : on arrête tout avec un message clair.
        raise SystemExit(f"Erreur : « {args.dossier} » n'est pas un dossier accessible.")

    print(f"Début du scan de « {args.dossier} » (cela peut être long sur un gros disque)...")

    liste_des_fichiers, messages_d_erreur = scanner_tout_le_disque(args.dossier)
    groupes = regrouper_les_copies(liste_des_fichiers)

    # On prépare le contenu du JSON.
    fichiers_pour_le_json = []
    for (taille, hash_du_fichier), emplacements in sorted(groupes.items()):
        noms_differents = sorted({os.path.basename(chemin) for chemin in emplacements})
        fichiers_pour_le_json.append({
            "noms": noms_differents,
            "taille": taille,
            "hash": hash_du_fichier,
            "emplacements": sorted(emplacements),
        })

    resultat_json = {
        "dossier_scanne": os.path.abspath(args.dossier),
        "date_du_scan": datetime.now(timezone.utc).isoformat(),
        "methode_de_comparaison": "taille + hash sha256 (le nom n'est PAS utilisé)",
        "nombre_de_fichiers_trouves": len(liste_des_fichiers),
        "nombre_de_contenus_distincts": len(groupes),
        "fichiers": fichiers_pour_le_json,
        "fichiers_non_lus": sorted(set(messages_d_erreur)),
    }

    # On écrit le JSON sur le disque.
    with open(args.sortie, "w", encoding="utf-8") as fichier_json:
        json.dump(resultat_json, fichier_json, ensure_ascii=False, indent=2)

    # Petit résumé pour l'utilisateur.
    print(f"Scan terminé : {len(liste_des_fichiers)} fichiers trouvés, "
          f"regroupés en {len(groupes)} contenus différents.")
    if messages_d_erreur:
        print(f"Attention : {len(messages_d_erreur)} fichier(s) n'ont pas pu être lus "
              f"(liste en fin du fichier JSON).")
    print(f"Résultat écrit dans : {args.sortie}")


if __name__ == "__main__":
    main()
