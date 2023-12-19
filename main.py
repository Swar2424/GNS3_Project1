import json 

with open('config.json', 'r', encoding='utf-8') as fichier:
    donnees_lues = json.load(fichier)
    
print("AAAA")
a = 0





for AS in donnees_lues :
    print(AS)

f = open("i1_startup-config.cfg", "w")
f.write("!\n! bgp area 11")
f.close()
