import json 


class Config() :
    
    def __init__(self, file1, file2) :
        with open(file1, 'r', encoding='utf-8') as file:
            donnees_lues = json.load(file)
            
        with open(file2, 'r', encoding='utf-8') as file:
            self.template = file.read()
            file.close()
        
        self.AS_dic = list(donnees_lues.values())[0]
        self.Inter_AS = list(donnees_lues.values())[1]
        self.path = list(donnees_lues.values())[2]
        self.networks = {}
        self.dict_info = {}
        
        
        
    def build_data(self) :    
        #Création des adresses iBGP  
        for AS in self.AS_dic.values() :

            

            for Router in AS["Routers"] :          
                name = f"{Router}"
                info = self.copy_dict()
                
                for network_name, network_dic in AS["Networks"].items() : 
                    
                    if name in network_dic.keys() :
                        address = self.addressing(network_name, Router)
                        
                        if address != "err" :
                            info[network_dic[name]] = (address)
                            
                        else :
                            print(f"Too much address in {network_name}") 


            
            
                    
                info["IGP"] = AS["IGP"]
                info["AS"] = [AS["n°"], Router]
                address = self.addressing(f"10:10:10:{hex(Router).split('x')[1]}::/64", Router)
                if address != "err" :
                    info["Loopback0"] = address
                if Router == AS["advertise_net"][0]:    
                    info["network"].append(AS["advertise_net"][1]) 
                    print(Router)                   
                self.dict_info[name] = info


            


        #Création des adresses eBGP  
        for network_name, network_dic in self.Inter_AS.items() :

            for Router, AS in network_dic.items() :
                address = self.addressing(network_name, Router)
                
                if address != "err" :
                    self.dict_info[Router][network_dic[Router][0]] = address
                    self.dict_info[Router]["eBGP_interface"] = network_dic[Router][0]
                    
                else :
                    print(f"Too much address in {network_name}")
                    
                self.dict_info[Router]["network"].append(network_name)

        #Récupération des neighbors
        for Router in self.dict_info.keys() :
            
            for Router_peer in self.AS_dic[f"As_{self.dict_info[Router]['AS'][0]}"]["Routers"] :
                
                if f"{Router_peer}" != Router :
                    self.dict_info[Router]["neighbor"].append([self.dict_info[f"{Router_peer}"]["Loopback0"], self.dict_info[Router]["AS"][0]])
                
            for network_name, network_dic in self.Inter_AS.items() :
                
                if f"{Router}" in network_dic.keys() :
                    
                    for Router_peer in network_dic.keys() :
                        
                        if Router_peer != Router :
                            self.dict_info[Router]["neighbor"].append([self.dict_info[Router_peer][self.dict_info[Router_peer]["eBGP_interface"]], network_dic[Router_peer][1]])
                        
               
                            
    def write_config(self, temp, router):

        #Initialisation des variables
        IP_addressGe1_0= self.dict_info[f'{router}']['GigabitEthernet1/0']
        IP_addressGe2_0= self.dict_info[f'{router}']['GigabitEthernet2/0']
        IP_addressLoo_0= self.dict_info[f'{router}']['Loopback0']
        IP_addressFa0_0= self.dict_info[f'{router}']['FastEthernet0/0']
        numAS = self.dict_info[f'{router}']['AS'][0]
        config = temp
        
        #Sélection de l'IGP
        if self.dict_info[f'{router}']['IGP'] == "RIP" :
            process = "rip 200 enable"
            config = config.split("[IGP]")[0] + "rip 200" + "\n redistribute connected" + config.split("[IGP]")[1]
        else :
            process = f"ospf 100 area 0"
            char_temp = ""
            if self.dict_info[f'{router}']['eBGP_interface'] != [] :
                char_temp = f"\n passive-interface {self.dict_info[f'{router}']['eBGP_interface']}"
            config = config.split("[IGP]")[0] + "ospf 100" + f"\n router-id {router}.{router}.{router}.{router}" + char_temp + config.split("[IGP]")[1]
        
        #Attributions des adresses sur les interfaces
        if IP_addressGe1_0 != [] :
            config = config.split("[GigabitEthernet1/0]")[0] + f"ipv6 address {IP_addressGe1_0}\n" + " ipv6 enable\n" + f" ipv6 {process}" + config.split("[GigabitEthernet1/0]")[1]
        else :
            config = config.split("[GigabitEthernet1/0]")[0] + "shutdown" + config.split("[GigabitEthernet1/0]")[1]
            
        if IP_addressGe2_0 != [] :    
            config = config.split("[GigabitEthernet2/0]")[0] + f"ipv6 address {IP_addressGe2_0}\n" +" ipv6 enable\n" + f" ipv6 {process}" + config.split("[GigabitEthernet2/0]")[1]
        else :
            config = config.split("[GigabitEthernet2/0]")[0] + "shutdown" + config.split("[GigabitEthernet2/0]")[1]
        
        if IP_addressFa0_0 != [] :
            config = config.split("[FastEthernet0/0]")[0] + f"ipv6 address {IP_addressFa0_0}\n" +" ipv6 enable\n" + f" ipv6 {process}" + config.split("[FastEthernet0/0]")[1]
        else :
            config = config.split("[FastEthernet0/0]")[0] + "shutdown" + config.split("[FastEthernet0/0]")[1]
            
        if IP_addressLoo_0 != [] :
            config = config.split("[Loopback0]")[0] + f"ipv6 address {IP_addressLoo_0}\n" +" ipv6 enable\n" + f" ipv6 {process}" + config.split("[Loopback0]")[1]
        else :  
            config = config.split("[Loopback0]")[0] + "shutdown" + config.split("[Loopback0]")[1]
            
        config = config.split("[AS]")[0] + f"{numAS}\n" + f" bgp router-id {router}.{router}.{router}.{router}" + config.split("[AS]")[1]
        
        
        #Attribution des neighbors
        char = ""
        char_activate = ""
        for neighbor_list in self.dict_info[f'{router}']['neighbor'] :
            neighbor_tronque = neighbor_list[0].split("/")[0]
            char += f"neighbor {neighbor_tronque} remote-as {neighbor_list[1]}\n "
            char_activate += f"  neighbor {neighbor_tronque} activate\n"
            if neighbor_list[0][:9] == "10:10:10:" :
                char += f"neighbor {neighbor_tronque} update-source Loopback0\n "
        char = char[:len(char)-2]
        char_activate = char_activate[:len(char_activate)-1]
        
        config = config.split("[neighbor]")[0] + char + config.split("[neighbor]")[1]
        
        #Attribution des networks
        char_net = ""
        
        if self.dict_info[f'{router}']['network'] != [] :
            print(self.dict_info[f'{router}']['network'])
            for network in self.dict_info[f'{router}']['network']:
                char_net += f"  network {network}\n"
       
        #for network in self.dict_info[f'{router}']['network']:
        #    char_net += f"  network {network}\n"
            
            char_net = char_net[2:]
            config = config.split("[network]")[0] + char_net + char_activate + config.split("[network]")[1]

        else:

            config = config.split("  [network]")[0]+ char_activate +config.split("  [network]")[1]
            
        #sprint(config)
        return(config)
    
    
    
    def addressing(self, network, router): #network est une chaine de caractères et router est un int
        
        if network not in self.networks.keys():   #on check si il y a déjà une entrée pour ce sous réseau et si non on peut prendre une addresse qu'on veut pour le routeur dans le sous réseau
            address = network.split("/")[0]+ "1/" + network.split("/")[1]
            self.networks[network]={}
            
        else: #le sous-réseau est déjà une entrée dans le dico networks donc il y a déjà au moins une addresse prise dans ce sous réseau
            nombre_elem= len(self.networks[network].keys()) #on compte le nombre d'addresses déjà prises
            if nombre_elem>65534: #on vérifie qu'il n'y a pas plus de 65534 addresses dans notre sous-réseau 
                return "err"
            else:
                address = network.split("/")[0]+ f"{hex(nombre_elem + 1).split('x')[1]}" + "/" + network.split("/")[1]

        self.networks[network][router]=address
        return address 
    
    
    
    def copy_dict(self):
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
        
       
        
    def write_files(self) :
        for Router in self.dict_info.keys() :
            a = self.write_config(self.template, int(Router))
    #        f = open(f"{self.path[Router]}/i{Router}_startup-config.cfg", "w")
    #        f.write(self.write_config(self.template, int(Router)))
    #        f.close()
                   
            
            
config = Config('config_3.json', "template_loop.txt")
config.build_data()
config.write_files()
