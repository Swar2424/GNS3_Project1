import json 

with open('config.json', 'r', encoding='utf-8') as fichier:
    donnees_lues = json.load(fichier)
    
dico = list(donnees_lues.values())[0]
for AS in dico.values() :
    for AS1 in AS.values() :
        print(AS1)

f = open("i1_startup-config.cfg", "w")
f.write("!\n! bgp area 11")
f.close()
