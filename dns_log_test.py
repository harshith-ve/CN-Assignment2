#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import re
import os
import csv
import sys

# NEW: Import plotting libraries
try:
    import matplotlib.pyplot as plt
    import pandas as pd
except ImportError:
    info("Error: 'matplotlib' and 'pandas' libraries are required.\n")
    info("Please run: pip install matplotlib pandas\n")
    sys.exit(1)

# Limit queries
MAX_QUERIES_PER_HOST = 500

# NEW: Global list to store h1 plot data
h1_plot_results = []

# --- Topology Class (Unchanged) ---
class NetworkTopo(Topo):
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

# --- DNS Server Function (Unchanged) ---
def start_dns_server(dns_host):
    info(f"*** Starting DNS server on {dns_host.name} with logging...\n")
    hosts_path = os.path.abspath('hosts.conf')
    log_path = '/tmp/dns.log'
    dns_host.cmd(f'touch {log_path} && chmod 666 {log_path}')
    dns_host.cmd(
        f'dnsmasq --no-daemon '
        f'--log-queries '
        f'--log-facility={log_path} '
        f'--address=/#/127.0.0.1 '
        f'--addn-hosts={hosts_path} &'
    )
    time.sleep(1)

# --- Host Resolver Config (Unchanged) ---
def update_host_resolvers(hosts, dns_server_ip):
    info(f"*** Configuring hosts to use DNS server at {dns_server_ip}...\n")
    for host in hosts:
        host.cmd(f'echo "nameserver {dns_server_ip}" > /etc/resolv.conf')

# --- NEW: Function to get known domains for HIT/MISS status ---
def get_known_domains():
    known_domains = set()
    try:
        with open('hosts.conf', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) > 1:
                        # Add all aliases for the IP
                        for domain in parts[1:]:
                            known_domains.add(domain)
    except FileNotFoundError:
        info("Warning: hosts.conf not found. All queries will be 'MISS'.\n")
    return known_domains

# --- Run Queries Function (MODIFIED to capture h1 data) ---
def run_dns_queries(host, known_domains):
    query_file = f"queries{host.name[1:]}.txt"
    info(f"--- Running queries for {host.name} from {query_file} ---\n")
    try:
        with open(query_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        info(f"⚠️  Could not find {query_file}. Skipping host {host.name}.\n")
        return

    # Limit queries
    if len(queries) > MAX_QUERIES_PER_HOST:
        info(f"  (Found {len(queries)} queries, limiting to {MAX_QUERIES_PER_HOST})\n")
        queries = queries[:MAX_QUERIES_PER_HOST]
    elif len(queries) == 0:
        info(f"  (File is empty, skipping)\n")
        return

    latencies, success_count, fail_count = [], 0, 0
    start_time = time.time()
    
    for i, domain in enumerate(queries):
        print(f"  {host.name} querying ({i+1}/{len(queries)}): {domain} ... ", end='', flush=True)
        
        # Fixed dig command
        cmd_result = host.cmd(f'dig +time=3 +tries=1 {domain}') 
        
        if "status: NOERROR" in cmd_result:
            success_count += 1
            match = re.search(r"Query time: (\d+) msec", cmd_result)
            latency = int(match.group(1)) if match else 0
            latencies.append(latency)
            print("OK")

            # NEW: Capture data for h1's first 10 queries
            if host.name == 'h1' and i < 10:
                status = "HIT" if domain in known_domains else "MISS"
                servers_visited = 0 if status == "HIT" else 1
                h1_plot_results.append((domain, latency, status, servers_visited))
        
        else:
            fail_count += 1
            print("FAIL")
            # NEW: Capture failed data for h1's first 10 queries
            if host.name == 'h1' and i < 10:
                h1_plot_results.append((domain, 0, "FAIL", 0))

    # (Rest of the function is unchanged)
    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    throughput = success_count / total_time if total_time > 0 else 0

    print(f"\nResults for {host.name}:")
    print(f"  ✅ Successful Resolutions: {success_count}")
    print(f"  ❌ Failed Resolutions....: {fail_count}")
    print(f"  ⏱️  Average Lookup Latency: {avg_latency:.2f} ms")
    print(f"  🚀 Average Throughput....: {throughput:.2f} QPS\n")

# --- Log Parsing Function (Unchanged) ---
def parse_log_to_csv(log_contents, csv_filename):
    info(f"*** Parsing log and saving to {csv_filename} ...\n")
    log_pattern = re.compile(
        r"(\w+\s+\d+\s+[\d:]+)\s+dnsmasq\[\d+\]:\s+"
        r"([\w-]+)\[?([\w\.]*)\]?\s+"
        r"([\w\.-]+)\s+"
        r"(from|to|is)\s+([\w\.-]+)"
    )
    header = ['Timestamp','DomainName','ClientIP','EventType','UpstreamServer','Response']
    
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for line in log_contents.splitlines():
            match = log_pattern.search(line)
            if not match: continue
            timestamp, event, event_type, domain, preposition, target = match.groups()
            client_ip, upstream_server, response = '', '', ''
            if event == 'query':
                event_type = f'query[{event_type}]'
                client_ip = target
            elif event == 'forwarded':
                upstream_server = target
            elif event == 'reply':
                response = target
            elif event == 'config':
                event_type = 'HIT (config)'
                response = target
            writer.writerow([timestamp, domain, client_ip, event_type, upstream_server, response])

# --- NEW: Plotting Function ---
def generate_plots(results_data):
    """
    Generates and saves plots for h1's first 10 queries.
    """
    if not results_data:
        info("No plot data for h1 was collected. Skipping plots.\n")
        return

    info("*** Generating plots for h1 (first 10 queries) ***\n")
    
    # Create a DataFrame
    df = pd.DataFrame(
        results_data,
        columns=['Domain', 'Latency(ms)', 'Status', 'ServersVisited']
    )
    # Add a short label for the plot
    df['QueryLabel'] = [f"{i+1}_{domain}" for i, domain in enumerate(df['Domain'])]

    # --- Plot 1: Latency per Query ---
    plt.figure(figsize=(12, 7))
    colors = ['#4CAF50' if s == 'HIT' else ('#F44336' if s == 'MISS' else '#9E9E9E') for s in df['Status']]
    bars = plt.bar(df['QueryLabel'], df['Latency(ms)'], color=colors)
    plt.xlabel('DNS Query (Query#_DomainName)')
    plt.ylabel('Latency (ms)')
    plt.title('Latency per Query (h1, First 10)')
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.tight_layout()
    # Custom legend
    hit_patch = plt.Rectangle((0,0),1,1, color='#4CAF50')
    miss_patch = plt.Rectangle((0,0),1,1, color='#F44336')
    fail_patch = plt.Rectangle((0,0),1,1, color='#9E9E9E')
    plt.legend([hit_patch, miss_patch, fail_patch], ['HIT (Local)', 'MISS (Forwarded)', 'FAIL'])
    plt.savefig('h1_latency_plot.png')
    info("✅ Latency plot saved as 'h1_latency_plot.png'\n")
    

    # --- Plot 2: Total Number of DNS Servers Visited ---
    # (0 for HIT, 1 for MISS)
    plt.figure(figsize=(12, 7))
    bars = plt.bar(df['QueryLabel'], df['ServersVisited'], color=colors)
    plt.xlabel('DNS Query (Query#_DomainName)')
    plt.ylabel('Number of External DNS Servers Visited')
    plt.title('External DNS Servers Visited per Query (h1, First 10)')
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks([0, 1]) # Set y-axis ticks to only 0 and 1
    plt.tight_layout()
    plt.legend([hit_patch, miss_patch, fail_patch], ['0 Servers (HIT)', '1 Server (MISS)', 'FAIL'])
    plt.savefig('h1_servers_visited_plot.png')
    info("✅ Servers visited plot saved as 'h1_servers_visited_plot.png'\n")
    

# --- Simulation Runner (MODIFIED) ---
def run_simulation():
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)

    try:
        net.start()
        dns_server = net.get('dns')
        hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
        
        update_host_resolvers(hosts, dns_server.IP())
        start_dns_server(dns_server)

        # NEW: Get known domains before running queries
        known_domains = get_known_domains()

        # Pass known_domains to the query function
        for h in hosts:
            run_dns_queries(h, known_domains)
        
        # --- Log Parsing ---
        info("\n*** Retrieving DNS server log file ***\n")
        log_contents = dns_server.cmd('cat /tmp/dns.log')
        csv_filename = 'dns_resolver_log.csv'
        parse_log_to_csv(log_contents, csv_filename)
        info(f"✅ DNS resolver log successfully saved to {csv_filename}\n")
        
        # --- Plot Generation ---
        # The h1_plot_results list was populated during run_dns_queries
        generate_plots(h1_plot_results)

    except KeyboardInterrupt:
        info("\n🛑 User interrupted, stopping network.\n")
    except Exception as e:
        info(f"\n❌ An error occurred: {e}\n")
    finally:
        info("--- Cleaning up and stopping Mininet ---\n")
        if net:
            net.stop()
        info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    run_simulation()