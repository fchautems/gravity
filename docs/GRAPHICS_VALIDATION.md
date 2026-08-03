# Validation du rendu graphique — jalon 3

Ce controle prend environ deux minutes sur le PC Windows cible. Il valide ce
qu'un test sans ecran ne peut pas prouver : le pilote NVIDIA, la fenetre native,
la mise a l'echelle Windows et le ressenti de la camera.

## Avant de commencer

1. Mettez le depot a jour ou telechargez le dernier ZIP puis extrayez-le.
2. Double-cliquez sur `INSTALLER.bat`, meme si le jalon 2 etait deja installe.
3. Attendez `Installation terminee avec succes`.

## Controle visuel

1. Double-cliquez sur `LANCER_GRAVITY.bat`.
2. Verifiez qu'une galaxie sombre et coloree apparait avec `10'000 particules`
   indique dans le panneau.
3. Maintenez le clic gauche et deplacez la souris : la camera doit tourner sans
   saut.
4. Maintenez le clic droit ou la molette et deplacez la souris : le centre de la
   vue doit se deplacer.
5. Tournez la roue : le zoom doit rester borne et ne jamais traverser le centre.
6. Manipulez les deux curseurs du panneau : la camera ne doit pas bouger.
7. Testez `Pause`, `Recommencer` et `Recentrer la vue`.
8. Masquez puis rouvrez les reglages.
9. Redimensionnez, maximisez puis restaurez la fenetre. L'image doit remplir la
   surface sans deformation ni plantage.
10. Fermez la fenetre normalement.

## Resultat attendu

- le compteur reste proche de 60 FPS lorsque la synchronisation verticale est
  active et la scene en pause;
- le panneau et les textes restent nets avec la mise a l'echelle Windows;
- les points sont ronds et lumineux, sans grands carres;
- aucune console ne reste ouverte;
- la fermeture est immediate.

Le chiffre FPS depend de l'ecran et peut etre bloque a sa frequence de
rafraichissement. Ce jalon verifie le rendu; les performances de gravitation ne
seront mesurables qu'apres Barnes-Hut.

## En cas d'echec

Lancez `TESTER_GRAVITY.bat`, puis transmettez :

- l'etape exacte qui echoue;
- une capture d'ecran si la fenetre est visible;
- le fichier `%LOCALAPPDATA%\Gravity\logs\gravity.log`.

Le journal contient le GPU, le fournisseur, la version OpenGL et l'erreur GLFW,
sans telemetrie ni collecte de documents personnels.
