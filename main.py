import json 

def copy_dict(name):
    return {
    "GigabitEthernet1/0" : [],
    "GigabitEthernet2/0" : [],
    "IGP" : [],
    "AS" : [],
    "neighbor" : [],
    "network" : []
               }
    
def addressing(network, router): #network est une chaine de caractères et router est un int
    if network not in networks.keys():   #on check si il y a déjà une entrée pour ce sous réseau et si non on peut prendre une addresse qu'on veut pour le routeur dans le sous réseau
        address = network.split("/")[0]+ "1/" + network.split("/")[1]
        networks[network]={}
        
    else: #le sous-réseau est déjà une entrée dans le dico networks donc il y a déjà au moins une addresse prise dans ce sous réseau
        nombre_elem= len(networks[network].keys()) #on compte le nombre d'addresses déjà prises
        if nombre_elem>65534: #on vérifie qu'il n'y a pas plus de 65534 addresses dans notre sous-réseau 
            return "err"
        else:
            print(nombre_elem)
            address = network.split("/")[0]+ f"{hex(nombre_elem + 1).split('x')[1]}" + "/" + network.split("/")[1]

    networks[network][router]=address
    return address 

with open('config_2.json', 'r', encoding='utf-8') as file:
    donnees_lues = json.load(file)
    
with open('template.txt', 'r', encoding='utf-8') as file:
    template = file.read()
    file.close()
    
AS_dic = list(donnees_lues.values())[0]
Inter_AS = list(donnees_lues.values())[1]

write = {}
networks = {}
dict_info = {}

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
                    
            info["network"].append(network_name)
            
        info["IGP"] = AS["IGP"]
        info["AS"] = [AS["n°"], Router]
        dict_info[name] = info


for network_name, network_dic in Inter_AS.items() :

    for Router, AS in network_dic.items() :
        address = addressing(network_name, Router)
        
        if address != "err" :
            dict_info[Router][network_dic[Router][0]].append(address)
            
        else :
            print(f"Too much address in {network_name}")
            
        dict_info[Router]["network"].append(network_name)

for Router in dict_info :
    
    for Router_peer in AS_dic[f"As_{dict_info[Router]['AS'][0]}"]["Routers"] :
        
        if f"{Router_peer}" != Router :
            dict_info[Router]["neighbor"].append([dict_info[f"{Router_peer}"]["GigabitEthernet1/0"][0], dict_info[Router]["AS"][0]])
        
    for network in Inter_AS.values() :
        
        if f"{Router}" in network.keys() :
            
            for Router_peer in network.keys() :
                
                if Router_peer != Router :
                    dict_info[Router]["neighbor"].append([dict_info[Router_peer]["GigabitEthernet1/0"][0], network[Router_peer][1]])

        
        

def remplace(temp, router):

    IP_addressGe1_0= dict_info[f'{router}']['GigabitEthernet1/0'][0]
    IP_addressGe2_0= dict_info[f'{router}']['GigabitEthernet2/0'][0]
    numAS = dict_info[f'{router}']['AS'][0]
    
    
    config = template.split("[GigabitEthernet1/0]")[0]+ f"ipv6 address {IP_addressGe1_0}\n" +" ipv6 enable\n" +" ipv6 rip 2 enable\n" + template.split("[GigabitEthernet1/0]")[1]
    
    config = config.split("[GigabitEthernet2/0]")[0]+ f"ipv6 address {IP_addressGe2_0}\n" +" ipv6 enable\n" +" ipv6 rip 2 enable\n" + config.split("[GigabitEthernet2/0]")[1]
    
    config = config.split("[AS]")[0]+ f"{numAS}\n" +f" bgp router-id {router}.{router}.{router}.{router}" + config.split("[AS]")[1]
    
    config = config.split("[neighbor]")[0] + f"neighbor {dict_info[f'{router}']['neighbor'][0][0]} remote-as {dict_info[f'{router}']['neighbor'][0][1]}\n" + f" neighbor {dict_info[f'{router}']['neighbor'][1][0]} remote-as {dict_info[f'{router}']['neighbor'][1][1]}\n" + config.split("[neighbor]")[1]
    print(config)
    return(config)
    #config = config.split("[network]")[0] + 

write["3"] = remplace(template, 4)

for key, val in write.items() :
    f = open(f"i{key}_startup-config.cfg", "w")
    f.write(val)
    f.close()
