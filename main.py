import json 

with open('config.json', 'r', encoding='utf-8') as fichier:
    donnees_lues = json.load(fichier)
    
AS_dic = list(donnees_lues.values())[0]


def ASout(address):
    if address != "NULL" :
        return (address.split(":")[1] == "2")
    else :
        return False
    
for AS in AS_dic.values() :
    for Router in AS["Routeurs"].values() :
        if ASout(Router['GigabitEthernet 2/0']) :
            a=0
        
        

f = open("i1_startup-config.cfg", "w")
f.write("!\n! bgp area 11")
f.close()
