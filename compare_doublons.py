#!/usr/bin/env python3
# =====================================================================
# COMPARATEUR DE DEUX DISQUES
# Ce programme compare deux fichiers JSON créés par "scan_disque.py"
# et détecte les doublons.
#
# IMPORTANT : la comparaison se fait UNIQUEMENT sur la taille et le
# hash. Le nom du fichier n'est PAS utilisé, car un fichier copié peut
# très bien avoir été renommé et rester une copie exacte.
#
# Le programme détecte :
#     1. les copies présentes sur LES DEUX disques ;
#     2. les copies qui existent plusieurs fois SUR UN MÊME disque.
# =====================================================================

import argparse
import json


# ---------------------------------------------------------------------
# ÉTAPE A : lire un fichier JSON de scan et en faire un tableau simple
# ---------------------------------------------------------------------
# Exemple de tableau produit : { (taille, hash) : [chemins des copies...] }
def charger_un_scan(chemin_du_json):
    with open(chemin_du_json, encoding="utf-8") as fichier:
        contenu_du_json = json.load(fichier)

    tableau = {}
    for groupe in contenu_du_json.get("fichiers", []):
        cle = (groupe["taille"], groupe["hash"])   # PAS le nom du fichier !
        tableau[cle] = groupe["emplacements"]

    systeme = contenu_du_json.get("algorithme_hash") or contenu_du_json.get("methode_de_comparaison", "")
    return contenu_du_json, tableau, systeme


# ---------------------------------------------------------------------
# ÉTAPE B : rendre une taille lisible (par exemple 1536 -> "1.5 Ko")
# ---------------------------------------------------------------------
def taille_lisible(taille_en_octets):
    taille = taille_en_octets
    for unite in ("o", "Ko", "Mo", "Go", "To"):
        if taille < 1024:
            if unite == "o":
                return f"{taille} o"
            return f"{round(taille, 1)} {unite}"
        taille = taille / 1024
    return f"{round(taille, 1)} Po"


# ---------------------------------------------------------------------
# ÉTAPE C : la comparaison des deux disques
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Compare deux JSON de scans et trouve les doublons (par taille + hash uniquement).")
    parser.add_argument("json_disque1", help="JSON du 1er disque (exemple : disque1.json)")
    parser.add_argument("json_disque2", help="JSON du 2e disque (exemple : disque2.json)")
    parser.add_argument("-o", "--sortie", default="rapport_doublons.json",
                        help="Nom du rapport JSON (par défaut : rapport_doublons.json)")
    args = parser.parse_args()

    # On lit les deux scans.
    try:
        scan1, tableau1, methode1 = charger_un_scan(args.json_disque1)
        scan2, tableau2, methode2 = charger_un_scan(args.json_disque2)
    except (OSError, json.JSONDecodeError) as erreur:
        raise SystemExit(f"Impossible de lire un des deux fichiers JSON : {erreur}")

    # Sécurité : si les deux scans n'ont pas été faits avec la même méthode
    # de hash, la comparaison n'a aucun sens, on arrête tout.
    if methode1 != methode2:
        raise SystemExit("Erreur : les deux scans n'utilisent pas la même méthode de hash. "
                         "Relancez les DEUX scans pour pouvoir comparer.")

    # ----- 1) Copies présentes sur les deux disques -----
    # On prend les clés (taille, hash) qui existent dans les DEUX tableaux.
    doublons_entre_disques = []
    for cle in sorted(set(tableau1).intersection(tableau2)):
        taille, hash_du_fichier = cle
        doublons_entre_disques.append({
            "taille": taille,
            "hash": hash_du_fichier,
            "emplacements_sur_disque1": tableau1[cle],
            "emplacements_sur_disque2": tableau2[cle],
        })

    # ----- 2) Copies en plusieurs exemplaires sur un seul disque -----
    def trouver_copies_internes(tableau):
        resultat = []
        for cle in sorted(tableau):
            taille, hash_du_fichier = cle
            if len(tableau[cle]) > 1:
                resultat.append({
                    "taille": taille,
                    "hash": hash_du_fichier,
                    "emplacements": tableau[cle],
                })
        return resultat

    copies_internes_disque1 = trouver_copies_internes(tableau1)
    copies_internes_disque2 = trouver_copies_internes(tableau2)

    # ----- 3) Écriture du rapport JSON -----
    rapport = {
        "disque1": scan1.get("dossier_scanne", args.json_disque1),
        "disque2": scan2.get("dossier_scanne", args.json_disque2),
        "methode_de_comparaison": "taille + hash uniquement (le nom n'est pas utilisé)",
        "doublons_entre_les_deux_disques": doublons_entre_disques,
        "copies_internes_au_disque1": copies_internes_disque1,
        "copies_internes_au_disque2": copies_internes_disque2,
    }

    with open(args.sortie, "w", encoding="utf-8") as fichier_rapport:
        json.dump(rapport, fichier_rapport, ensure_ascii=False, indent=2)

    # ---------- Résumé lisible dans le terminal ----------
    nombre_de_doublons = len(doublons_entre_disques)
    espace_en_double = sum(doublon["taille"] for doublon in doublons_entre_disques)

    print(f"Disque 1 : {scan1.get('dossier_scanne', args.json_disque1)}")
    print(f"Disque 2 : {scan2.get('dossier_scanne', args.json_disque2)}")
    print("")
    if nombre_de_doublons == 0:
        print("Résultat : les deux disques n'ont AUCUN fichier en commun.")
    else:
        print(f"Résultat : {nombre_de_doublons} fichier(s) existe(nt) sur les deux disques.")
        print(f"          Ces doublons occupent {taille_lisible(espace_en_double)} sur le disque 2.")
        for doublon in doublons_entre_disques[:10]:
            for chemin in doublon["emplacements_sur_disque1"]:
                print(f"    disque 1 : {chemin}")
            for chemin in doublon["emplacements_sur_disque2"]:
                print(f"    disque 2 : {chemin}")
            print("")
        if nombre_de_doublons > 10:
            print(f"    (... et {nombre_de_doublons - 10} autres, voir le rapport JSON)")
    print(f"Copies en plusieurs exemplaires sur le disque 1 : {len(copies_internes_disque1)}")
    print(f"Copies en plusieurs exemplaires sur le disque 2 : {len(copies_internes_disque2)}")
    print(f"Rapport complet écrit dans : {args.sortie}")


if __name__ == "__main__":
    main()
