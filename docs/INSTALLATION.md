# Installation et jalon physique 5 de Gravity sous Windows

Ce guide couvre le jalon 5. Il installe le calcul compile et la pile graphique,
valide le moteur gravitationnel exact ainsi que le generateur physique de
galaxie, puis ouvre le premier nuage galactique 3D. Le moteur n'est pas encore
relie au rendu : l'image reste donc celle du jalon 3 jusqu'a l'etape 7.

## Prerequis

- Windows 10 ou Windows 11 en 64 bits;
- Python 3.12 en 64 bits installe depuis
  [python.org](https://www.python.org/downloads/);
- une connexion Internet pendant l'installation initiale.

Si le depot a ete telecharge sous forme de fichier ZIP, il faut d'abord extraire
son contenu. Ne lancez pas les fichiers `.bat` directement depuis la fenetre du
ZIP.

## Installation et lancement

1. Double-cliquez sur `INSTALLER.bat`.
2. Attendez le message `Installation terminee avec succes` puis appuyez sur une
   touche pour fermer la fenetre.
3. Double-cliquez sur `LANCER_GRAVITY.bat`.
4. La fenetre `Gravity - Galaxie 3D` doit s'ouvrir avec 10 000 particules et un
   panneau de reglages a droite.

Apres une mise a jour d'un jalon precedent, relancez `INSTALLER.bat` une fois.
Il reutilise l'environnement existant et applique le verrouillage courant.

L'installateur cree `.venv` dans le dossier du projet. Il ne modifie pas les
autres environnements Python de l'ordinateur.

## Lancer les controles

Double-cliquez sur `TESTER_GRAVITY.bat`. Il execute successivement :

- la compilation syntaxique de tous les modules;
- l'analyse Ruff;
- le controle de types Mypy;
- les tests Pytest et leur couverture;
- la verification de coherence des paquets installes.

Les tests sans materiel verifient aussi la camera, les gestes de souris, la
generation des 10 000 points, le contrat d'un seul appel GPU, les shaders, les
statistiques d'image et l'ordre de fermeture des ressources. Ils valident en
plus les forces exactes, les invariants et la stabilite d'une orbite binaire sur
100 periodes. Le jalon 5 ajoute la reproductibilite et les distributions de la
galaxie, le halo analytique, la coherence des vitesses et un court essai
dynamique exact de 240 particules.

La fenetre reste ouverte a la fin pour permettre de lire le resultat.

## Journaux et donnees locales

Les journaux se trouvent dans :

```text
%LOCALAPPDATA%\Gravity\logs
```

Le cache Numba est place dans `%LOCALAPPDATA%\Gravity\cache\numba`. Aucune
telemetrie n'est envoyee.

## En cas de probleme

### Python 3.12 est introuvable

Reinstallez Python 3.12 en 64 bits depuis python.org et activez l'option
`Add Python to PATH`. Relancez ensuite `INSTALLER.bat`.

### Une ancienne installation locale est incompatible

L'installateur ne la supprime pas. Il la renomme en
`.venv-incompatible-AAAAAMMJJ-HHMMSS`, puis cree un environnement propre.

### L'installation d'un paquet echoue

Verifiez la connexion Internet et consultez le chemin du journal affiche par
l'installateur. Relancer `INSTALLER.bat` est sans danger : un environnement
Python 3.12 valide est reutilise.

### Le lancement ne montre rien

Executez `TESTER_GRAVITY.bat`. Si un controle echoue, le journal indique la
cause. Si tous les controles reussissent, mettez a jour le pilote NVIDIA puis
relancez Gravity. Le journal contient la version OpenGL et le nom du GPU lorsque
la creation de la fenetre a reussi.

### La fenetre s'ouvre, mais l'image est vide ou lente

- mettez le pilote NVIDIA a jour depuis le site NVIDIA;
- verifiez que Gravity utilise bien la GTX 1070 dans les parametres graphiques
  de Windows;
- essayez de reduire `Taille des etoiles` pour distinguer un probleme de rendu
  d'un simple effet trop lumineux;
- consultez la [checklist graphique](GRAPHICS_VALIDATION.md) et transmettez le
  journal si le probleme persiste.
