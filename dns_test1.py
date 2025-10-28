from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

class NetworkTopo(Topo):
    """
    A custom topology for the assignment.
    """
    def build(self):
        # (Topology definition as in Task A)
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


def configure_custom_resolver():
    """
    Starts the network, configures all hosts to use 10.0.0.5
    as the default DNS resolver, and verifies the change.
    """
    topo = NetworkTopo()
    net = Mininet(topo=topo, link=TCLink, controller=OVSController)
    net.start()
    
    info("✅ Network started successfully.\n")
    
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
    resolver_ip = net.get('dns').IP() # This is 10.0.0.5

    info(f"--- Configuring hosts to use {resolver_ip} as default resolver ---\n")

    for h in hosts:
        # This command overwrites the /etc/resolv.conf file
        h.cmd(f'echo "nameserver {resolver_ip}" > /etc/resolv.conf')
        info(f"Configured {h.name}\n")

    info("\n--- Verification Step (Task C) ---\n")
    info("Reading /etc/resolv.conf from host h1:\n")
    
    # Run 'cat' on h1 to show the file contents
    h1 = net.get('h1')
    verification_output = h1.cmd('cat /etc/resolv.conf')
    
    # Print the output for the report
    print(f"h1$ cat /etc/resolv.conf\n{verification_output}")

    if resolver_ip in verification_output:
        info("✅ Success: Host h1 is correctly configured.\n")
    else:
        info("❌ Failure: Host h1 configuration is incorrect.\n")

    info("Configuration complete. Starting Mininet CLI.\n")
    info("You can type 'h1 ping h4' or 'exit' to quit.\n")
    CLI(net)

    net.stop()
    info("🛑 Simulation finished.\n")

if __name__ == '__main__':
    setLogLevel('info')
    configure_custom_resolver()
