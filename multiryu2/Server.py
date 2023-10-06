#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
该类只负责创建一个Server连接，消息处理交给Client类
"""
import logging
import networkx as nx
from gevent import monkey;monkey.patch_all()
import socket
import time
import contextlib
import json
from gevent import spawn
from threading import Thread
import settings

IP=settings.IP     #IP

PORT=settings.PORT          #端口号

WAIT_CONNECT=settings.WAIT_CONNECT  #最大等待连接数

MONITOR=settings.MONITOR        #打印消息周期

"""
    controller_id 每一个控制器的IP从0开始，具体从几开始，要看网络的子网号，具体请看mininet拓扑文件中的配置信息
"""


class Server(object):
    def __init__(self, *args):
        #初始化服务类
        super(Server, self).__init__()
        self.server = self.start_server()


    #========初始化服务器========
    def start_server(self):
        server=socket.socket()
        server.bind((IP,PORT))
        server.listen(WAIT_CONNECT)
        return server


    def accept_client(self):
        while True:
            controller, addr = self.server.accept()  # 为每一个client保存为一个对象，返回每一个操控该客户端的socket句柄，也就是client
            # t=self.thread_exec.submit()
            self.controller_id += 1
            thread = Thread(target=self.start_client, args=(controller, addr))
            #thread.setDaemon(True)  # 主进程结束，该守护进程结束
            thread.start()
            

    def remove_client(self,controller_id):
        """
        :param controller_id: 控制器ID
        :return: 控制器下线
        """
        controller=self.controller_obj[controller_id]
        if controller:
            controller.close()
            self.controller_obj.pop(controller_id)
            print(f'控制器：{controller_id}  下线！')

    def start(self):
        spawn(self.monitor)  # 协程监控，打印全局拓扑
        print("Server start...")

    def monitor(self):  # 2s打印拓扑
        while True:
            #self.log.info(f'cur：{self.sw_ip}')
            time.sleep(MONITOR)

def main():

    server=Server()
    server.start()

    accept=Thread(target=server.accept_client)
    accept.start()

if __name__ == '__main__':
    main()