import json 
import telnetlib
import time

 
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

            

            for router_list in AS["Routers"] :   
                Router = router_list[0]       
                name = f"{Router}"
                
                info = self.copy_dict()
                
                for network_name, network_dic in AS["Networks"].items() : 
                    
                    if name in network_dic.keys() :
                        address = self.addressing(network_name, Router)
                        
                        if address != "err" :
                            info["Interfaces"][network_dic[name]] = (address)
                            
                        else :
                            print(f"Too much address in {network_name}") 

                    
                info["IGP"] = AS["IGP"]
                info["AS"] = [AS["n°"], Router]
                info["Port"]=router_list[1]
                address = self.addressing(f"10:10:10:{hex(Router).split('x')[1]}::/64", Router)
                if address != "err" :
                    info["Interfaces"]["Loopback0"] = address                 
          
                self.dict_info[name] = info


            


        #Création des adresses eBGP  
        for network_name, network_dic in self.Inter_AS.items() :

            for Router, Connect in network_dic.items() :
                self.dict_info[Router]["Interfaces"][Connect[0]] = Connect[2]
                self.dict_info[Router]["eBGP_interface"] = Connect[0]
                self.dict_info[Router]["network"].append(self.AS_dic[f"As_{Connect[1]}"]["Prefix"][1])

        #Récupération des neighbors
        for Router in self.dict_info.keys() :
            
            for Router_peer_list in self.AS_dic[f"As_{self.dict_info[Router]['AS'][0]}"]["Routers"] :
                Router_peer = Router_peer_list[0]
                
                if f"{Router_peer}" != Router :
                    self.dict_info[Router]["neighbor"].append([self.dict_info[f"{Router_peer}"]["Interfaces"]["Loopback0"], self.dict_info[Router]["AS"][0]])
                
            for network_name, network_dic in self.Inter_AS.items() :
                
                if f"{Router}" in network_dic.keys() :
                    
                    for Router_peer in network_dic.keys() :
                        
                        if Router_peer != Router :
                            self.dict_info[Router]["neighbor"].append([self.dict_info[Router_peer]["Interfaces"][self.dict_info[Router_peer]["eBGP_interface"]], network_dic[Router_peer][1]])
                        
               
                           
    def write_config(self, temp, router):



        #Initialisation des variables
        IP_addresses = self.dict_info[f'{router}']['Interfaces']

        numAS = self.dict_info[f'{router}']['AS'][0]
        config = temp
        
        #Sélection de l'IGP
        if self.dict_info[f'{router}']['IGP'] == "RIP" :
            process = "rip 200 enable"
            config = config.split("[OSPFband]")[0] + config.split("[OSPFband]")[1]
            config = config.split("[IGP]")[0] + "rip 200" + "\n redistribute connected" + config.split("[IGP]")[1]
        else :
            process = f"ospf 100 area 0"
            config = config.split("[OSPFband]")[0] + (f'router ospf {router} \n  auto-cost reference-bandwidth {self.AS_dic["As_2"]["Metricref"]}' + config.split("[OSPFband]")[1])
            char_temp = ""
            if self.dict_info[f'{router}']['eBGP_interface'] != [] :
                char_temp = f"\n passive-interface {self.dict_info[f'{router}']['eBGP_interface']}"
            config = config.split("[IGP]")[0] + "ospf 100" + f"\n router-id {router}.{router}.{router}.{router}" + char_temp + config.split("[IGP]")[1]
        
        #Attributions des adresses sur les interfaces
        interfaces_txt = ""
        for Interface, Address in IP_addresses.items() :
            
            if "Gigabit" in Interface :
                    Special = "\n negotiation auto"
                    BandW = "1000000"
                
            elif "Fast" in Interface :
                    Special = "\n duplex full"
                    BandW = "100000"
            else :
                Special = ""
                
            if ((Interface == self.dict_info[f'{router}']['eBGP_interface']) and (self.dict_info[f'{router}']['IGP'] == "RIP")) :
                interfaces_txt += f"interface {Interface}\n no ip address{Special}\n ipv6 address {Address}\n ipv6 enable\n!\n"
            else :
                interfaces_txt += f"interface {Interface}\n no ip address{Special}\n bandwidth {BandW} \n ipv6 address {Address}\n ipv6 enable\n ipv6 {process}\n!\n"
        
        config = config.split("[Interfaces]\n")[0] + interfaces_txt + config.split("[Interfaces]\n")[1]
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
            if neighbor_list[1] != self.dict_info[f'{router}']['AS'][0] :
                char_activate += f"  neighbor {neighbor_tronque} route-map community-map in\n"
                char_activate += f"  neighbor {neighbor_tronque} send-community\n"
                
        char = char[:len(char)-2]
        char_activate = char_activate[:len(char_activate)-1]
        
        config = config.split("[neighbor]")[0] + char + config.split("[neighbor]")[1]
        
        #Attribution des networks        
        if self.dict_info[f'{router}']['network'] != [] :        
            network = self.dict_info[f'{router}']['network'][0]
            network_inter_as = (self.dict_info[f'{router}']["Interfaces"][self.dict_info[f'{router}']['eBGP_interface']]).split('::')[0] + "::/64"
            As_remote = self.Inter_AS[network_inter_as][f'{router}'][3]
            As = self.Inter_AS[network_inter_as][f'{router}'][1]
            weight = self.Inter_AS[network_inter_as][f'{router}'][4]
            
            char_net = f"  network {network} route-map community-map-out\n"
            char_route = f"\nipv6 route {network} Null0"
            char_community = f"\nip bgp-community new-format\nip community-list 1 permit 1:{As_remote + 5}"
            char_route_map = f"\nroute-map community-map permit 100\n match community 1\n set metric {weight}\n!\n"
            char_route_map += f"route-map community-map-out permit 100\n set community 1:{As + 5}\n!"
            
            char_net = char_net[2:]
            config = config.split("[network]")[0] + char_net + char_activate + config.split("[network]")[1]
            config = config.split("\n[route]")[0] + char_route +  config.split("\n[route]")[1]
            config = config.split("\n[route-map]")[0] + char_route_map + config.split("\n[route-map]")[1]
            config = config.split("\n[community]")[0] + char_community + config.split("\n[community]")[1]
            
        else:

            config = config.split("  [network]")[0] + char_activate + config.split("  [network]")[1]
            config = config.split("\n[route]")[0] + config.split("\n[route]")[1]
            config = config.split("\n[route-map]")[0] + config.split("\n[route-map]")[1]
            config = config.split("\n[community]")[0] + config.split("\n[community]")[1]
            
        #print(config)
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
        "Interfaces" : {
        },
        "IGP" : [],
        "AS" : [],
        "neighbor" : [],
        "network" : [],
        "eBGP_interface" : [],
        "Port" : []
        }
        
       
        
    def write_files(self) :
        for Router in self.dict_info.keys() :
            #f = open(f"{self.path[Router]}/i{Router}_startup-config.cfg", "w")
            
            #f.write(self.write_config(self.template, int(Router)))
            print((self.write_config(self.template, int(Router))))
            #f.close()
                   
    def Telnet(self):
        for Router, dico in self.dict_info.items() :
            telnet_connexion = telnetlib.Telnet("localhost",dico["Port"]) #ajouter le port dans le dico
            if dico["IGP"] == "RIP":
                #config rip
                
                telnet_connexion.write(b"enable\r\n")
                time.sleep(0.01)
                telnet_connexion.write(b"configure terminal\r\n")
                time.sleep(0.01)
                telnet_connexion.write(b"ipv6 unicast-routing\r\n")
                time.sleep(0.01)
                for interface, address in dico["Interfaces"].items():
                    telnet_connexion.write(bytes(f"interface {interface}\r\n", "utf-8"))
                    time.sleep(0.01)
                    telnet_connexion.write(b"ipv6 enable\r\n")
                    time.sleep(0.01)
                    telnet_connexion.write(bytes(f"ipv6 address {address}\r\n", "utf-8"))
                    time.sleep(0.01)
                    telnet_connexion.write(b"no shutdown\r\n")
                    time.sleep(0.01)
                    if interface not in dico["eBGP_interface"]:
                        telnet_connexion.write(b"ipv6 router rip ripprocess\r\n")
                        time.sleep(0.01)
                        telnet_connexion.write(b"redistribute connected\r\n")
                        time.sleep(0.01)
                    telnet_connexion.write(b"exit\r\n")
                    time.sleep(0.01)
                    if interface not in dico["eBGP_interface"]:
                        telnet_connexion.write(bytes(f"interface {interface}\r\n","utf-8"))
                        time.sleep(0.01)
                        telnet_connexion.write(b"ipv6 rip ripprocess enable\r\n")
                        time.sleep(0.01)
                        telnet_connexion.write(b"exit\r\n")
                        time.sleep(0.01)
                telnet_connexion.write(b"end\r\n")       

            if dico["IGP"] == "OSPF":
                #config ospf
                
                telnet_connexion.write(b"enable\r\n")
                time.sleep(0.01)
                telnet_connexion.write(b"configure terminal\r\n")
                time.sleep(0.01)
                telnet_connexion.write(b"ipv6 unicast-routing\r\n")
                time.sleep(0.01)
                telnet_connexion.write(bytes(f"ipv6 router ospf {Router}\r\n","utf-8"))   
                time.sleep(0.01)
                telnet_connexion.write(bytes(f"router-id {Router}.{Router}.{Router}.{Router}\r\n", "utf-8"))  
                time.sleep(0.01) 

                telnet_connexion.write(b"exit\r\n")
                time.sleep(0.01)
                for interface, address in dico["Interfaces"].items():
                    telnet_connexion.write(bytes(f"interface {interface}\r\n", "utf-8"))
                    time.sleep(0.01)
                    telnet_connexion.write(b"ipv6 enable\r\n")
                    time.sleep(0.01)
                    telnet_connexion.write(bytes(f"ipv6 address {address}\r\n", "utf-8"))
                    time.sleep(0.01)
                    telnet_connexion.write(b"no shutdown\r\n")
                    time.sleep(0.01)
                    telnet_connexion.write(bytes(f"ipv6 ospf {Router} area 0\r\n","utf-8"))   
                    time.sleep(0.01)    
                    telnet_connexion.write(b"exit\r\n")
                    time.sleep(0.01)
                    

                    if interface in dico["eBGP_interface"]:
                        telnet_connexion.write(bytes(f"ipv6 router ospf {Router}\r\n","utf-8"))   
                        time.sleep(0.01)
                        telnet_connexion.write(bytes(f"passive-interface {interface}\r\n","utf-8"))
                        time.sleep(0.01)
                telnet_connexion.write(b"end\r\n")
                time.sleep(0.01)
            
            telnet_connexion.write(b"conf t\r\n")   
            time.sleep(0.01)
            telnet_connexion.write(bytes(f"router bgp {dico['AS'][0]}\r\n","utf-8"))
            time.sleep(0.01)
            telnet_connexion.write(b"no bgp default ipv4-unicast\r\n")
            time.sleep(0.01)
            telnet_connexion.write(bytes(f"bgp router-id {Router}.{Router}.{Router}.{Router}\r\n","utf-8")) 
            time.sleep(0.01)
            for neighbor_address, neighbor_AS in dico["neighbor"]:
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} remote-as {neighbor_AS}\r\n","utf-8")) 
                time.sleep(0.01)
                if dico["AS"][0]==neighbor_AS:
                    telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} update-source Loopback0\r\n","utf-8")) 
                    time.sleep(0.01)
                

                telnet_connexion.write(b"address-family ipv6 unicast\r\n")
                time.sleep(0.01)
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} activate\r\n","utf-8")) 
                time.sleep(0.01)
                telnet_connexion.write(b"exit\r\n")
                time.sleep(0.01)
            for net in dico["network"]:
                telnet_connexion.write(b"address-family ipv6 unicast\r\n")
                time.sleep(0.01)
                telnet_connexion.write(bytes(f"network {net}\r\n","utf-8")) 
                time.sleep(0.01)
                telnet_connexion.write(b"end\r\n")
                time.sleep(0.01)
                telnet_connexion.write(b"conf t\r\n")
                time.sleep(0.01)
                telnet_connexion.write(bytes(f"ipv6 route {net} Null0\r\n", 'utf-8'))
                time.sleep(0.01)
          
            if telnet_connexion:
                telnet_connexion.close()
            #config BGP
                 


#            if AS["IGP"]=="RIP":
#                for router in AS["Routeurs"]:
#                    telnet_connexion = telnetlib.Telnet("localhost",port)
#                    telnet_connexion.write("test")
                    
#            if AS["IGP"]=="OSPF":
#                for router in AS["Routeurs"]:
#                    telnet_connexion = telnetlib.Telnet("localhost",port)
#                    telnet_connexion.write("test")
        

            
config = Config('config_3.json', "template_loop.txt")
config.build_data()
config.write_files()
config.Telnet()
