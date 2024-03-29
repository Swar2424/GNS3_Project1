import json 
import telnetlib
import time
from threading import Thread

 
class Config() :
    
    def __init__(self, file1, file2) :
        """
        Initialisation : chargement des données de file1 (intent file) et file2 (template pour l'écriture)
        """
        
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
        """
        Création des adresses iBGP, eBGP et récupération des neighbors
        """
        
        for AS in self.AS_dic.values() :

            for Router_list in AS["Routers"] :          
                Router = Router_list[0]
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
                
                if AS["IGP"] == "OSPF" :
                    info["OSPF"] = AS["Metric_val"][f'{Router}']
                
                info["AS"] = [AS["n°"], Router]
                info["Port"]=Router_list[1]
                address = self.addressing(f"10:10:10:{hex(Router).split('x')[1]}::/64", Router)
                if address != "err" :
                    info["Interfaces"]["Loopback0"] = address                 
          
                self.dict_info[name] = info

        
        for network_name, network_dic in self.Inter_AS.items() :

            for Router, Connect in network_dic.items() :
                self.dict_info[Router]["Interfaces"][Connect[0]] = Connect[2]
                self.dict_info[Router]["eBGP_interface"].append(Connect[0]) 
                self.dict_info[Router]["network"].append(self.AS_dic[f"As_{Connect[1]}"]["Prefix"])


        for Router in self.dict_info.keys() :
            
            for Router_peer_list in self.AS_dic[f"As_{self.dict_info[Router]['AS'][0]}"]["Routers"] :
                Router_peer = Router_peer_list[0]
                
                if f"{Router_peer}" != Router :
                    self.dict_info[Router]["neighbor"].append([self.dict_info[f"{Router_peer}"]["Interfaces"]["Loopback0"], self.dict_info[Router]["AS"][0]]) 
            
            for network_name, network_dic in self.Inter_AS.items() :
                
                if f"{Router}" in network_dic.keys() :
                    
                    for Router_peer in network_dic.keys() :
                        
                        if Router_peer != Router :
                            self.dict_info[Router]["neighbor"].append([network_dic[Router_peer][2], network_dic[Router_peer][1], network_dic[Router][4], Router_peer])



    def write_config(self, temp, router):
        """
        Initialisation des variables, sélection de l'IGP, attributions des adresses sur les interfaces,
        attribution des neighbors et des networks, implémentation des commmunities si connexions eBGP
        Toutes les infos utiles sont stockées dans le dico d'information self.dict_info pour être écrites ensuite avec TELNET
        Renvoie config, qui contient l'allure du fichier cfg écrit ensuite (basé sur le template)
        """

        IP_addresses = self.dict_info[f'{router}']['Interfaces']

        numAS = self.dict_info[f'{router}']['AS'][0]
        config = temp
        
        if self.dict_info[f'{router}']['IGP'] == "RIP" :
            process = "rip 200 enable"
            config = config.split("[IGP]")[0] + "rip 200" + "\n redistribute connected" + config.split("[IGP]")[1]
        else :
            process = f"ospf 100 area 0"
            char_temp = ""
            for interface in self.dict_info[f'{router}']['eBGP_interface']  :
                char_temp = f"\n passive-interface {interface}"
            config = config.split("[IGP]")[0] + "ospf 100" + f"\n router-id {router}.{router}.{router}.{router}" + char_temp + config.split("[IGP]")[1]
        
        
        
        interfaces_txt = ""
        for Interface, Address in IP_addresses.items() :
            
            if "Gigabit" in Interface :
                Special = "\n negotiation auto"
                
            elif "Fast" in Interface :
                Special = "\n duplex full"

            else :
                Special = ""
                
            if self.dict_info[f'{router}']['IGP'] == "RIP" and Interface in self.dict_info[f'{router}']["eBGP_interface"] :
                interfaces_txt += f"interface {Interface}\n no ip address{Special}\n ipv6 address {Address}\n ipv6 enable\n!\n"
            elif self.dict_info[f'{router}']['IGP'] == "OSPF" and "Loopback" not in Interface :
                interfaces_txt += f"interface {Interface}\n no ip address{Special}\n ipv6 ospf cost {self.dict_info[f'{router}']['OSPF'][Interface]} \n ipv6 address {Address}\n ipv6 enable\n ipv6 {process}\n!\n"
            else :
                interfaces_txt += f"interface {Interface}\n no ip address{Special}\n ipv6 address {Address}\n ipv6 enable\n ipv6 {process}\n!\n"
        
        config = config.split("[Interfaces]\n")[0] + interfaces_txt + config.split("[Interfaces]\n")[1]
        config = config.split("[AS]")[0] + f"{numAS}\n" + f" bgp router-id {router}.{router}.{router}.{router}" + config.split("[AS]")[1]
        
        
        
        char_neighbor = ""
        char_activate = ""
        char_community = ""
        char_route_map = ""
        
        if self.dict_info[f'{router}']['eBGP_interface'] != [] :    
            char_community += "\nip community-list 1 permit 10\nip community-list 1 permit 20\nip community-list 1 permit 30"
            char_community += "\nip community-list 2 permit 10\nip community-list 2 deny 20\nip community-list 2 deny 30"
            char_community += "\nip community-list 3 permit 10\nip community-list 3 deny 20\nip community-list 3 deny 30"
            char_community += "\nip community-list 4 permit 10\nip community-list 5 permit 20\nip community-list 6 permit 30"
            char_route_map += "\nroute-map Client-map-out permit 100\n match community 1\n!"
            char_route_map += "\nroute-map Peer-map-out permit 100\n match community 2\n!"
            char_route_map += "\nroute-map Provider-map-out permit 100\n match community 3\n!"
            char_route_map += "\nroute-map iBGP-map-out permit 100\n match community 1\n!"
            char_route_map += "\nroute-map Client-map permit 100\n set community 10\n set local-preference 400\n!"
            char_route_map += "\nroute-map Peer-map permit 100\n set community 20\n set local-preference 300\n!"
            char_route_map += "\nroute-map Provider-map permit 100\n set community 30\n set local-preference 200\n!"
            char_route_map += "\nroute-map iBGP-map permit 100\n match community 4\n set local-preference 400\n!"
            char_route_map += "\nroute-map iBGP-map permit 200\n match community 5\n set local-preference 300\n!"
            char_route_map += "\nroute-map iBGP-map permit 300\n match community 6\n set local-preference 200\n!"
        
        for neighbor_list in self.dict_info[f'{router}']['neighbor'] :  
            neighbor_tronque = neighbor_list[0].split("/")[0]
            char_neighbor += f"neighbor {neighbor_tronque} remote-as {neighbor_list[1]}\n "
            char_activate += f"  neighbor {neighbor_tronque} activate\n"
            
            if neighbor_list[0][:9] == "10:10:10:" :   
                char_neighbor += f"neighbor {neighbor_tronque} update-source Loopback0\n "
            
            if neighbor_list[1] != self.dict_info[f'{router}']['AS'][0] :  
                Type = neighbor_list[2]
       
                char_activate += f"  neighbor {neighbor_tronque} route-map {Type}-map in\n"
                char_activate += f"  neighbor {neighbor_tronque} route-map {Type}-map-out out\n"
                char_activate += f"  neighbor {neighbor_tronque} send-community\n"
            elif self.dict_info[f'{router}']['eBGP_interface'] != [] :
                char_activate += f"  neighbor {neighbor_tronque} route-map iBGP-map in\n"
                char_activate += f"  neighbor {neighbor_tronque} route-map iBGP-map-out out\n"
                char_activate += f"  neighbor {neighbor_tronque} send-community\n"
                

        char_neighbor = char_neighbor[:len(char_neighbor)-2]
        char_activate = char_activate[:len(char_activate)-1]
        
        config = config.split("[neighbor]")[0] + char_neighbor + config.split("[neighbor]")[1]
        config = config.split("\n[route-map]")[0] + char_route_map + config.split("\n[route-map]")[1]
        config = config.split("\n[community]")[0] + char_community + config.split("\n[community]")[1]
        
        
               
        if self.dict_info[f'{router}']['network'] != [] :        
            network = self.dict_info[f'{router}']['network'][0]
            
            char_net = f"  network {network} route-map Client-map\n"
            char_route = f"\nipv6 route {network} Null0"
            
            char_net = char_net[2:]
            config = config.split("[network]")[0] + char_net + char_activate + config.split("[network]")[1]
            config = config.split("\n[route]")[0] + char_route +  config.split("\n[route]")[1]
            
        else:
            config = config.split("  [network]")[0] + char_activate + config.split("  [network]")[1]
            config = config.split("\n[route]")[0] + config.split("\n[route]")[1]
            
        return(config)
    
    
    
    def addressing(self, network, router): 
        """
        Prends en paramètre un nom de réseau et le router qui cherche une adresse
        Renvoie une adresse non utilisée
        """
        
        if network not in self.networks.keys():   
            self.networks[network]={}
            
        else: 
            nombre_elem= len(self.networks[network].keys()) 
            if nombre_elem>65534: 
                return "err"
            else:
                address = network.split("/")[0]+ f"{hex(nombre_elem + 1).split('x')[1]}" + "/" + network.split("/")[1]

        self.networks[network][router]=address
        return address 
    
    
    
    def copy_dict(self):
        """
        Crée et renvoie le template de base d'un dico d'information
        """
        
        return {
        "Interfaces" : {},
        "IGP" : [],
        "AS" : [],
        "neighbor" : [],
        "network" : [],
        "eBGP_interface" : [],
        "Port" : []
        }
        
        
        
    def write_files(self) :
        """
        Écrit dans le dossier ./cfg_files la config correspondant à chaque router
        """
        
        for Router in self.dict_info.keys() :
            f = open(f"./cfg_files/i{Router}_startup-config.cfg", "w")
            
            f.write(self.write_config(self.template, int(Router)))

            f.close()
                   
                   
                   
    def Launch_Telnet(self):
        """
        Lance avec multithreading l'écriture par TELNET des commandes pour mettre la config
        sur chaque router
        """
        
        for Router, dico in self.dict_info.items() :
            t = Thread(target = self.Telnet, args = (Router, dico))
            t.start()
            
    
    
    def Telnet(self, Router, dico):
        """
        Prend en paramètre un routeur et le dico d'information associé
        Écrit les commandes correspondantes avec TELNET
        Nécessite que le router avec le numéro de port correspondant aie sa console ouverte
        et prête à recevoir des commandes
        """
        
        telnet_connexion = telnetlib.Telnet("localhost",dico["Port"]) #ajouter le port dans le dico
        
        if dico["IGP"] == "RIP":
            

            telnet_connexion.write(b"enable\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"configure terminal\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ipv6 unicast-routing\r\n")
            time.sleep(0.05)
            
            for interface, address in dico["Interfaces"].items():
                telnet_connexion.write(bytes(f"interface {interface}\r\n", "utf-8"))
                time.sleep(0.05)
                telnet_connexion.write(b"ipv6 enable\r\n")
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"ipv6 address {address}\r\n", "utf-8"))
                time.sleep(0.05)
                telnet_connexion.write(b"no shutdown\r\n")
                time.sleep(0.05)
                
                if interface not in dico["eBGP_interface"]:
                    telnet_connexion.write(b"ipv6 router rip ripprocess\r\n")
                    time.sleep(0.05)
                    telnet_connexion.write(b"redistribute connected\r\n")
                    time.sleep(0.05)
                telnet_connexion.write(b"exit\r\n")
                time.sleep(0.05)
                
                if interface not in dico["eBGP_interface"]:
                    telnet_connexion.write(bytes(f"interface {interface}\r\n","utf-8"))
                    time.sleep(0.05)
                    telnet_connexion.write(b"ipv6 rip ripprocess enable\r\n")
                    time.sleep(0.05)
                    telnet_connexion.write(b"exit\r\n")
                    time.sleep(0.05)
            telnet_connexion.write(b"end\r\n")

        if dico["IGP"] == "OSPF":
            
            
            telnet_connexion.write(b"enable\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"configure terminal\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ipv6 unicast-routing\r\n")
            time.sleep(0.05)
            telnet_connexion.write(bytes(f"ipv6 router ospf {Router}\r\n","utf-8"))   
            time.sleep(0.05)
            telnet_connexion.write(bytes(f"router-id {Router}.{Router}.{Router}.{Router}\r\n", "utf-8"))  
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            
            for interface, address in dico["Interfaces"].items():
                telnet_connexion.write(bytes(f"interface {interface}\r\n", "utf-8"))
                time.sleep(0.05)
                telnet_connexion.write(b"ipv6 enable\r\n")
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"ipv6 address {address}\r\n", "utf-8"))
                time.sleep(0.05)
                telnet_connexion.write(b"no shutdown\r\n")
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"ipv6 ospf {Router} area 0\r\n","utf-8"))   
                time.sleep(0.05) 
                
                if interface in dico["OSPF"].keys():
                    telnet_connexion.write(bytes(f"ipv6 ospf cost {dico['OSPF'][interface]}\r\n","utf-8"))
                    time.sleep(0.05)
                
                telnet_connexion.write(b"exit\r\n")
                time.sleep(0.05)
                
                if interface in dico["eBGP_interface"]:
                    telnet_connexion.write(bytes(f"ipv6 router ospf {Router}\r\n","utf-8"))   
                    time.sleep(0.05)
                    telnet_connexion.write(bytes(f"passive-interface {interface}\r\n","utf-8"))
                    time.sleep(0.05)
                    
            telnet_connexion.write(b"end\r\n")
            time.sleep(0.05)
        
        telnet_connexion.write(b"conf t\r\n")   
        time.sleep(0.05)
        telnet_connexion.write(bytes(f"router bgp {dico['AS'][0]}\r\n","utf-8"))
        time.sleep(0.05)
        telnet_connexion.write(b"no bgp default ipv4-unicast\r\n")
        time.sleep(0.05)
        telnet_connexion.write(bytes(f"bgp router-id {Router}.{Router}.{Router}.{Router}\r\n","utf-8")) 
        time.sleep(0.05)
        
        for list_neighbor in dico["neighbor"]:
            neighbor_address = list_neighbor[0]
            neighbor_AS = list_neighbor[1]
            telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} remote-as {neighbor_AS}\r\n","utf-8")) 
            time.sleep(0.05)
            
            if dico["AS"][0]==neighbor_AS:
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} update-source Loopback0\r\n","utf-8")) 
                time.sleep(0.05)

            telnet_connexion.write(b"address-family ipv6 unicast\r\n")
            time.sleep(0.05)
            telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} activate\r\n","utf-8")) 
            time.sleep(0.05)
            
            if dico["AS"][0]!=neighbor_AS:
                Type = list_neighbor[2]
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} route-map {Type}-map in\r\n","utf-8")) 
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} route-map {Type}-map-out out\r\n","utf-8")) 
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} send-community\r\n","utf-8")) 
                time.sleep(0.05)
                
            elif dico['eBGP_interface'] != [] :
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} route-map iBGP-map in\r\n","utf-8")) 
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} route-map iBGP-map-out out\r\n","utf-8")) 
                time.sleep(0.05)
                telnet_connexion.write(bytes(f"neighbor {neighbor_address[:-3]} send-community\r\n","utf-8")) 
                time.sleep(0.05)
            
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            
        if dico["network"] != []:
            net = dico["network"][0]
            telnet_connexion.write(b"address-family ipv6 unicast\r\n")
            time.sleep(0.05)
            telnet_connexion.write(bytes(f"network {net} route-map Client-map\r\n","utf-8")) 
            time.sleep(0.05)
            telnet_connexion.write(b"end\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"conf t\r\n")
            time.sleep(0.05)
            telnet_connexion.write(bytes(f"ipv6 route {net} Null0\r\n", 'utf-8'))
            time.sleep(0.05)
            telnet_connexion.write(b"end\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"config t\r\n")
            time.sleep(0.05)
            
            
            telnet_connexion.write(b"ip community-list 1 permit 10\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 1 permit 20\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 1 permit 30\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 2 permit 10\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 2 deny 20\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 2 deny 30\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 3 permit 10\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 3 deny 20\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 3 deny 30\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 4 permit 10\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 5 permit 20\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"ip community-list 6 permit 30\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Client-map-out permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 1\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Peer-map-out permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 2\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Provider-map-out permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 3\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map iBGP-map-out permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 1\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Client-map permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set community 10\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 400\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Peer-map permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set community 20\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 300\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map Provider-map permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set community 30\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 200\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"exit\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map iBGP-map permit 100\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 4\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 400\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map iBGP-map permit 200\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 5\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 300\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"route-map iBGP-map permit 300\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"match community 6\r\n")
            time.sleep(0.05)
            telnet_connexion.write(b"set local-preference 200\r\n")
            time.sleep(0.05)
            
        telnet_connexion.write(b"end\r\n")
        time.sleep(0.05)
            
        if telnet_connexion:
            telnet_connexion.close()

                 
        
     
config = Config('config_3.json', "template_loop.txt")
config.build_data()
config.write_files()
config.Launch_Telnet()
