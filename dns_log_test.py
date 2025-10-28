#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import re
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

def start_dns_server(dns_host):
    """Starts the custom MULTI-THREADED Python DNS resolver."""
    info(f"*** Starting DNS server on {dns_host.name}...\n")
    
    # --- THIS IS THE CHANGE ---
    # We are running the new multi-threaded server script
    resolver_script = os.path.abspath('custom_resolver_multithreaded.py')
    
    dns_host.cmd(f'python3 {resolver_script} &> dns_server_output.log &')
    time.sleep(2) # Give the server a moment to start
    info("✅ DNS server started.\n")

def run_dns_queries(host, dns_server_ip):
    """
    Reads queries from a file and measures performance SERIALLY.
    """
    query_file = f"queries{host.name[1:]}.txt"
    info(f"--- Running queries for {host.name} from {query_file} ---\n")

    try:
        with open(query_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        info(f"⚠️  Could not find {query_file}. Skipping host {host.name}.\n")
        return

    latencies = []
    success_count = 0
    fail_count = 0
    start_time = time.time()

    # The client script still runs queries serially.
    # host.cmd() is a blocking call.
    for i, domain in enumerate(queries):
        info(f"  {host.name} querying ({i+1}/{len(queries)}): {domain[:40]} ...")
        
        cmd_result = host.cmd(f'dig @{dns_server_ip} {domain}')
        
        if "status: NOERROR" in cmd_result:
            success_count += 1
            info("OK\n")
            match = re.search(r"Query time: (\d+) msec", cmd_result)
            if match:
                latencies.append(int(match.group(1)))
        else:
            fail_count += 1
            info("FAIL\n")

    end_time = time.time()
    total_time = end_time - start_time

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    throughput = success_count / total_time if total_time > 0 else 0

    print(f"\nResults for {host.name}:")
    print(f"  ✅ Successful Resolutions: {success_count}")
    print(f"  ❌ Failed Resolutions....: {fail_count}")
    print(f"  ⏱️  Average Lookup Latency: {avg_latency:.2f} ms")
    print(f"  🚀 Average Throughput....: {throughput:.2f} QPS\n")


def run_simulation():
    """Create network, run DNS tests, and stop."""
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    
    # Add NAT so the 'dns' host can reach the internet (root servers)
    net.addNAT().configDefault()
    
    net.start()
    info("✅ Network started successfully.\n")

    dns_server = net.get('dns')
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]

    start_dns_server(dns_server)

    for h in hosts:
        h.cmd(f'echo "nameserver {dns_server.IP()}" > /etc/resolv.conf')

    for h in hosts:
        run_dns_queries(h, dns_server.IP())

    dns_server.cmd('kill %python3')
    net.stop()
    info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    run_simulation()
