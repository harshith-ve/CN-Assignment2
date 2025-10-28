#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import os

class NetworkTopo(Topo):
    # (Topology definition is the same as Task A)
    def build(self):
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        dns = self.addHost('dns', ip='10.0.0.5/24')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        link_params = {'bw': 100}
        self.addLink(h1, s1, delay='2ms', **link_params)
        self.addLink(h2, s2, delay='2ms', **link_params)
        self.addLink(h3, s3, delay='2ms', **link_params)
        self.addLink(h4, s4, delay='2ms', **link_params)
        self.addLink(dns, s2, delay='1ms', **link_params)
        self.addLink(s1, s2, delay='5ms', **link_params)
        self.addLink(s2, s3, delay='8ms', **link_params)
        self.addLink(s3, s4, delay='10ms', **link_params)

def start_custom_server(dns_host):
    """Starts the custom TCP server on the dns host."""
    info(f"*** Starting Custom TCP server on {dns_host.name}...\n")
    server_script = os.path.abspath('custom_tcp_server.py')
    dns_host.cmd(f'python3 {server_script} &> server_output.log &')
    time.sleep(2) # Give the server a moment to start
    info("✅ Custom TCP server started.\n")

def run_custom_clients(hosts, dns_server_ip):
    """Runs the custom_tcp_client.py on each host."""
    client_script = os.path.abspath('custom_tcp_client.py')
    
    for h in hosts:
        info(f"*** Running client on {h.name} ***\n")
        # Run the client and wait for it to complete
        h.cmd(f'python3 {client_script} {h.name} {dns_server_ip}')
        info(f"*** Client on {h.name} finished ***\n")

def run_simulation():
    """Create network, run tests, and stop."""
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    
    # NOTE: NO NAT IS NEEDED here because your server doesn't
    # need to contact the outside internet.
    
    net.start()
    info("✅ Network started successfully.\n")

    dns_server = net.get('dns')
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]

    # 1. Start your server on 10.0.0.5
    start_custom_server(dns_server)

    # 2. Run the clients on H1-H4
    run_custom_clients(hosts, dns_server.IP())

    # 3. Stop the server
    dns_server.cmd('kill %python3')
    
    net.stop()
    info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    run_simulation()
