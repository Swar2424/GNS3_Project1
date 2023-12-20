import json 

def ASout(address):
    if address != "NULL" :
        return (address.split(":")[1] == "2")
    else :
        return False
    
def addressing(network, router) :
    return network.split("/")[0] + f"{router}" + "/" + network.split("/")[1]

def copy_dict(name):
    return {
    "GigabitEthernet1/0" : [],
    "GigabitEthernet2/0" : [],
    "IGP" : [],
    "AS" : [],
    "neighbor" : [],
    "network" : []
               }
with open('config_2.json', 'r', encoding='utf-8') as file:
    donnees_lues = json.load(file)
    
with open('template.txt', 'r', encoding='utf-8') as file:
    template = file.read()
    file.close()
    
AS_dic = list(donnees_lues.values())[0]

write = {}
networks = {}
dict_info = {}


for AS in AS_dic.values() :
    for Router in AS["Routers"] :        
        name = f"{Router}"
        temp = template
        info = copy_dict(name)
        for network_name, network_dic in AS["Networks"].items() :
            if name in network_dic.keys() :
                address = addressing(network_name, Router)
                if address != "err" :
                    info[network_dic[name]].append(address)
                else :
                    print(f"Too much address in {network_name}")
            info["network"].append([network_name, AS["n°"]])
        print(name, "\n", info)
        dict_info[name] = info

        write["i" + name] = temp
            
        
        
for key, val in write.items() :
    f = open(f"{key}_startup-config.cfg", "w")
    f.write(val)
    f.close()

def addressing(network, router): #network est une chaine de caractères et router est un int
    if network not in networks.keys():   #on check si il y a déjà une entrée pour ce sous réseau et si non on peut prendre une addresse qu'on veut pour le routeur dans le sous réseau
        address = network.split("/")[0]+ "1/" + network.split("/")[1]
        networks[network]={}
        
    else: #le sous-réseau est déjà une entrée dans le dico networks donc il y a déjà au moins une addresse prise dans ce sous réseau
        nombre_elem= len(networks[network].keys()) #on compte le nombre d'addresses déjà prises
        if nombre_elem>255: #on vérifie qu'il n'y a pas plus de 255 addresses dans notre sous-réseau 
            return "err"
        else:
            address = network.split("/")[0]+ f"{nombre_elem+1}" + "/" + network.split("/")[1]

    networks[network][router]=address
    return address 

#TESTS DE LA FONCTION ADDRESSING
#print(addressing("2001:1:1:1::/64",1))
#print(addressing("2001:1:1:1::/64",2))

