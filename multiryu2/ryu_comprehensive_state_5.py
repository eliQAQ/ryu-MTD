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
from ryu.lib.packet import ether_types
import random
from operator import attrgetter



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
    pre_stat_port = {}
    stat_port = {}
    forbid_port = 32
    dpid_forbid_port = {}

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
            self.send_event_to_observers(EventMessage("ACCESS_CONTROLL"))
            hub.sleep(30)

    def TimerEventGen(self):
        
        '''
            A function which generates timeout events every 30 seconds
            每30s生成一个事件
            & sends these events to its listeners
            Reference: https://sourceforge.net/p/ryu/mailman/ryu-devel/?viewmonth=201601&viewday=12
        '''
        while 1:
            self.send_event_to_observers(EventMessage("LOAD_BALANCE"))
            hub.sleep(20)
    
    def __init__(self, *args, **kwargs):
        '''Constructor, used to initialize the member variables'''
        super(MovingTargetDefense, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.port_to_mac = {}
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
        message = ev.msg

        if message == "ACCESS_CONTROLL":
            for dpid in self.datapaths.keys():
                dpid = format(dpid, "d").zfill(16)
                if dpid not in self.pre_stat_port:
                    self.pre_stat_port.setdefault(dpid, {})
                    self.stat_port.setdefault(dpid, {})
                    for key in self.port_to_mac[dpid]:
                        self.pre_stat_port[dpid][key] = 0
                        self.stat_port[dpid][key] = 0
            for dp in self.datapaths.values():  #遍历所有的交换机或网桥
                self._request_stats(dp)

            
            
        elif message == "LOAD_BALANCE":
            print("还没做")

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



    def _request_stats(self,datapath):
        self.logger.info('send stats request:%016x',datapath.id)
        ofproto=datapath.ofproto
        ofp_parser=datapath.ofproto_parser   #解析器
 
        # send flow stats request msg
        # request=ofp_parser.OFPFlowStatsRequest(datapath)
        # datapath.send_msg(request)
 
        # send port stats request msg
        request=ofp_parser.OFPPortStatsRequest(datapath,0,ofproto.OFPP_ANY)
        datapath.send_msg(request)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply,MAIN_DISPATCHER)
    def _port_stats_reply_handler(self,event):
        body=event.msg.body     #消息体
 
        self.logger.info('datapath         port      '
                         'rx-pkts  rx-bytes rx-error '  
                         'tx-pkts  tx-bytes tx-error ')     # rx-pkts:receive packets tx-pks:transmit packets
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
        for stat in sorted(body,key=attrgetter('port_no')):     #attrgetter：属性获取工具
            self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
                             event.msg.datapath.id, stat.port_no,
                             stat.rx_packets, stat.rx_bytes, stat.rx_errors,
                             stat.tx_packets, stat.tx_bytes, stat.tx_errors)
            dpid = format(event.msg.datapath.id, "d").zfill(16)
            self.stat_port[dpid][stat.port_no] = stat.rx_packets

        for dpid in self.datapaths.keys():
            dpid = format(dpid, "d").zfill(16)
            mark_port = 0
            mark_num = 0
            for port, num in self.stat_port[dpid].items():
                if port > 10:
                    continue
                now_num = num - self.pre_stat_port[dpid][port]
                if now_num > mark_num:
                    mark_port = port
                    mark_num = now_num
                self.pre_stat_port[dpid][port] = num
            if mark_num > 25:
                self.dpid_forbid_port[dpid] = mark_port
            else:
                self.dpid_forbid_port[dpid] = -1

            

        

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
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        if in_port == self.forbid_port:
            return None     
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = format(datapath.id, "d").zfill(16)

        if dpid in self.dpid_forbid_port:
            if in_port == self.dpid_forbid_port[dpid]:
                return None

        self.mac_to_port.setdefault(dpid, {})
        self.port_to_mac.setdefault(dpid, {})

        #self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port
        self.port_to_mac[dpid][in_port] = src

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)