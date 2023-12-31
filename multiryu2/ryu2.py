from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_2
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.ofproto import ether
from ryu.lib.packet import ipv4, ethernet, udp
from ryu.lib.packet import icmp, tcp


class SimpleSwitch12(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_2.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch12, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, port, dst, src, actions):
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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        #常规的获取参数操作
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        #获取以太网
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        print(eth)
        #忽略lldp链路层
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id


        if eth.ethertype == ether.ETH_TYPE_IP:
            # 在这里处理IPv4数据包
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            print(ipv4_pkt)
            if ipv4_pkt.proto == 6:  # 检查UDP协议（17是UDP的协议号）
                # 在这里处理UDP数据包
                tcp_pkt = pkt.get_protocol(tcp.tcp)
                if tcp_pkt:
                    tcp_pkt.dst_port = 4000

                src_port = tcp_pkt.src_port
                dst_port = tcp_pkt.dst_port
                self.logger.info(f"TCP packet with source port {src_port} and destination port {dst_port} received")
                print(pkt.get_protocol(tcp.tcp))
                    
        # pkt.serialize()
        # print(pkt.data)

        self.mac_to_port.setdefault(dpid, {})

        #self.logger.info("packet in %s %s %s %s %s", dpid, src, dst, in_port, pkt)
        #self.logger.info("packet in %s",pkt)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, in_port, dst, src, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = pkt.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data)
        datapath.send_msg(out)