import json 

def copy_dict():
    return {
    "Loopback0" : [],
    "FastEthernet0/0" : [],
    "GigabitEthernet1/0" : [],
    "GigabitEthernet2/0" : [],
    "IGP" : [],
    "AS" : [],
    "neighbor" : [],
    "network" : [],
    "eBGP_interface" : []
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
            address = network.split("/")[0]+ f"{hex(nombre_elem + 1).split('x')[1]}" + "/" + network.split("/")[1]

    networks[network][router]=address
    return address 


def remplace(temp, router):

    #Initialisation des variables
    IP_addressGe1_0= dict_info[f'{router}']['GigabitEthernet1/0']
    IP_addressGe2_0= dict_info[f'{router}']['GigabitEthernet2/0']
    IP_addressLoo_0= dict_info[f'{router}']['Loopback0']
    IP_addressFa0_0= dict_info[f'{router}']['FastEthernet0/0']
    numAS = dict_info[f'{router}']['AS'][0]
    config = temp
    
    #Sélection de l'IGP
    if dict_info[f'{router}']['IGP'] == "RIP" :
        process = "rip 200"
        config = config.split("[IGP]")[0] + process + "\n redistribute connected" + config.split("[IGP]")[1]
    else :
        process = f"ospf 100 area {numAS}"
        char_temp = ""
        if dict_info[f'{router}']['eBGP_interface'] != [] :
            char_temp = f"\n passive-interface {dict_info[f'{router}']['eBGP_interface']}"
        config = config.split("[IGP]")[0] + process + f"\n router-id {router}.{router}.{router}.{router}" + char_temp + config.split("[IGP]")[1]
    
    #Attributions des adresses sur les interfaces
    if IP_addressGe1_0 != [] :
        config = config.split("[GigabitEthernet1/0]")[0] + f"ipv6 address {IP_addressGe1_0}\n" + " ipv6 enable\n" + f" ipv6 {process} enable" + config.split("[GigabitEthernet1/0]")[1]
    else :
        config = config.split("[GigabitEthernet1/0]")[0] + "shutdown" + config.split("[GigabitEthernet1/0]")[1]
        
    if IP_addressGe2_0 != [] :    
        config = config.split("[GigabitEthernet2/0]")[0] + f"ipv6 address {IP_addressGe2_0}\n" +" ipv6 enable\n" + f" ipv6 {process} enable" + config.split("[GigabitEthernet2/0]")[1]
    else :
        config = config.split("[GigabitEthernet2/0]")[0] + "shutdown" + config.split("[GigabitEthernet2/0]")[1]
    
    if IP_addressFa0_0 != [] :
        config = config.split("[FastEthernet0/0]")[0] + f"ipv6 address {IP_addressFa0_0}\n" +" ipv6 enable\n" + f" ipv6 {process} enable" + config.split("[FastEthernet0/0]")[1]
    else :
        config = config.split("[FastEthernet0/0]")[0] + "shutdown" + config.split("[FastEthernet0/0]")[1]
        
    if IP_addressLoo_0 != [] :
        config = config.split("[Loopback0]")[0] + f"ipv6 address {IP_addressLoo_0}\n" +" ipv6 enable\n" + f" ipv6 {process} enable" + config.split("[Loopback0]")[1]
    else :  
        config = config.split("[Loopback0]")[0] + "shutdown" + config.split("[Loopback0]")[1]
        
    config = config.split("[AS]")[0] + f"{numAS}\n" + f" bgp router-id {router}.{router}.{router}.{router}" + config.split("[AS]")[1]
    
    
    #Attribution des neighbors
    char = ""
    char_activate = ""
    for neighbor_list in dict_info[f'{router}']['neighbor'] :
        neighbor_tronque = neighbor_list[0].split("/")[0]
        print(f"le tronq donne {neighbor_tronque}")
        char += f"neighbor {neighbor_tronque} remote-as {neighbor_list[1]}\n "
        char_activate += f"  neighbor {neighbor_tronque} activate\n"
        if neighbor_list[0][:9] == "10:10:10:" :
            char += f"neighbor {neighbor_tronque} update-source Loopback0\n "
    char = char[:len(char)-2]
    char_activate = char_activate
    
    config = config.split("[neighbor]")[0] + char + config.split("[neighbor]")[1]
    
    #Attribution des networks
    char_net = ""
    for network in dict_info[f'{router}']['network']:
        char_net += f"  network {network}\n"
        
    char_net = char_net[2:]
    config = config.split("[network]")[0] + char_net + char_activate + config.split("[network]")[1]

        
    print(config)
    return(config)







with open('config_2.json', 'r', encoding='utf-8') as file:
    donnees_lues = json.load(file)
    
with open('template_loop.txt', 'r', encoding='utf-8') as file:
    template = file.read()
    file.close()
    
AS_dic = list(donnees_lues.values())[0]
Inter_AS = list(donnees_lues.values())[1]

networks = {}
dict_info = {}


#Création des adresses iBGP  
for AS in AS_dic.values() :
    
    for Router in AS["Routers"] :          
        name = f"{Router}"
        info = copy_dict()
        
        for network_name, network_dic in AS["Networks"].items() : 
            
            if name in network_dic.keys() :
                address = addressing(network_name, Router)
                
                if address != "err" :
                    info[network_dic[name]] = (address)
                    
                else :
                    print(f"Too much address in {network_name}")
                    
            info["network"].append(network_name)
            
        info["IGP"] = AS["IGP"]
        info["AS"] = [AS["n°"], Router]
        address = addressing(f"10:10:10:{hex(Router).split('x')[1]}::/64", Router)
        if address != "err" :
            info["Loopback0"] = address
            
        dict_info[name] = info


#Création des adresses eBGP  
for network_name, network_dic in Inter_AS.items() :

    for Router, AS in network_dic.items() :
        address = addressing(network_name, Router)
        
        if address != "err" :
            dict_info[Router][network_dic[Router][0]] = address
            dict_info[Router]["eBGP_interface"] = network_dic[Router][0]
            
        else :
            print(f"Too much address in {network_name}")
            
        dict_info[Router]["network"].append(network_name)

#Récupération des neighbors
for Router in dict_info.keys() :
    
    for Router_peer in AS_dic[f"As_{dict_info[Router]['AS'][0]}"]["Routers"] :
        
        if f"{Router_peer}" != Router :
            dict_info[Router]["neighbor"].append([dict_info[f"{Router_peer}"]["Loopback0"], dict_info[Router]["AS"][0]])
        
    for network_name, network_dic in Inter_AS.items() :
        
        if f"{Router}" in network_dic.keys() :
            
            for Router_peer in network_dic.keys() :
                
                if Router_peer != Router :
                    dict_info[Router]["neighbor"].append([dict_info[Router_peer][dict_info[Router]["eBGP_interface"]], network_dic[Router_peer][1]])

remplace(template, 4)


#Écriture des configs
for Router in dict_info.keys() :
    f = open(f"i{Router}_startup-config.cfg", "w")
    f.write(remplace(template, int(Router)))
    f.close()

