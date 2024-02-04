Le programme s'exécute avec TELNET. Pour que cela fonctionne :

- Avoir la config GNS3 correspondant à l'intent file utilisé (config_X.json)
- Vérifier les connections entre routeurs et les interfaces, ainsi que les numéros de ports TELNET
- Lancer toutes les consoles et appuyer sur ENTER pour que les consoles soient prêtes à recevoir des commandes
- Exécuter le programme main_class.py (avec en paramètre à la ligne 497 le nom de l'intent file utilisé)



Pour tester le programme, nous conseillons les configs 3 et 4, ou la 5 (pour les communautés)

Une copie de la config écrite dans les routeurs est créée dans le dossier ./cfg_files.

Attention : il est possible qu'il y ait de légères différences entre la config cfg dans le dossier
et la config obtenue avec <show running config>