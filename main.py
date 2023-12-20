import json 

def ASout(address):
    if address != "NULL" :
        return (address.split(":")[1] == "2")
    else :
        return False
    

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

for AS in AS_dic.values() :
    for Router in AS["Routers"] :        
        name = f"{Router}"
        info = copy_dict(name)
        for network_name, network_dic in AS["Networks"].items() :
            if name in network_dic.keys() :
                address = addressing(network_name, Router)
                if address != "err" :
                    info[network_dic[name]].append(address)
                else :
                    print(f"Too much address in {network_name}")
            info["network"].append([network_name, AS["n°"]])
        #print(name, "\n", info)
        dict_info[name] = info

            
        
        
for key, val in write.items() :
    f = open(f"{key}_startup-config.cfg", "w")
    f.write(val)
    f.close()



def remplace(temp, router):
    dict_info[f"{router}"]={'GigabitEthernet1/0': ['2001:1:1:1::1/64'], 'GigabitEthernet2/0': ['2001:1:1:2::1/64'], 'IGP': ["RIP"], 'AS': ["111"], 'neighbor': [["2001:1:1:1::2/64",111],["2001:1:1:2::2/64",112]], 'network': ['2001:1:1:1::/64','2001:1:1:2::/64']}
    print(dict_info[f"{router}"])

    IP_addressGe1_0= dict_info[f'{router}']['GigabitEthernet1/0'][0]
    IP_addressGe2_0= dict_info[f'{router}']['GigabitEthernet2/0'][0]
    numAS = dict_info[f'{router}']['AS'][0]
    
    
    config = template.split("[GigabitEthernet1/0]")[0]+ f"ipv6 address {IP_addressGe1_0}\n" +" ipv6 enable\n" +" ipv6 rip 2 enable\n" + template.split("[GigabitEthernet1/0]")[1]
    
    config = config.split("[GigabitEthernet2/0]")[0]+ f"ipv6 address {IP_addressGe2_0}\n" +" ipv6 enable\n" +" ipv6 rip 2 enable\n" + config.split("[GigabitEthernet2/0]")[1]
    
    config = config.split("[AS]")[0]+ f"{numAS}\n" +f" bgp router-id {router}.{router}.{router}.{router}" + config.split("[AS]")[1]
    
    config = config.split("[neighbor]")[0] + f"neighbor {dict_info[f'{router}']['neighbor'][0][0]} remote-as {dict_info[f'{router}']['neighbor'][0][1]}\n" + f" neighbor {dict_info[f'{router}']['neighbor'][1][0]} remote-as {dict_info[f'{router}']['neighbor'][1][1]}\n" + config.split("[neighbor]")[1]
    print(config)
    #config = config.split("[network]")[0] + 


remplace(template, 1)