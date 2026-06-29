import simpy
import random
import pandas as pd
import numpy as np
import os
import time

# Set random seeds for reproducibility across runs
random.seed(42)
np.random.seed(42)

# --- SIMULATION CONFIGURATION ---
MEDIA_PARAMS = {
    'Fiber': {
        'bandwidth': 1000 * 1e6,  # 1 Gbps
        'prop_delay': 0.0001,     # 0.1 ms (100 microseconds)
        'ber': 1e-9,              # Very low Bit Error Rate
        'physical_mtu': 9000,     # Supports jumbo frames natively
        'overhead_delay': 0.0     # No fragmentation overhead
    },
    'Copper': {
        'bandwidth': 100 * 1e6,   # 100 Mbps
        'prop_delay': 0.001,      # 1.0 ms
        'ber': 1e-7,              # Moderate Bit Error Rate
        'physical_mtu': 1500,     # Standard Ethernet MTU
        'overhead_delay': 0.00001 # 10 microseconds inter-fragment gap
    },
    'Wireless': {
        'bandwidth': 54 * 1e6,    # 54 Mbps (e.g., 802.11g)
        'prop_delay': 0.005,      # 5.0 ms
        'ber': 1e-5,              # High Bit Error Rate (interference/fading)
        'physical_mtu': 1500,     # Standard Wi-Fi MTU
        'overhead_delay': 0.0001  # 100 microseconds (SIFS + ACK + Backoff overhead)
    }
}

MTUS = [500, 1500, 9000]

TRAFFIC_LOADS = {
    'Low': 0.20,      # 20% of link capacity
    'Medium': 0.50,   # 50% of link capacity
    'High': 0.80      # 80% of link capacity
}

FOREGROUND_RATE_BPS = 2 * 1e6    # 2 Mbps probe traffic
BUFFER_MAX_BYTES = 500 * 1024     # 500 KB buffer size
SIM_DURATION = 10.0               # 10 seconds of simulated time
WARMUP_TIME = 1.0                 # 1 second warmup (ignore statistics)

# --- CLASS DEFINITIONS ---

class Packet:
    """Represents a network packet traveling through the system."""
    def __init__(self, packet_id, size_bytes, creation_time, is_background=False):
        self.id = packet_id
        self.size = size_bytes
        self.creation_time = creation_time
        self.is_background = is_background

class Link:
    """Represents the physical transmission medium and transmitter queue."""
    def __init__(self, env, bandwidth, prop_delay, ber, physical_mtu, overhead_delay, buffer_max_bytes):
        self.env = env
        self.bandwidth = bandwidth
        self.prop_delay = prop_delay
        self.ber = ber
        self.physical_mtu = physical_mtu
        self.overhead_delay = overhead_delay
        self.buffer_max_bytes = buffer_max_bytes
        
        self.current_buffer_bytes = 0
        self.tx_resource = simpy.Resource(env, capacity=1)

class Receiver:
    """Collects and calculates performance metrics for foreground traffic."""
    def __init__(self, warmup_time):
        self.warmup_time = warmup_time
        self.packets_sent = 0
        self.packets_received = 0
        self.delays = []
        self.drop_counts = {
            'Buffer Overflow': 0,
            'Channel Error': 0
        }
        
    def record_sent(self, packet):
        if packet.creation_time >= self.warmup_time:
            self.packets_sent += 1
            
    def record_success(self, packet, arrival_time):
        if packet.creation_time >= self.warmup_time:
            self.packets_received += 1
            delay = (arrival_time - packet.creation_time) * 1000.0  # Convert to ms
            self.delays.append(delay)
            
    def record_drop(self, packet, reason):
        if packet.creation_time >= self.warmup_time:
            self.drop_counts[reason] = self.drop_counts.get(reason, 0) + 1

# --- HELPER FUNCTIONS ---

def calculate_tx_details(size, physical_mtu, bandwidth, overhead_delay, ber):
    """
    Calculates transmission time and packet success probability.
    Applies fragmentation if the packet size exceeds the medium's physical MTU.
    """
    header_overhead = 40  # IP + MAC headers (bytes)
    
    if size <= physical_mtu:
        # No fragmentation needed
        total_size_bits = size * 8
        total_tx_time = total_size_bits / bandwidth
        # Probability that all bits are transmitted without error
        p_success = (1.0 - ber) ** total_size_bits
    else:
        # Fragmentation required
        num_frags = int(np.ceil(size / physical_mtu))
        frag_sizes = []
        remaining = size
        
        for _ in range(num_frags):
            frag_payload = min(physical_mtu, remaining)
            frag_sizes.append(frag_payload + header_overhead)
            remaining -= frag_payload
            
        # Total transmission time is the sum of fragment transmission times
        # plus the inter-fragment gap/overhead delays
        total_tx_time = sum((fs * 8) / bandwidth for fs in frag_sizes) + (num_frags - 1) * overhead_delay
        
        # Packet is successful only if ALL fragments are received successfully
        p_success = 1.0
        for fs in frag_sizes:
            p_success *= (1.0 - ber) ** (fs * 8)
            
    return total_tx_time, p_success

def packet_transmit(env, packet, link, receiver):
    """Simulates the queuing, transmission, and propagation of a single packet."""
    # 1. Queue Admission Control (Buffer Check)
    if link.current_buffer_bytes + packet.size > link.buffer_max_bytes:
        if not packet.is_background:
            receiver.record_drop(packet, 'Buffer Overflow')
        return
        
    # 2. Enter Queue
    link.current_buffer_bytes += packet.size
    
    # Request transmitter resource (FIFO queueing)
    with link.tx_resource.request() as req:
        yield req
        
        # Packet starts transmission, leaves the queue buffer
        link.current_buffer_bytes -= packet.size
        
        # Calculate transmission time and transmission success probability
        tx_time, p_success = calculate_tx_details(
            packet.size, link.physical_mtu, link.bandwidth, link.overhead_delay, link.ber
        )
        
        yield env.timeout(tx_time)
        
    # 3. Propagation delay across the physical medium
    yield env.timeout(link.prop_delay)
    
    # 4. Receiver processing (only analyze foreground probe traffic)
    if not packet.is_background:
        # Check for packet loss due to bit errors (channel noise)
        if random.random() < p_success:
            receiver.record_success(packet, env.now)
        else:
            receiver.record_drop(packet, 'Channel Error')

# --- GENERATORS ---

def foreground_generator(env, link, receiver, mtu, rate_bps):
    """Generates foreground (probe) traffic at a constant bit rate."""
    packet_id = 0
    interval = (mtu * 8) / rate_bps
    while True:
        pkt = Packet(packet_id, mtu, env.now, is_background=False)
        receiver.record_sent(pkt)
        env.process(packet_transmit(env, pkt, link, receiver))
        packet_id += 1
        yield env.timeout(interval)

def background_generator(env, link, receiver, mtu, load_fraction):
    """Generates background traffic modeled as a Poisson process (exponential inter-arrival)."""
    packet_id = 0
    # Background packet size is uniformly distributed between 64 bytes and the current MTU
    avg_size = (64 + mtu) / 2
    
    # Calculate required packet rate to achieve the desired background load fraction
    target_throughput_bps = link.bandwidth * load_fraction
    lambda_bg = target_throughput_bps / (8 * avg_size)
    mean_interval = 1.0 / lambda_bg
    
    while True:
        bg_size = random.randint(64, mtu)
        pkt = Packet(packet_id, bg_size, env.now, is_background=True)
        env.process(packet_transmit(env, pkt, link, receiver))
        packet_id += 1
        
        # Poisson process: inter-arrival times are exponentially distributed
        interval = random.expovariate(1.0 / mean_interval)
        yield env.timeout(interval)

# --- EXPERIMENT RUNNER ---

def calculate_jitter(delays):
    """Calculates jitter as the average absolute difference between consecutive delays (RFC 3550)."""
    if len(delays) < 2:
        return 0.0
    diffs = [abs(delays[i] - delays[i-1]) for i in range(1, len(delays))]
    return sum(diffs) / len(diffs)

def run_single_scenario(medium_name, mtu, load_name, sim_duration=10.0, warmup_time=1.0):
    """Runs a single simulation scenario with specific input parameters."""
    # Reset random seeds for each scenario to ensure fair, deterministic traffic patterns
    random.seed(42)
    np.random.seed(42)
    
    env = simpy.Environment()
    m_params = MEDIA_PARAMS[medium_name]
    load_fraction = TRAFFIC_LOADS[load_name]
    
    # Initialize link and receiver
    link = Link(
        env=env,
        bandwidth=m_params['bandwidth'],
        prop_delay=m_params['prop_delay'],
        ber=m_params['ber'],
        physical_mtu=m_params['physical_mtu'],
        overhead_delay=m_params['overhead_delay'],
        buffer_max_bytes=BUFFER_MAX_BYTES
    )
    receiver = Receiver(warmup_time=warmup_time)
    
    # Start traffic processes
    env.process(foreground_generator(env, link, receiver, mtu, FOREGROUND_RATE_BPS))
    env.process(background_generator(env, link, receiver, mtu, load_fraction))
    
    # Run the simulation
    env.run(until=sim_duration)
    
    # Process results
    avg_delay = np.mean(receiver.delays) if receiver.delays else 0.0
    jitter = calculate_jitter(receiver.delays)
    pdr = (receiver.packets_received / receiver.packets_sent) * 100.0 if receiver.packets_sent > 0 else 0.0
    
    return {
        'Medium': medium_name,
        'MTU': mtu,
        'TrafficLoad': load_name,
        'AvgDelay_ms': round(avg_delay, 4),
        'Jitter_ms': round(jitter, 4),
        'PacketDeliveryRatio_Percent': round(pdr, 2),
        'PacketsSent': receiver.packets_sent,
        'PacketsReceived': receiver.packets_received,
        'BufferOverflowDrops': receiver.drop_counts.get('Buffer Overflow', 0),
        'ChannelErrorDrops': receiver.drop_counts.get('Channel Error', 0)
    }

def main():
    print("=" * 80)
    print("STARTING HETEROGENEOUS NETWORK TOPOLOGY SIMULATION")
    print("=" * 80)
    
    results = []
    
    # Full Factorial Iteration: 3 Media * 3 MTUs * 3 Traffic Loads = 27 Scenarios
    scenario_count = 0
    total_scenarios = len(MEDIA_PARAMS) * len(MTUS) * len(TRAFFIC_LOADS)
    
    for medium in MEDIA_PARAMS.keys():
        for mtu in MTUS:
            for load in TRAFFIC_LOADS.keys():
                scenario_count += 1
                print(f"Running scenario {scenario_count}/{total_scenarios}: "
                      f"Medium={medium:<8} | MTU={mtu:<4} | Load={load:<6}...", end="", flush=True)
                
                start_time = time.time()
                res = run_single_scenario(medium, mtu, load, SIM_DURATION, WARMUP_TIME)
                elapsed = time.time() - start_time
                
                results.append(res)
                print(f" Done ({elapsed:.3f}s) | PDR: {res['PacketDeliveryRatio_Percent']}% | Delay: {res['AvgDelay_ms']} ms")
                
    # Create DataFrame and export to CSV
    df = pd.DataFrame(results)
    output_filename = "simulation_results.csv"
    df.to_csv(output_filename, index=False)
    
    print("\n" + "=" * 80)
    print(f"SIMULATION COMPLETE. Results successfully saved to: {os.path.abspath(output_filename)}")
    print("=" * 80)
    
    # Print a summary pivot table for quick inspection
    print("\nSummary of Results (Average Packet Delivery Ratio % by Medium and MTU):")
    piv_pdr = df.pivot_table(values='PacketDeliveryRatio_Percent', index='Medium', columns='MTU', aggfunc='mean')
    print(piv_pdr)
    
    print("\nSummary of Results (Average Delay ms by Medium and Traffic Load):")
    piv_delay = df.pivot_table(values='AvgDelay_ms', index='Medium', columns='TrafficLoad', aggfunc='mean')
    # Reorder columns for logical progression
    piv_delay = piv_delay[['Low', 'Medium', 'High']]
    print(piv_delay)
    print("=" * 80)

if __name__ == "__main__":
    main()
