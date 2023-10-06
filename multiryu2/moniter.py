# 编码时间: 2021/3/3 17:25
# @File : my_monitor_13.py
# @software : PyCharm
from operator import attrgetter
 
import ryu1
import ryu_comprehensive_state_1
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
 
 
class MyMonitor13(ryu_comprehensive_state_1.MovingTargetDefense):
 
    def __init__(self, *args, **kwargs):          #初始化函数
        super(MyMonitor13, self).__init__(*args, **kwargs)
        self.datapaths = {}          #初始化成员变量，用来存储数据
        self.monitor_thread = hub.spawn(self._monitor)    #用协程方法执行_monitor方法，这样其他方法可以被其他协程执行。 hub.spawn()创建协程
 
    """
    Controller组件主要由OpenFlowController和Datapath两类构成，其中，OpenFlowController负责监听与Ryu连接的OpenFlow网络中的事件，
    一旦有事件发生，会创建一个Datapath对象负责接收来自该事件的连接和数据，并将这些事件的数据分组进行解析，封装成Ryu的事件对象，然后派发。
    """
    #get datapath info 获取datapath信息
    #EventOFPStateChange事件用于检测连接和断开。
    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER,DEAD_DISPATCHER])#通过ryu.controller.handler.set_ev_cls装饰器（decorator）进行注册，在运行时，ryu控制器就能知道MyMonitor13这个模块的函数_state_change_handler监听了一个事件
    def _state_change_handler(self,event):  #交换机状态发生变化后，让控制器数据于交换机一致
        datapath=event.datapath
        if event.state == MAIN_DISPATCHER:            # 在MAIN_DISPATCHER状态下，交换机处于上线状态
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x',datapath.id)
                self.datapaths[datapath.id]=datapath   #datapath用字典来保存，key为id,value为datapath
        elif event.state == DEAD_DISPATCHER:          #在DEAD_DISPATCHER状态下
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath:%016x',datapath.id)
                del self.datapaths[datapath.id]
 
    #send request msg periodically
    def _monitor(self):
        while True:              #对已注册交换机发出统计信息获取请求每10秒无限地重复一次           
            for dp in self.datapaths.values():  #遍历所有的交换机或网桥
                self._request_stats(dp)
            hub.sleep(30)         #休眠
 
 
    #send stats request msg to datapath        （完成控制器主动下发逻辑）
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
 
 
    #handle the port stats reply msg             （完成交换机被动发送逻辑）
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
 
    #handle the flow entry stats reply msg
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply,MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self,event):
        body=event.msg.body    # body:OFPFlowStats的列表，存储受FlowStatsRequest影响每个流表项的统计信息
 
        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority==1]
                              ,key=lambda flow:(flow.match['in_port'],flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                             event.msg.datapath.id,stat.match['in_port'],
                             stat.match['eth_dst'],stat.instructions[0].actions[0].port,
                             stat.packet_count,stat.byte_count)
 
 
 