# from ryu.base import app_manager
# from ryu.controller import ofp_event
# from ryu.controller.handler import MAIN_DISPATCHER
# from ryu.controller.handler import set_ev_cls
# from ryu.ofproto import ofproto_v1_2
# from ryu.lib.packet import packet
# from ryu.lib.packet import ethernet
# from ryu.lib.packet import ether_types


# class SimpleSwitch12(app_manager.RyuApp):
#     OFP_VERSIONS = [ofproto_v1_2.OFP_VERSION]

#     def __init__(self, *args, **kwargs):
#         super(SimpleSwitch12, self).__init__(*args, **kwargs)
#         self.mac_to_port = {}

#     def add_flow(self, datapath, port, dst, src, actions):
#         ofproto = datapath.ofproto

#         match = datapath.ofproto_parser.OFPMatch(in_port=port,
#                                                  eth_dst=dst,
#                                                  eth_src=src)
#         inst = [datapath.ofproto_parser.OFPInstructionActions(
#                 ofproto.OFPIT_APPLY_ACTIONS, actions)]

#         mod = datapath.ofproto_parser.OFPFlowMod(
#             datapath=datapath, cookie=0, cookie_mask=0, table_id=0,
#             command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
#             priority=0, buffer_id=ofproto.OFP_NO_BUFFER,
#             out_port=ofproto.OFPP_ANY,
#             out_group=ofproto.OFPG_ANY,
#             flags=0, match=match, instructions=inst)
#         datapath.send_msg(mod)

#     @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
#     def _packet_in_handler(self, ev):
#         #常规的获取参数操作
#         msg = ev.msg
#         datapath = msg.datapath
#         ofproto = datapath.ofproto
#         in_port = msg.match['in_port']

#         #获取以太网
#         pkt = packet.Packet(msg.data)
#         eth = pkt.get_protocols(ethernet.ethernet)[0]

#         #忽略lldp链路层
#         if eth.ethertype == ether_types.ETH_TYPE_LLDP:
#             # ignore lldp packet
#             return
#         dst = eth.dst
#         src = eth.src

#         dpid = datapath.id
#         self.mac_to_port.setdefault(dpid, {})

#         #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

#         # learn a mac address to avoid FLOOD next time.
#         self.mac_to_port[dpid][src] = in_port

#         if dst in self.mac_to_port[dpid]:
#             out_port = self.mac_to_port[dpid][dst]
#         else:
#             out_port = ofproto.OFPP_FLOOD

#         actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

#         # install a flow to avoid packet_in next time
#         if out_port != ofproto.OFPP_FLOOD:
#             self.add_flow(datapath, in_port, dst, src, actions)

#         data = None
#         if msg.buffer_id == ofproto.OFP_NO_BUFFER:
#             data = msg.data

#         out = datapath.ofproto_parser.OFPPacketOut(
#             datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
#             actions=actions, data=data)
#         datapath.send_msg(out)

# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller import event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import icmp
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib import hub
from ryu.ofproto import ether
from ryu.lib.packet import icmp, tcp, udp
from random import randint,seed
from time import time
import random



#Custom Event for time out
class EventMessage(event.EventBase):
    '''Create a custom event with a provided message'''
    def __init__(self, message):
        print("Creating Event")
        super(EventMessage, self).__init__()
        self.msg=message

#Main Application
class MovingTargetDefense(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _EVENTS = [EventMessage] 
    R2V_Mappings={"10.0.0.1":"","10.0.0.2":"","10.0.0.3":"","10.0.0.4":"","10.0.0.5":"","10.0.0.6":"","10.0.0.7":"","10.0.0.8":"", "10.0.0.9":"",  "10.0.0.10":"", "10.0.0.11":"", "10.0.0.12":""}
    V2R_Mappings={} 
    AuthorizedEntities=['10.0.0.1']
    Resources=["10.0.0.13","10.0.0.14","10.0.0.15","10.0.0.16",
           "10.0.0.17","10.0.0.18","10.0.0.19","10.0.0.20",
           "10.0.0.21","10.0.0.22","10.0.0.23","10.0.0.24",
           "10.0.0.25","10.0.0.26","10.0.0.27","10.0.0.28",
           "10.0.0.29","10.0.0.30","10.0.0.31","10.0.0.32",
           "10.0.0.33","10.0.0.34","10.0.0.35","10.0.0.36",
           "10.0.0.37","10.0.0.38","10.0.0.39","10.0.0.40"]
    dpid_to_port = {(1,2):12, (2,1):12, (2,3):22, (3,2):22, (1,3):32, (3,1):32}
    sw = {}
    mid_id = 2
    forbid_port = 32

    
    def change_topo(self):
            for datapath in self.datapaths.values():
                parser = datapath.ofproto_parser
                match=parser.OFPMatch()
                self.EmptyTable(datapath)
                ofProto=datapath.ofproto
                actions = [parser.OFPActionOutput(ofProto.OFPP_CONTROLLER,
                                                ofProto.OFPCML_NO_BUFFER)]
                self.add_flow_match(datapath, 0, match, actions)
            seed(time())
            random_id = randint(1, 3)
            self.mid_id = random_id
            id_1 = (random_id + 1) % 3
            id_2 = (random_id + 2) % 3
            if id_1 == 0:
                id_1 = 3
            if id_2 == 0:
                id_2 = 3
            self.forbid_port = self.dpid_to_port[(id_1, id_2)] 
            print("now mid id is", self.mid_id)
            print("now forbid_port id is", self.forbid_port)

    def start(self):
        '''
            Append a new thread which calls the TimerEventGen function which generates timeout events
            every 30 seconds & sends these events to its listeners
            Reference: https://sourceforge.net/p/ryu/mailman/ryu-devel/?viewmonth=201601&viewday=12
        '''
        super(MovingTargetDefense,self).start()
        #将一个新的线程添加到应用程序的线程列表中。这个线程调用TimerEventGen函数，该函数生成每30秒的超时事件，并将这些事件发送给监听器。
        self.threads.append(hub.spawn(self.TimerEventGen))
        self.threads.append(hub.spawn(self.TimerEventGen2))
    
    def TimerEventGen2(self):
    
        '''
            A function which generates timeout events every 30 seconds
            每30s生成一个事件
            & sends these events to its listeners
            Reference: https://sourceforge.net/p/ryu/mailman/ryu-devel/?viewmonth=201601&viewday=12
        '''
        while 1:
            self.send_event_to_observers(EventMessage("PATH_SHUFFLE"))
            hub.sleep(10)

    def TimerEventGen(self):
        
        '''
            A function which generates timeout events every 30 seconds
            每30s生成一个事件
            & sends these events to its listeners
            Reference: https://sourceforge.net/p/ryu/mailman/ryu-devel/?viewmonth=201601&viewday=12
        '''
        while 1:
            self.send_event_to_observers(EventMessage("IP_SHUFFLE"))
            hub.sleep(20)
    
    def __init__(self, *args, **kwargs):
        '''Constructor, used to initialize the member variables'''
        super(MovingTargetDefense, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.HostAttachments = {}
        self.offset_of_mappings = 0
        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def handleSwitchFeatures(self, ev):
        '''
            Handles switch feature events sent by the switches to the controller
            the first time switch sends negotiation messages.
            We store the switch info to the datapaths member variable
            & add table miss flow entry to the switches.
            处理交换机首次发送的协商消息时，处理交换机向控制器发送的交换机特性事件。
            将交换机信息存储到datapaths成员变量中,并向交换机添加表缺失流表项。

            #Reference: Simple_Switch
            #http://ryu.readthedocs.io/en/latest/writing_ryu_app.html
        '''
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id]=datapath
        # install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
          
    def EmptyTable(self,datapath):
        '''
            Empties flow table of a switch!
            Remove Flow rules from switches
            Reference: https://sourceforge.net/p/ryu/mailman/message/32333352/
        '''
        ofProto=datapath.ofproto
        parser = datapath.ofproto_parser
        match=parser.OFPMatch()
        flow_mod=datapath.ofproto_parser.OFPFlowMod(datapath,0,0,0,ofProto.OFPFC_DELETE,0,0,1,ofProto.OFPCML_NO_BUFFER,ofProto.OFPP_ANY,ofProto.OFPG_ANY,0,match=match,instructions=[])
        datapath.send_msg(flow_mod)
        
    #Listen to timeout & update the mappings
    @set_ev_cls(EventMessage)
    def update_resources(self,ev):
        '''
            Listen to the Time-out event & update the real-virtual IP address mappings from the resources
            Also remove the flow rules from all the switches.
            & Add a default, table-miss entry to all the switches.
            
        '''
        '''seed function is used initialize random number generator. The current system time is seeded to
        obtain different set of random numbers every time the function runs.'''  
        message = ev.msg
        if message == "IP_SHUFFLE":
            seed(time())
            pseudo_ranum = 6 #randint(0,len(self.Resources)-1) #randint returns a random integer in the range of 0 and len(Resources)-1
            print ("Random Number:",pseudo_ranum)
            for keys in self.R2V_Mappings.keys():
                #Virtual IP address are assigned to each host from the pool of Resources starting from (pseudo_ranum)th index
                self.R2V_Mappings[keys]=self.Resources[pseudo_ranum]
                #pseudo_ranum is updated to point to next index. If the index is overshooted from the Resources pool, it is looped back to point to 0th index  
                pseudo_ranum=(pseudo_ranum+1)%len(self.Resources)    
            self.V2R_Mappings = {v: k for k, v in self.R2V_Mappings.items()}
            print ("**********", self.R2V_Mappings,"***********")
            print ("**********", self.V2R_Mappings,"***********")
        elif message == "PATH_SHUFFLE":
            self.change_topo()


        for curSwitch in self.datapaths.values():
            #Remove all flow entries
            parser = curSwitch.ofproto_parser
            match=parser.OFPMatch()
            flowModMsg=self.EmptyTable(curSwitch)
            #Add default flow rule
            ofProto=curSwitch.ofproto
            actions = [parser.OFPActionOutput(ofProto.OFPP_CONTROLLER,
                                        ofProto.OFPCML_NO_BUFFER)]
            self.add_flow(curSwitch, 0, match, actions)

    def isRealIPAddress(self,ipAddr):
        '''Returns True id IP address is real'''
        if ipAddr in self.R2V_Mappings.keys():
            return True
    
    def isVirtualIPAddress(self,ipAddr):
        ''' Returns True if the IP address is virtual'''
        if ipAddr in self.R2V_Mappings.values():
            return True
        
    '''def isAuthorizedEntity(self,ipAddr):
        if ipAddr in self.AuthorizedEntities:
            return True'''
        
    def isDirectContact(self,datapath,ipAddr):
        '''
            Return true if the IP addr host is directky connected to the switch given
            Also assumes that the host is directly connected if it has no information in the hostAttachments Table
        '''
        if ipAddr in self.HostAttachments.keys():
            if self.HostAttachments[ipAddr]==datapath:
                return True
            else:
                return False
        return True
         
    
    def add_flow(self, datapath, priority, match, actions, buffer_id=None, hard_timeout=None):
        '''
            Adds flow rules to the switch 
            Reference: Simple_Switch
            http://ryu.readthedocs.io/en/latest/writing_ryu_app.html
        '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id :
            if hard_timeout==None:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, hard_timeout=hard_timeout)
        else:
            if hard_timeout==None:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst, hard_timeout=hard_timeout)
        datapath.send_msg(mod)
    

    def add_flow_port(self, datapath, port, dst, src, actions):
        '''
            处理端口形的输入的流表
        '''
        ofproto = datapath.ofproto

        match = datapath.ofproto_parser.OFPMatch(in_port=port,
                                                 eth_dst=dst,
                                                 eth_src=src)
        inst = [datapath.ofproto_parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS, actions)]

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, cookie=0, cookie_mask=0, table_id=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=0, buffer_id=ofproto.OFP_NO_BUFFER,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            flags=0, match=match, instructions=inst)
        datapath.send_msg(mod)


    def add_flow_match(self, datapath, priority, match, actions, buffer_id=None, hard_timeout=None):
        '''
            处理匹配已经写好的流表
        '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id :
            if hard_timeout==None:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, hard_timeout=hard_timeout)
        else:
            if hard_timeout==None:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            else:
                mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst, hard_timeout=hard_timeout)
        datapath.send_msg(mod)    

    #Packet Handler ICMP & ARP
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def handlePacketInEvents(self, ev):
        '''
            Handles Incoming Packets & implements Random Host mutation technique
            by changing src & dst IP addresses of the incoming packets.
            Some part of the code is inspired by Simple_Switch
            http://ryu.readthedocs.io/en/latest/writing_ryu_app.html 
        '''
        actions=[]
        pktDrop=False
        
            
        if ev.msg.msg_len < ev.msg.total_len:
           self.logger.debug("packet truncated: only %s of %s bytes",
                             ev.msg.msg_len, ev.msg.total_len)
            
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        if in_port == self.forbid_port:
            return None     
        pkt = packet.Packet(msg.data)
        arp_Obj=pkt.get_protocol(arp.arp)# Extract ARP object from packet
        icmp_Obj=pkt.get_protocol(ipv4.ipv4)# Extract ICMP object packet

        
        if arp_Obj:
            '''Handles ARP packets'''
            src=arp_Obj.src_ip
            dst=arp_Obj.dst_ip
            
            '''
                To Implement a Learning MTD, there is a need to know, to which switch, the host is directly connected to.
                So the first time an ARP packet comes in who's src address is real, we store the IP addr-Switch DPID mapping
                into the member variable HostAttachments.
                因此,当首次收到源地址为真实IP的ARP数据包时,我们将IP地址和交换机的DPID映射存储在成员变量HostAttachments中。
            '''
            if self.isRealIPAddress(src) and src not in self.HostAttachments.keys():
                self.HostAttachments[src]=datapath.id
                
            '''
                Learning MTD implementation
                if src is real change it to virtual no matter wat.
                if dest doesn't have a mapping in my table change to real and flood.
                    This happens only for the first time when we donot know
                    to which switch, the destination host is directly connected to.
                if dst is virtual check if dest is directly connected then change it to real
                else let it pass unchanged.
                如果源地址是真实IP,则无论如何都将其更改为虚拟IP。
                如果目标地址在我的映射表中没有对应的映射关系,则将其更改为真实IP并进行广播。
                这仅发生在第一次通信时，我们不知道目标主机直接连接到哪个交换机。
                如果目标地址是虚拟IP,则检查目标主机是否直接连接,如果是,则将其更改为真实IP。
                否则，保持不变，不进行任何更改。
            '''
            
            if self.isRealIPAddress(src):
                match=parser.OFPMatch(eth_type=0x0806,in_port=in_port,arp_spa=src,arp_tpa=dst)
                spa = self.R2V_Mappings[src] 
                print("Changing SRC REAL IP "+src+"---> Virtual SRC IP "+spa)
                actions.append(parser.OFPActionSetField(arp_spa=spa))
                
            if self.isVirtualIPAddress(dst):
                match=  parser.OFPMatch(eth_type=0x0806,in_port=in_port,arp_tpa=dst,arp_spa=src)
                if self.isDirectContact(datapath=datapath.id,ipAddr=self.V2R_Mappings[dst]):
                    keys = self.V2R_Mappings.keys() 
                    tpa = self.V2R_Mappings[dst] 
                    print("Changing DST Virtual IP "+dst+"---> REAL DST IP "+tpa)
                    actions.append(parser.OFPActionSetField(arp_tpa=tpa))
                    
            elif self.isRealIPAddress(dst):
                '''Learn MTD From Flood'''
                match=parser.OFPMatch(eth_type=0x0806,in_port=in_port,arp_spa=src,arp_tpa=dst)
                if not self.isDirectContact(datapath=datapath.id,ipAddr=dst):
                    pktDrop=True
                    print ("Dropping from",dpid)
            else:
                pktDrop=True
        elif icmp_Obj:
            '''Handles ICMP packets'''
            #print("ICMP PACKET FOUND!")
            src=icmp_Obj.src
            dst=icmp_Obj.dst
            
            if self.isRealIPAddress(src) and src not in self.HostAttachments.keys():
                self.HostAttachments[src]=datapath.id
            
            '''
                Learning MTD implementation
                if src is real change it to virtual no matter wat.
                if dest doesn't have a mapping in my table change to real and flood.
                    This happens only for the first time when we donot know
                    to which switch, the destination host is directly connected to.
                if dst is virtual check if dest is directly connected then change it to real
                else let it pass unchanged.
            '''
            
            if self.isRealIPAddress(src):         
                match=  parser.OFPMatch(eth_type=0x0800,in_port=in_port,ipv4_src=src,ipv4_dst=dst)
                ipSrc = self.R2V_Mappings[src]
                print("Changing SRC REAL IP "+src+"---> Virtual SRC IP "+ipSrc)
                actions.append(parser.OFPActionSetField(ipv4_src=ipSrc))
            if self.isVirtualIPAddress(dst):
                match =  parser.OFPMatch(eth_type=0x0800,in_port=in_port,ipv4_dst=dst,ipv4_src=src)
                if self.isDirectContact(datapath=datapath.id,ipAddr=self.V2R_Mappings[dst]):
                    ipDst = self.V2R_Mappings[dst] 
                    print("Changing DST Virtual IP "+dst+"---> Real DST IP "+ipDst)
                    actions.append(parser.OFPActionSetField(ipv4_dst=ipDst))
            
            elif self.isRealIPAddress(dst):
                match = parser.OFPMatch(eth_type=0x0800,in_port=in_port,arp_spa=src,arp_tpa=dst)
                if not self.isDirectContact(datapath=datapath.id,ipAddr=dst):
                    pktDrop=True
                    print ("Dropping from",dpid)
            else:
                pktDrop=True
                    
        '''Extract Ethernet Object from packet'''                    
        eth = pkt.get_protocols(ethernet.ethernet)[0]


        dst = eth.dst
        src = eth.src
        '''Store the incoming packet source address, switch & the port combination to be used to learn the packet switching'''
        self.mac_to_port.setdefault(dpid, {})

       # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        
        '''learn a mac address to avoid FLOOD next time.'''
        
        self.mac_to_port[dpid][src] = in_port
        '''Learning Mac implemention to avoid flood'''
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        '''Append the outport action to the action set'''
        if not pktDrop:
            actions.append(parser.OFPActionOutput(out_port))
        '''install a flow to avoid packet_in next time'''
        if out_port != ofproto.OFPP_FLOOD:
            '''
                verify if we have a valid buffer_id, if yes avoid to send both flow_mod & packet_out
                Install Flow rules to avoid the packet in message for similar packets.
            '''
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions,msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)    
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        '''
            Build a packet out message & send it to the switch with the action set,
            Action set includes all the IP addres changes & out port actions.
        '''
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        '''Send the packet out message to the switch'''
        datapath.send_msg(out)
    