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
    # (Topology definition remains unchanged)
    def build(self):
        # ... same topology code as before ...
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
    info(f"*** Starting DNS server on {dns_host.name}...\n")
    hosts_path = os.path.abspath('hosts.conf')
    dns_host.cmd(f'dnsmasq --no-daemon --address=/#/127.0.0.1 --addn-hosts={hosts_path} &')
    time.sleep(1)

# NEW FUNCTION to update DNS config
def update_host_resolvers(hosts, dns_server_ip):
    info(f"*** Configuring hosts to use DNS server at {dns_server_ip}...\n")
    for host in hosts:
        # Overwrite the resolv.conf file
        host.cmd(f'echo "nameserver {dns_server_ip}" > /etc/resolv.conf')

# MODIFIED FUNCTION for running queries
def run_dns_queries(host): # No longer needs dns_server_ip passed in
    query_file = f"queries{host.name[1:]}.txt"
    info(f"--- Running queries for {host.name} from {query_file} ---\n")
    # ... (file reading logic is the same) ...
    try:
        with open(query_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        info(f"⚠️  Could not find {query_file}. Skipping host {host.name}.\n")
        return

    latencies, success_count, fail_count = [], 0, 0
    start_time = time.time()
    for domain in queries:
        # MODIFICATION: The 'dig' command now uses the system resolver
        # instead of explicitly pointing to the server with '@'.
        cmd_result = host.cmd(f'dig {domain}')
        
        if "status: NOERROR" in cmd_result:
            success_count += 1
            match = re.search(r"Query time: (\d+) msec", cmd_result)
            if match:
                latencies.append(int(match.group(1)))
        else:
            fail_count += 1
    # ... (calculation and printing logic is the same) ...
    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    throughput = success_count / total_time if total_time > 0 else 0
    print(f"Results for {host.name}:")
    print(f"  ✅ Successful Resolutions: {success_count}")
    print(f"  ❌ Failed Resolutions....: {fail_count}")
    print(f"  ⏱️  Average Lookup Latency: {avg_latency:.2f} ms")
    print(f"  🚀 Average Throughput....: {throughput:.2f} QPS\n")


def run_simulation():
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    net.start()

    dns_server = net.get('dns')
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
    
    # Run the new configuration function
    update_host_resolvers(hosts, dns_server.IP())

    # --- Verification Step ---
    info("*** Verifying DNS configuration for h1...\n")
    config_output = hosts[0].cmd('cat /etc/resolv.conf')
    info(f"h1's /etc/resolv.conf now contains:\n{config_output.strip()}\n")
    # --- End Verification ---

    start_dns_server(dns_server)

    for h in hosts:
        run_dns_queries(h)

    net.stop()
    info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    run_simulation()