#!/usr/bin/env python3
# =====================================================================
# INTERFACE DE GESTION DES DOUBLONS
#
# Ce programme lit le fichier « rapport_doublons.json » créé par
# « compare_doublons.py » et affiche les doublons dans une fenêtre.
#
# DEUX FENÊTRES :
#
#   1. La fenêtre PRINCIPALE (ouverte au démarrage) :
#        - chaque groupe de copies identiques est affiché dans un
#          bloc séparé et indépendant ;
#        - dans chaque bloc : le nom et l'emplacement de chaque copie ;
#        - à la fin de chaque copie, un bouton radio permet de la
#          désigner ;
#        - le bouton « Supprimer » envoie à la CORBEILLE du système
#          (pas une suppression définitive !) toutes les copies
#          désignées par les boutons radio, puis met le rapport à jour.
#
#   2. La fenêtre FILTRES (ouverte par le bouton « Filtres... ») :
#        - permet d'AJOUTER et de SUPPRIMER des filtres d'affichage ;
#        - soit on montre seulement les blocs contenant les textes
#          des filtres, soit on les cache.
#
# Prérequis : Python 3. Aucune bibliothèque supplémentaire obligatoire.
# =====================================================================

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import corbeille

FICHIER_RAPPORT_PAR_DEFAUT = "rapport_doublons.json"


# ---------------------------------------------------------------------
# Petit outil : transformer un nombre d'octets en texte lisible
# (par exemple 1536 devient "1.5 Ko").
# ---------------------------------------------------------------------
def taille_lisible(taille_en_octets):
    taille = float(taille_en_octets)
    for unite in ("o", "Ko", "Mo", "Go", "To"):
        if taille < 1024:
            if unite == "o":
                return f"{int(taille)} o"
            return f"{round(taille, 1)} {unite}"
        taille = taille / 1024
    return f"{round(taille, 1)} Po"


class Application(tk.Tk):
    """La fenêtre principale du programme."""

    def __init__(self):
        super().__init__()
        self.title("Gestion des doublons")
        self.geometry("900x600")

        # --- Les données dont l'application se sert -----------------
        self.chemin_du_rapport = None     # où est le fichier rapport_doublons.json
        self.rapport = {}                 # le contenu du rapport (les doublons)
        self.blocs = []                   # un par groupe de copies :
                                          # {cadre, variable_radio, emplacements, taille, noms}
        self.liste_des_filtres = []       # les textes des filtres actifs
        self.mode_des_filtres = tk.StringVar(value="montrer")   # "montrer" ou "cacher"

        # --- Au démarrage : trouver le fichier du rapport -----------
        if os.path.exists(FICHIER_RAPPORT_PAR_DEFAUT):
            self.chemin_du_rapport = FICHIER_RAPPORT_PAR_DEFAUT
        else:
            # Le fichier n'est pas à côté du programme : on demande à l'utilisateur.
            choisi = filedialog.askopenfilename(
                title="Choisir le fichier rapport_doublons.json",
                filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")])
            if not choisi:
                raise SystemExit("Aucun rapport choisi : fermeture.")
            self.chemin_du_rapport = choisi

        # --- Construction de la fenêtre -----------------------------
        self.construire_le_haut_de_la_fenetre()
        self.construire_la_zone_avec_ascenceur()
        self.construire_le_bouton_supprimer()

        # --- Lecture du rapport et affichage des blocs --------------
        self.charger_et_afficher_le_rapport()

    # =================================================================
    # CONSTRUCTION DE LA FENÊTRE (faite une seule fois au démarrage)
    # =================================================================

    def construire_le_haut_de_la_fenetre(self):
        """Le bandeau du haut : bouton « Filtres... » et résumé."""

        bandeau = tk.Frame(self)
        bandeau.pack(side="top", fill="x", padx=8, pady=6)

        ttk.Button(bandeau, text="Filtres...",
                   command=self.ouvrir_la_fenetre_des_filtres).pack(side="left")

        # Ce texte indique combien de groupes sont visibles / en tout.
        self.texte_de_resume = tk.Label(bandeau, anchor="w")
        self.texte_de_resume.pack(side="left", fill="x", expand=True, padx=10)

    def construire_la_zone_avec_ascenceur(self):
        """Une zone qui défile verticalement (car il y a souvent des
        dizaines de blocs de doublons à afficher)."""

        cadre_de_la_zone = tk.Frame(self)
        cadre_de_la_zone.pack(side="top", fill="both", expand=True)

        self.zone_defilante = tk.Canvas(cadre_de_la_zone)
        ascenceur = ttk.Scrollbar(cadre_de_la_zone, orient="vertical",
                                  command=self.zone_defilante.yview)
        self.zone_defilante.configure(yscrollcommand=ascenceur.set)
        ascenceur.pack(side="right", fill="y")
        self.zone_defilante.pack(side="left", fill="both", expand=True)

        # Un cadre intérieur « flottant » à l'intérieur de la zone défilante :
        # c'est lui qui contiendra tous les blocs de doublons.
        self.cadre_des_blocs = tk.Frame(self.zone_defilante)
        self.zone_defilante.create_window((0, 0), window=self.cadre_des_blocs, anchor="nw")

        # À chaque fois que le contenu change de taille, on ajuste la zone défilante.
        self.cadre_des_blocs.bind(
            "<Configure>",
            lambda evenement: self.zone_defilante.configure(
                scrollregion=self.zone_defilante.bbox("all")))

        # La molette de la souris fait défiler la zone.
        self.zone_defilante.bind_all("<MouseWheel>", self.defiler_avec_la_molette)
        self.zone_defilante.bind_all("<Button-4>", self.defiler_avec_la_molette)   # Linux (molette haut)
        self.zone_defilante.bind_all("<Button-5>", self.defiler_avec_la_molette)   # Linux (molette bas)

    def construire_le_bouton_supprimer(self):
        """Le bandeau du bas avec le gros bouton « Supprimer »."""

        bandeau = tk.Frame(self)
        bandeau.pack(side="bottom", fill="x", padx=8, pady=8)
        ttk.Button(bandeau, text="Supprimer", width=25,
                   command=self.supprimer_la_selection).pack()

    def defiler_avec_la_molette(self, evenement):
        if evenement.num == 4:            # Linux : molette vers le haut
            self.zone_defilante.yview_scroll(-1, "units")
        elif evenement.num == 5:          # Linux : molette vers le bas
            self.zone_defilante.yview_scroll(1, "units")
        else:                             # Windows / macOS
            self.zone_defilante.yview_scroll(-1 if evenement.delta > 0 else 1, "units")

    # =================================================================
    # LECTURE DU RAPPORT ET AFFICHAGE DES BLOCS
    # =================================================================

    def lire_le_rapport(self):
        """Lit le fichier JSON du rapport et le mémorise."""
        with open(self.chemin_du_rapport, encoding="utf-8") as fichier:
            self.rapport = json.load(fichier)

    def groupes_de_copies_dans_le_rapport(self):
        """Renvoie la liste des groupes de copies identiques, quelle que soit
        la partie du rapport où ils se trouvent. Chaque groupe est un
        dictionnaire : {taille, hash, emplacements}."""

        groupes = []

        # Les copies présentes sur les DEUX disques : on fusionne les
        # emplacements des deux disques dans une seule liste.
        for groupe in self.rapport.get("doublons_entre_les_deux_disques", []):
            emplacements = (list(groupe.get("emplacements_sur_disque1", []))
                            + list(groupe.get("emplacements_sur_disque2", [])))
            if len(emplacements) >= 2:
                groupes.append({"taille": groupe.get("taille", 0),
                                "hash": groupe.get("hash", ""),
                                "emplacements": emplacements})

        # Les copies en plusieurs exemplaires sur un seul disque.
        for cle in ("copies_internes_au_disque1", "copies_internes_au_disque2"):
            for groupe in self.rapport.get(cle, []):
                if len(groupe.get("emplacements", [])) >= 2:
                    groupes.append({"taille": groupe.get("taille", 0),
                                    "hash": groupe.get("hash", ""),
                                    "emplacements": list(groupe["emplacements"])})

        return groupes

    def charger_et_afficher_le_rapport(self):
        """(Re)construit l'affichage à partir du fichier du rapport."""

        self.lire_le_rapport()

        # On efface tous les blocs actuellement affichés.
        for enfant in self.cadre_des_blocs.winfo_children():
            enfant.destroy()
        self.blocs = []

        # On crée un bloc pour chaque groupe de copies identiques.
        for groupe in self.groupes_de_copies_dans_le_rapport():
            self.creer_un_bloc(groupe)

        self.appliquer_les_filtres()

    def creer_un_bloc(self, groupe):
        """Crée le cadre visuel d'UN groupe de copies identiques.

        Le bloc contient :
          - un titre : les noms des fichiers, la taille, le nombre de copies ;
          - une ligne par copie : son chemin complet, puis à la fin un
            bouton radio qui désigne cette copie pour la suppression.
        """

        emplacements = groupe["emplacements"]
        noms_differents = sorted({os.path.basename(chemin) for chemin in emplacements})

        # Exemple de titre :  « 12.2 Mo  —  3 copies  —  vacances.jpg, vacances2019.jpg »
        morceaux_de_noms = noms_differents[:3]
        if len(noms_differents) > 3:
            morceaux_de_noms.append("...")
        titre = (f"{taille_lisible(groupe['taille'])}  —  "
                 f"{len(emplacements)} copies  —  "
                 f"{', '.join(morceaux_de_noms)}")

        cadre = ttk.LabelFrame(self.cadre_des_blocs, text=titre)
        cadre.pack(side="top", fill="x", padx=10, pady=6)

        # Une variable partagée pour les boutons radio du bloc.
        # Valeur -1 tant que rien n'est coché ; ensuite l'indice de la
        # copie cochée (0 pour la première ligne, 1 pour la deuxième...).
        variable_radio = tk.IntVar(value=-1)

        for indice, chemin in enumerate(emplacements):
            ligne = tk.Frame(cadre)
            ligne.pack(side="top", fill="x", padx=6, pady=1)

            texte_du_chemin = tk.Label(ligne, text=chemin, anchor="w")
            texte_du_chemin.pack(side="left", fill="x", expand=True)

            bouton_radio = ttk.Radiobutton(ligne, variable=variable_radio, value=indice)
            bouton_radio.pack(side="right")

        self.blocs.append({"cadre": cadre,
                           "variable_radio": variable_radio,
                           "emplacements": emplacements,
                           "taille": groupe["taille"],
                           "hash": groupe["hash"],
                           "noms": noms_differents})

    def mettre_a_jour_le_resume(self, nombre_visible):
        total = len(self.blocs)
        texte_filtres = f"{len(self.liste_des_filtres)} filtre(s) actif(s)" if self.liste_des_filtres else "aucun filtre"
        self.texte_de_resume.configure(
            text=f"{nombre_visible} groupe(s) affiché(s) sur {total}  —  {texte_filtres}")

    # =================================================================
    # LES FILTRES D'AFFICHAGE (fenêtre numéro 2)
    # =================================================================

    def ouvrir_la_fenetre_des_filtres(self):
        FenetreFiltres(self)

    def appliquer_les_filtres(self):
        """Montre ou cache les blocs en fonction des filtres actifs.

        - sans filtre : tous les blocs sont affichés ;
        - mode "montrer" : seul un bloc contenant un des textes des
          filtres est affiché ;
        - mode "cacher" : un bloc contenant un texte de filtre est caché.
        Le texte est recherché dans le nom ET l'emplacement des copies,
        sans tenir compte des majuscules/minuscules.
        """

        nombre_visibles = 0
        for bloc in self.blocs:
            if not self.liste_des_filtres:
                visible = True
            else:
                textes_des_copies = (bloc["noms"] + bloc["emplacements"])
                textes_des_copies = " ".join(textes_des_copies).lower()
                correspond_a_un_filtre = any(filtre.lower() in textes_des_copies
                                             for filtre in self.liste_des_filtres)
                if self.mode_des_filtres.get() == "montrer":
                    visible = correspond_a_un_filtre
                else:  # mode "cacher"
                    visible = not correspond_a_un_filtre

            bloc["cadre"].pack_forget()      # on le cache toujours d'abord...
            if visible:
                bloc["cadre"].pack(side="top", fill="x", padx=10, pady=6)   # ...puis on le replace
                nombre_visibles += 1

        self.mettre_a_jour_le_resume(nombre_visibles)

    # =================================================================
    # LE BOUTON « SUPPRIMER » : envoyer vers la corbeille
    # =================================================================

    def supprimer_la_selection(self):
        """Supprime (vers la corbeille) chaque copie désignée par un
        bouton radio, met le rapport à jour et rafraîchit l'écran."""

        # --- 1. On récupère la liste des fichiers cochés ----------------
        copies_choisies = []
        for bloc in self.blocs:
            valeur = bloc["variable_radio"].get()
            if valeur != -1:                     # -1 = rien de coché dans ce bloc
                copies_choisies.append(bloc["emplacements"][valeur])

        if not copies_choisies:
            messagebox.showinfo("Supprimer", "Cochez d'abord un bouton radio "
                                             "dans au moins un bloc.")
            return

        # --- 2. Une dernière confirmation, avec le nombre de fichiers ---
        reponse = messagebox.askyesno(
            "Confirmation",
            f"Mettre {len(copies_choisies)} fichier(s) à la corbeille ?\n\n"
            "Ils pourront être restaurés depuis la corbeille de votre système.")
        if not reponse:
            return

        # --- 3. Envoi vers la corbeille, un par un ----------------------
        fichiers_supprimes = 0
        erreurs = []
        for chemin in copies_choisies:
            try:
                corbeille.envoyer_a_la_corbeille(chemin)
                fichiers_supprimes += 1
                self.retirer_chemin_du_rapport(chemin)
            except Exception as erreur:
                erreurs.append(f"{chemin}\n    {erreur}")

        # --- 4. On enregistre le rapport mis à jour ---------------------
        with open(self.chemin_du_rapport, "w", encoding="utf-8") as fichier:
            json.dump(self.rapport, fichier, ensure_ascii=False, indent=2)

        # --- 5. Message final et rafraîchissement de l'affichage --------
        message = f"{fichiers_supprimes} fichier(s) mis à la corbeille."
        if erreurs:
            message += (f"\n\n{len(erreurs)} fichier(s) n'ont PAS pu être mis "
                        f"à la corbeille :\n\n" + "\n\n".join(erreurs))
        messagebox.showinfo("Résultat", message)

        # On reconstruit tout l'affichage à partir du rapport mis à jour
        # (les blocs devenus inutiles disparaissent tout seuls).
        self.charger_et_afficher_le_rapport()

    def retirer_chemin_du_rapport(self, chemin_supprime):
        """Enlève un fichier supprimé de toutes les listes du rapport,
        puis retire les groupes qui ne sont plus de vrais doublons
        (un groupe doit garder au moins 2 emplacements)."""

        for groupe in self.rapport.get("doublons_entre_les_deux_disques", []):
            for cle in ("emplacements_sur_disque1", "emplacements_sur_disque2"):
                liste = groupe.get(cle, [])
                if chemin_supprime in liste:
                    liste.remove(chemin_supprime)
        groupes_deux_disques = self.rapport.get("doublons_entre_les_deux_disques", [])
        self.rapport["doublons_entre_les_deux_disques"] = [
            groupe for groupe in groupes_deux_disques
            if len(groupe.get("emplacements_sur_disque1", []))
               + len(groupe.get("emplacements_sur_disque2", [])) >= 2]

        for cle in ("copies_internes_au_disque1", "copies_internes_au_disque2"):
            for groupe in self.rapport.get(cle, []):
                if chemin_supprime in groupe.get("emplacements", []):
                    groupe["emplacements"].remove(chemin_supprime)
            if cle in self.rapport:
                self.rapport[cle] = [groupe for groupe in self.rapport[cle]
                                     if len(groupe.get("emplacements", [])) >= 2]


class FenetreFiltres(tk.Toplevel):
    """La fenêtre d'ajout et de suppression des filtres d'affichage."""

    def __init__(self, application):
        super().__init__(application)
        self.application = application
        self.title("Filtres d'affichage")
        self.geometry("520x360")

        # --- Explication en français courant -------------------------
        tk.Label(self, justify="left", wraplength=490, anchor="w", text=(
            "Un filtre est un morceau de texte. Il est comparé au nom et à "
            "l'emplacement des copies, sans tenir compte des majuscules "
            "ou minuscules.\n\n"
            "Sans filtre, tous les blocs de doublons sont affichés.")).pack(
            side="top", fill="x", padx=10, pady=8)

        # --- Le mode : montrer seulement, ou cacher -------------------
        cadre_du_mode = ttk.LabelFrame(self, text="Mode des filtres")
        cadre_du_mode.pack(side="top", fill="x", padx=10, pady=4)
        ttk.Radiobutton(cadre_du_mode, value="montrer",
                        variable=self.application.mode_des_filtres,
                        text="Montrer SEULEMENT les blocs contenant un filtre",
                        command=self.application.appliquer_les_filtres).pack(
            side="top", anchor="w", padx=6, pady=2)
        ttk.Radiobutton(cadre_du_mode, value="cacher",
                        variable=self.application.mode_des_filtres,
                        text="CACHER les blocs contenant un filtre",
                        command=self.application.appliquer_les_filtres).pack(
            side="top", anchor="w", padx=6, pady=2)

        # --- Ajouter un filtre ----------------------------------------
        cadre_d_ajout = ttk.LabelFrame(self, text="Ajouter un filtre")
        cadre_d_ajout.pack(side="top", fill="x", padx=10, pady=4)
        self.champ_de_filtre = ttk.Entry(cadre_d_ajout)
        self.champ_de_filtre.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        self.champ_de_filtre.bind("<Return>", self.ajouter_le_filtre)   # Entrée = ajouter
        ttk.Button(cadre_d_ajout, text="Ajouter",
                   command=self.ajouter_le_filtre).pack(side="left", padx=(0, 6))

        # --- Liste des filtres actifs + bouton de suppression ---------
        cadre_de_la_liste = ttk.LabelFrame(self, text="Filtres actifs")
        cadre_de_la_liste.pack(side="top", fill="both", expand=True, padx=10, pady=4)
        self.liste_affichee = tk.Listbox(cadre_de_la_liste)
        self.liste_affichee.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Button(cadre_de_la_liste, text="Supprimer le filtre sélectionné",
                   command=self.supprimer_le_filtre).pack(side="bottom", pady=6)

        self.rafraichir_la_liste()

    def ajouter_le_filtre(self, evenement=None):
        texte = self.champ_de_filtre.get().strip()
        if texte and texte not in self.application.liste_des_filtres:
            self.application.liste_des_filtres.append(texte)
        self.champ_de_filtre.delete(0, "end")
        self.rafraichir_la_liste()
        self.application.appliquer_les_filtres()

    def supprimer_le_filtre(self):
        selection = self.liste_affichee.curselection()
        if selection:
            del self.application.liste_des_filtres[selection[0]]
            self.rafraichir_la_liste()
            self.application.appliquer_les_filtres()

    def rafraichir_la_liste(self):
        self.liste_affichee.delete(0, "end")
        for filtre in self.application.liste_des_filtres:
            self.liste_affichee.insert("end", filtre)


# ---------------------------------------------------------------------
# Démarrage du programme : on crée la fenêtre principale et on lance
# « la boucle » qui écoute la souris et le clavier.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    gestionnaire = Application()
    gestionnaire.mainloop()
