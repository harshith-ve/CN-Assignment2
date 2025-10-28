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
    # (The topology definition is the same as the previous script)
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
    """Starts a dnsmasq server on the specified host."""
    info(f"*** Starting DNS server on {dns_host.name}...\n")
    # Get the absolute path for the hosts file
    hosts_path = os.path.abspath('hosts.conf')
    dns_host.cmd(f'dnsmasq --no-daemon --address=/#/127.0.0.1 --addn-hosts={hosts_path} &')
    time.sleep(1) # Give the server a moment to start

def run_dns_queries(host, dns_server_ip):
    """Reads queries from a file and measures performance."""
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

    for domain in queries:
        # Use dig to perform the DNS lookup and get output
        cmd_result = host.cmd(f'dig @{dns_server_ip} {domain}')
        
        # Check for success (NOERROR) or failure (NXDOMAIN, etc.)
        if "status: NOERROR" in cmd_result:
            success_count += 1
            # Use regex to find the query time
            match = re.search(r"Query time: (\d+) msec", cmd_result)
            if match:
                latencies.append(int(match.group(1)))
        else:
            fail_count += 1

    end_time = time.time()
    total_time = end_time - start_time

    # --- Calculate metrics ---
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    # Throughput in Queries Per Second (QPS)
    throughput = success_count / total_time if total_time > 0 else 0

    # --- Print results ---
    print(f"Results for {host.name}:")
    print(f"  ✅ Successful Resolutions: {success_count}")
    print(f"  ❌ Failed Resolutions....: {fail_count}")
    print(f"  ⏱️  Average Lookup Latency: {avg_latency:.2f} ms")
    print(f"  🚀 Average Throughput....: {throughput:.2f} QPS\n")


def run_simulation():
    """Create network, run DNS tests, and stop."""
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    net.start()

    dns_server = net.get('dns')
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]

    start_dns_server(dns_server)

    for h in hosts:
        run_dns_queries(h, dns_server.IP())

    net.stop()
    info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    run_simulation()