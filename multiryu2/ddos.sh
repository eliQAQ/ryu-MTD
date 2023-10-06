h1 python -m http.server 80 &
h2 ping -f h3
h2 nc h1 80
iperf h1 h2
sudo mn --custom topo.py --topo mytopo --controller remote #启动自定义拓扑
sudo mn --topo single,3 --mac --switch ovsk --controller remote -x #启动简单topo