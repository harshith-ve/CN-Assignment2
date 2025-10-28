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
    """
    A custom topology for the assignment.
    """
    def build(self):
        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        dns = self.addHost('dns', ip='10.0.0.5/24') # Host exists but is not used as a server in this task

        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Define link parameters
        link_params = {'bw': 100}

        # Add links (Host to Switch)
        self.addLink(h1, s1, delay='2ms', **link_params)
        self.addLink(h2, s2, delay='2ms', **link_params)
        self.addLink(h3, s3, delay='2ms', **link_params)
        self.addLink(h4, s4, delay='2ms', **link_params)
        self.addLink(dns, s2, delay='1ms', **link_params)

        # Add links (Switch to Switch)
        self.addLink(s1, s2, delay='5ms', **link_params)
        self.addLink(s2, s3, delay='8ms', **link_params)
        self.addLink(s3, s4, delay='10ms', **link_params)


def run_dns_queries_default(host):
    """
    Reads queries from a file and measures performance using the
    host's DEFAULT resolver (i.e., the computer's system resolver).
    """
    query_file = f"queries{host.name[1:]}.txt"
    info(f"--- Running queries for {host.name} from {query_file} (using default resolver) ---\n")

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
        #
        # --- THIS IS THE KEY CHANGE FOR TASK B ---
        # We run 'dig' without specifying a server (@10.0.0.5).
        # This forces 'dig' to use the default resolver configured
        # in the host's /etc/resolv.conf, which Mininet inherits
        # from the machine running the simulation.
        #
        cmd_result = host.cmd(f'dig {domain}')
        
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


def run_task_b_simulation():
    """Create network, run DNS tests, and stop."""
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    
    # Enable Internet connectivity for hosts
    nat = net.addNAT()
    nat.configDefault()
    
    net.start()
    info("✅ Network started successfully with NAT enabled.\a\n")

    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
    info("Configuring default nameservers for hosts...\n")
    for h in hosts:
        h.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
        info(f"Set nameserver for {h.name}\n")
    # ---------------------------
    for h in hosts:
        run_dns_queries_default(h) # This function is unchanged

    net.stop()
    info("🛑 Simulation finished.\n")


if __name__ == '__main__':
    setLogLevel('info')
    run_task_b_simulation()


