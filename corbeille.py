#!/usr/bin/env python3
# =====================================================================
# CORBEILLE
# Ce module fournit UNE fonction : envoyer_a_la_corbeille(chemin).
# Elle déplace un fichier vers la corbeille du système, comme si
# l'utilisateur appuyait sur la touche "Suppr" dans son gestionnaire
# de fichiers. Le fichier N'EST PAS détruit définitivement : il peut
# être restauré (clic droit -> restaurer).
#
# Comment ça marche selon le système :
#   - Si la petite bibliothèque "send2trash" est installée, on
#     l'utilise (elle gère parfaitement les trois systèmes).
#   - Windows  : on demande à Windows (via PowerShell) de mettre le
#                fichier à la corbeille.
#   - macOS    : on demande au Finder de supprimer le fichier
#                (ce qui le met à la corbeille).
#   - Linux    : on déplace le fichier dans la corbeille officielle
#                (~/.local/share/Trash) selon la norme "FreeDesktop".
# =====================================================================

import datetime
import os
import platform
import subprocess
import urllib.parse

# ---------------------------------------------------------------------
# Tentative d'utilisation de la bibliothèque "send2trash"
# si elle est installée (pip install send2trash). Sinon, on utilisera
# les méthodes internes décrites ci-dessous.
# ---------------------------------------------------------------------
try:
    from send2trash import send2trash as _envoi_avec_send2trash
    send2trash_est_disponible = True
except ImportError:
    send2trash_est_disponible = False


def envoyer_a_la_corbeille(chemin):
    """Met le fichier situé à « chemin » dans la corbeille du système."""

    if send2trash_est_disponible:
        _envoi_avec_send2trash(chemin)
        return

    systeme = platform.system()
    if systeme == "Windows":
        corbeille_windows(chemin)
    elif systeme == "Darwin":          # "Darwin" est le nom interne de macOS
        corbeille_macos(chemin)
    else:                              # Linux et les autres systèmes libres
        corbeille_linux(chemin)


# ---------------------------------------------------------------------
# WINDOWS : on utilise PowerShell, présent sur tous les Windows
# récents. La commande appelle la fonction Visual Basic officielle
# "DeleteFile" avec l'option "SendToRecycleBin" (mise à la corbeille).
# ---------------------------------------------------------------------
def corbeille_windows(chemin):
    chemin_pour_powershell = chemin.replace("'", "''")   # échapper les apostrophes
    commande_powershell = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
        f"'{chemin_pour_powershell}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    resultat = subprocess.run(
        ["powershell", "-NoProfile", "-Command", commande_powershell],
        capture_output=True, text=True,
    )
    if resultat.returncode != 0:
        raise OSError(resultat.stderr.strip() or "Windows a refusé la mise à la corbeille.")


# ---------------------------------------------------------------------
# macOS : on demande au Finder de « delete » le fichier, ce qui le
# met à la corbeille (et PAS une suppression définitive).
# ---------------------------------------------------------------------
def corbeille_macos(chemin):
    chemin_pour_applescript = chemin.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Finder" to delete POSIX file "{chemin_pour_applescript}"'
    resultat = subprocess.run(["osascript", "-e", script],
                              capture_output=True, text=True)
    if resultat.returncode != 0:
        raise OSError(resultat.stderr.strip() or "macOS a refusé la mise à la corbeille.")


# ---------------------------------------------------------------------
# LINUX : norme officielle "FreeDesktop". La corbeille se trouve dans
# le dossier personnel :  ~/.local/share/Trash
#     - les fichiers déplacés vont dans  Trash/files
#     - un petit fichier d'information va dans  Trash/info
#       (il permet au gestionnaire de fichiers d'afficher le fichier
#       dans la corbeille et de savoir le restaurer où il était)
# Attention : si le fichier est sur un autre disque que le dossier
# personnel, le déplacement peut échouer ; dans ce cas un message
# d'erreur sera affiché à l'utilisateur plutôt qu'une suppression.
# ---------------------------------------------------------------------
def corbeille_linux(chemin):
    chemin = os.path.abspath(chemin)
    racine_de_la_corbeille = os.path.expanduser("~/.local/share/Trash")
    dossier_des_fichiers = os.path.join(racine_de_la_corbeille, "files")
    dossier_des_infos = os.path.join(racine_de_la_corbeille, "info")

    # On crée les dossiers de la corbeille s'ils n'existent pas encore.
    os.makedirs(dossier_des_fichiers, exist_ok=True)
    os.makedirs(dossier_des_infos, exist_ok=True)

    # On choisit un nom non utilisé dans la corbeille
    # (si "rapport.txt" existe déjà, on essaira "rapport.1.txt", etc.).
    nom_d_origine = os.path.basename(chemin)
    destination = os.path.join(dossier_des_fichiers, nom_d_origine)
    compteur = 1
    while os.path.exists(destination):
        racine_du_nom, extension = os.path.splitext(nom_d_origine)
        destination = os.path.join(dossier_des_fichiers,
                                   f"{racine_du_nom}.{compteur}{extension}")
        compteur += 1

    # Le déplacement vers la corbeille. Si le fichier est sur un disque
    # différent, os.rename échoue et lève une erreur : c'est voulu, il
    # vaut mieux prévenir que supprimer définitivement par accident.
    os.rename(chemin, destination)
    nom_final = os.path.basename(destination)

    # Le fichier d'information demandé par la norme (format .trashinfo).
    chemin_du_fichier_info = os.path.join(dossier_des_infos, nom_final + ".trashinfo")
    date_de_suppression = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(chemin_du_fichier_info, "w", encoding="utf-8") as fichier_info:
        fichier_info.write("[Trash Info]\n")
        fichier_info.write("Path=" + urllib.parse.quote(chemin) + "\n")
        fichier_info.write("DeletionDate=" + date_de_suppression + "\n")
