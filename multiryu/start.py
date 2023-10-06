import os
import threading

def create_controller(num):
    tcp_port = 6653
    tcp_port = tcp_port + num
    cmd = 'ryu-manager ryu1.py --ofp-tcp-listen-port=' + str(tcp_port)
    os.system(cmd)


# def clear(num):
#     for i in range(num):
#         command='''kill -9 $(netstat -nlp | grep :'''+str(9090+i)+''' | awk '{print $7}' | awk -F"/" '{ print $1 }')'''
#         os.system(command)
#         os.system("netstat -an|awk '/tcp/ {print $6}'|sort|uniq -c")

num = 7
threads = set()
for i in range(num):
    thread_now = threading.Thread(target=create_controller, args=(i,))
    thread_now.start()
    threads.add(thread_now)

for thread_now in threads:
    thread_now.join()


