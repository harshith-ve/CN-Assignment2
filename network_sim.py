#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

class NetworkTopo(Topo):
    """
    A custom topology for the assignment.
    H1-S1-S2-S3-S4-H4
         |  |  |
         H2 |  H3
            |
           DNS
    """

    def build(self):
        "Build the custom topology."

        # Add hosts with specified IP addresses
        # The /24 subnet mask is standard for these simple topologies.
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        dns = self.addHost('dns', ip='10.0.0.5/24') # This is the DNS Resolver

        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Define link parameters for clarity
        link_params = {'bw': 100} # Bandwidth is 100Mbps for all links

        # Add links between hosts and switches
        self.addLink(h1, s1, delay='2ms', **link_params)
        self.addLink(h2, s2, delay='2ms', **link_params)
        self.addLink(h3, s3, delay='2ms', **link_params)
        self.addLink(h4, s4, delay='2ms', **link_params)
        self.addLink(dns, s2, delay='1ms', **link_params)

        # Add links between switches
        self.addLink(s1, s2, delay='5ms', **link_params)
        self.addLink(s2, s3, delay='8ms', **link_params)
        self.addLink(s3, s4, delay='10ms', **link_params)


def runSimulation():
    "Create and test the network."
    topo = NetworkTopo()
    net = Mininet(
        topo=topo,
        link=TCLink,              # TCLink allows specifying delay and bandwidth
        controller=OVSController, # A simple OpenFlow controller
        autoSetMacs=True
    )

    net.start()
    info("✅ Network started successfully!\n")

    info("Testing connectivity between all nodes...\n")
    # This command pings every host from every other host.
    ping_results = net.pingAll()

    # A result of 0.0 means 0% packet loss, indicating success.
    if ping_results == 0.0:
        info("✅ All nodes are successfully connected.\n")
    else:
        info(f"⚠️ Connectivity test failed. Packet loss: {ping_results}%\n")


    # Opens the Mininet command-line interface for manual testing.
    # You can type 'h1 ping h4' or 'iperf h1 dns' here.
    CLI(net)

    net.stop()
    info("🛑 Network stopped.\n")


if __name__ == '__main__':
    # Set the logging level to 'info' to see detailed output.
    setLogLevel('info')
    runSimulation()