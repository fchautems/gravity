# Installation de Gravity sous Windows

Ce guide couvre le jalon 2. Il valide l'installation et le calcul compile, mais
la galaxie 3D apparaitra au jalon 3.

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
4. Une petite fenetre Windows confirme que Python, NumPy et la compilation Numba
   fonctionnent. C'est le resultat visuel attendu pour le jalon 2.

L'installateur cree `.venv` dans le dossier du projet. Il ne modifie pas les
autres environnements Python de l'ordinateur.

## Lancer les controles

Double-cliquez sur `TESTER_GRAVITY.bat`. Il execute successivement :

- la compilation syntaxique de tous les modules;
- l'analyse Ruff;
- le controle de types Mypy;
- les tests Pytest et leur couverture;
- la verification de coherence des paquets installes.

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
cause. Si tous les controles reussissent, le test specifique du jalon 3 sera la
creation de la vraie fenetre OpenGL sur le PC cible.

