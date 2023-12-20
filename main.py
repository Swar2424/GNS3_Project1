import json 

with open('config.json', 'r', encoding='utf-8') as file:
    donnees_lues = json.load(file)
    
with open('template.txt', 'r', encoding='utf-8') as file:
    template = file.read()
    file.close()
    
AS_dic = list(donnees_lues.values())[0]

write = {}
networks = {}


def ASout(address):
    if address != "NULL" :
        return (address.split(":")[1] == "2")
    else :
        return False
    
for AS in AS_dic.values() :
    for Router in AS["Routeurs"].values() :
        name = f"{Router}"
        temp = template
        if ASout(Router['GigabitEthernet 2/0']) :
            a=0
        write["i" + name] = temp
            
        
        
for key, val in write.items() :
    f = open(f"{key}_startup-config.cfg", "w")
    f.write(val)
    f.close()
