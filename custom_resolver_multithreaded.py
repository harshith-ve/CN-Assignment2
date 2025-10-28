
#!/usr/bin/python3
import socket
import socketserver
import logging
from datetime import datetime
import time
from dnslib import DNSRecord, DNSHeader, RR, QTYPE, RCODE

# --- Root DNS Servers ---
ROOT_SERVERS = ['198.41.0.4'] # A-Root

# --- Setup Logging (as required by Task D) ---
def setup_logging():
    """Configures the logger to write to resolver.log."""
    logger = logging.getLogger('DNSResolver')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('resolver.log', mode='w') # Overwrite log
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(fh)
    return logger

logger = setup_logging()

class DNSRequestHandler(socketserver.BaseRequestHandler):
    """
    Handles incoming DNS queries via UDP.
    Each request will be handled in its own thread by the ThreadingUDPServer.
    """
    
    def send_response(self, response_packet, client_address, client_socket):
        """Sends a DNS response packet back to the client."""
        client_socket.sendto(response_packet.pack(), client_address)

    def resolve_iterative(self, query_domain, log_data):
        """
        Performs iterative DNS resolution.
        """
        current_server_ip = ROOT_SERVERS[0]
        log_data["resolution_mode"] = "iterative"
        
        for i in range(10): # Limit to 10 hops
            if not current_server_ip:
                logger.warning(f"Resolution failed for {query_domain}: No server to query.")
                return None

            query = DNSRecord.parse(DNSRecord.question(query_domain).pack())
            
            if i == 0: log_data["step"] = "Root"
            log_data["server_ip"] = current_server_ip
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2.0)
                
                start_rtt = time.time()
                sock.sendto(query.pack(), (current_server_ip, 53))
                response_data, _ = sock.recvfrom(4096)
                end_rtt = time.time()
                
                log_data["rtt"] = (end_rtt - start_rtt) * 1000 # RTT in ms
                response = DNSRecord.parse(response_data)
                
            except socket.timeout:
                log_data["response"] = "TIMEOUT"
                logger.info(str(log_data))
                current_server_ip = None
                continue
            except Exception as e:
                logger.error(f"Error querying {current_server_ip}: {e}")
                current_server_ip = None
                continue
            
            # --- Process Response ---
            if response.header.rcode == RCODE.NOERROR:
                if response.rr: # Answer section
                    for rr in response.rr:
                        if rr.rtype == QTYPE.A:
                            log_data["step"] = "Authoritative"
                            log_data["response"] = f"RESPONSE: A={str(rr.rdata)}"
                            logger.info(str(log_data))
                            return response # Found it!
                
                if response.auth: # Authority section (Referral)
                    log_data["response"] = "REFERRAL"
                    new_ns_domain = str(response.auth[0].rdata)
                    new_server_ip = None
                    
                    if response.ar: # Additional section
                        for rr in response.ar:
                            if rr.rtype == QTYPE.A:
                                new_server_ip = str(rr.rdata)
                                log_data["step"] = "TLD" if "tld" in new_ns_domain else "Authoritative"
                                break
                    
                    if new_server_ip:
                        current_server_ip = new_server_ip
                    else:
                        logger.warning(f"Got referral to {new_ns_domain} but no IP (Glue).")
                        current_server_ip = None # Simplification: stop here
                
                logger.info(str(log_data))

            elif response.header.rcode == RCODE.NXDOMAIN:
                log_data["response"] = "NXDOMAIN"
                logger.info(str(log_data))
                return response # Domain doesn't exist
            else:
                log_data["response"] = f"RCODE_{response.header.rcode}"
                logger.info(str(log_data))
                return response # Other error

        return None # Failed to resolve


    def handle(self):
        client_data, client_socket = self.request
        client_address = self.client_address
        
        try:
            query = DNSRecord.parse(client_data)
            query_domain = str(query.q.qname)
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "domain": query_domain,
                "resolution_mode": "N/A", "server_ip": "N/A", "step": "N/A",
                "response": "N/A", "rtt": 0.0, "total_time": 0.0,
                "cache_status": "MISS"
            }
            
            start_total_time = time.time()
            response_packet = self.resolve_iterative(query_domain, log_data)
            end_total_time = time.time()
            
            log_data["total_time"] = (end_total_time - start_total_time) * 1000 # Total ms
            
            if response_packet:
                response_packet.header.qr = 1
                response_packet.header.id = query.header.id
                self.send_response(response_packet, client_address, client_socket)
            else:
                response_fail = query.reply()
                response_fail.header.rcode = RCODE.SERVFAIL
                self.send_response(response_fail, client_address, client_socket)

            log_data["step"] = "FINAL"
            logger.info(str(log_data))

        except Exception as e:
            print(f"Error handling request: {e}")

if __name__ == "__main__":
    print("Starting MULTI-THREADED DNS resolver on 10.0.0.5:53...")
    
    #
    # --- THIS IS THE FIX ---
    # We are using ThreadingUDPServer instead of UDPServer.
    # This creates a new thread for every single request.
    #
    with socketserver.ThreadingUDPServer(("10.0.0.5", 53), DNSRequestHandler) as server:
        server.serve_forever()
