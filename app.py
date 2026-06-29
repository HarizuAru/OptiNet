import streamlit as st
import simpy
import random
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OptiNet - Network Topology Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR PREMIUM AESTHETICS ---
st.markdown("""
<style>
    /* Main container styling */
    .reportview-container {
        background: #0e1117;
    }
    
    /* Title and Headers */
    h1, h2, h3 {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .main-title {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        color: #9ca3af;
        font-size: 1.15rem;
        margin-bottom: 2rem;
    }
    
    /* Premium Metric Card */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
        transition: transform 0.2s, border-color 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    .metric-val {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 10px 0;
        font-family: 'Outfit', sans-serif;
    }
    
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #9ca3af;
        font-weight: 600;
    }
    
    .metric-desc {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- CORE SIMULATION ENGINE ---

MEDIA_PARAMS = {
    'Fiber': {
        'bandwidth': 1000 * 1e6,  # 1 Gbps
        'prop_delay': 0.0001,     # 0.1 ms
        'ber': 1e-9,
        'physical_mtu': 9000,
        'overhead_delay': 0.0
    },
    'Copper': {
        'bandwidth': 100 * 1e6,   # 100 Mbps
        'prop_delay': 0.001,      # 1.0 ms
        'ber': 1e-7,
        'physical_mtu': 1500,
        'overhead_delay': 0.00001 # 10 us
    },
    'Wireless': {
        'bandwidth': 54 * 1e6,    # 54 Mbps
        'prop_delay': 0.005,      # 5.0 ms
        'ber': 1e-5,
        'physical_mtu': 1500,
        'overhead_delay': 0.0001  # 100 us (SIFS + ACK)
    }
}

class Packet:
    def __init__(self, packet_id, size_bytes, creation_time, is_background=False):
        self.id = packet_id
        self.size = size_bytes
        self.creation_time = creation_time
        self.is_background = is_background

class Link:
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
        
        # To track queue occupancy over time
        self.queue_history = [(0.0, 0.0)]
        
    def update_buffer(self, bytes_change):
        self.current_buffer_bytes += bytes_change
        self.queue_history.append((self.env.now, self.current_buffer_bytes))

class Receiver:
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
            delay = (arrival_time - packet.creation_time) * 1000.0  # ms
            self.delays.append(delay)
            
    def record_drop(self, packet, reason):
        if packet.creation_time >= self.warmup_time:
            self.drop_counts[reason] = self.drop_counts.get(reason, 0) + 1

def calculate_tx_details(size, physical_mtu, bandwidth, overhead_delay, ber):
    header_overhead = 40
    if size <= physical_mtu:
        total_size_bits = size * 8
        total_tx_time = total_size_bits / bandwidth
        p_success = (1.0 - ber) ** total_size_bits
    else:
        num_frags = int(np.ceil(size / physical_mtu))
        frag_sizes = []
        remaining = size
        for _ in range(num_frags):
            frag_payload = min(physical_mtu, remaining)
            frag_sizes.append(frag_payload + header_overhead)
            remaining -= frag_payload
            
        total_tx_time = sum((fs * 8) / bandwidth for fs in frag_sizes) + (num_frags - 1) * overhead_delay
        
        p_success = 1.0
        for fs in frag_sizes:
            p_success *= (1.0 - ber) ** (fs * 8)
            
    return total_tx_time, p_success

def packet_transmit(env, packet, link, receiver):
    # 1. Buffer Admission
    if link.current_buffer_bytes + packet.size > link.buffer_max_bytes:
        if not packet.is_background:
            receiver.record_drop(packet, 'Buffer Overflow')
        return
        
    # 2. Enter Queue
    link.update_buffer(packet.size)
    
    with link.tx_resource.request() as req:
        yield req
        # Start transmission, leave queue
        link.update_buffer(-packet.size)
        
        tx_time, p_success = calculate_tx_details(
            packet.size, link.physical_mtu, link.bandwidth, link.overhead_delay, link.ber
        )
        yield env.timeout(tx_time)
        
    # 3. Propagation
    yield env.timeout(link.prop_delay)
    
    # 4. Receiver processing (Foreground only)
    if not packet.is_background:
        if random.random() < p_success:
            receiver.record_success(packet, env.now)
        else:
            receiver.record_drop(packet, 'Channel Error')

def foreground_generator(env, link, receiver, mtu, rate_bps):
    packet_id = 0
    interval = (mtu * 8) / rate_bps
    while True:
        pkt = Packet(packet_id, mtu, env.now, is_background=False)
        receiver.record_sent(pkt)
        env.process(packet_transmit(env, pkt, link, receiver))
        packet_id += 1
        yield env.timeout(interval)

def background_generator(env, link, receiver, mtu, load_fraction):
    if load_fraction <= 0:
        return
        
    packet_id = 0
    avg_size = (64 + mtu) / 2
    target_throughput_bps = link.bandwidth * load_fraction
    lambda_bg = target_throughput_bps / (8 * avg_size)
    mean_interval = 1.0 / lambda_bg
    
    while True:
        bg_size = random.randint(64, mtu)
        pkt = Packet(packet_id, bg_size, env.now, is_background=True)
        env.process(packet_transmit(env, pkt, link, receiver))
        packet_id += 1
        
        interval = random.expovariate(1.0 / mean_interval)
        yield env.timeout(interval)

def calculate_jitter(delays):
    if len(delays) < 2:
        return 0.0
    diffs = [abs(delays[i] - delays[i-1]) for i in range(1, len(delays))]
    return sum(diffs) / len(diffs)

def run_simulation(medium_name, mtu, load_fraction, sim_duration, warmup_time, fg_rate_bps, buffer_max_kb):
    # Reset seeds for consistency
    random.seed(42)
    np.random.seed(42)
    
    env = simpy.Environment()
    m_params = MEDIA_PARAMS[medium_name]
    
    link = Link(
        env=env,
        bandwidth=m_params['bandwidth'],
        prop_delay=m_params['prop_delay'],
        ber=m_params['ber'],
        physical_mtu=m_params['physical_mtu'],
        overhead_delay=m_params['overhead_delay'],
        buffer_max_bytes=buffer_max_kb * 1024
    )
    
    receiver = Receiver(warmup_time=warmup_time)
    
    env.process(foreground_generator(env, link, receiver, mtu, fg_rate_bps))
    env.process(background_generator(env, link, receiver, mtu, load_fraction))
    
    env.run(until=sim_duration)
    
    # Process queue history into steps
    times, sizes = zip(*link.queue_history)
    df_queue = pd.DataFrame({
        'Time (s)': times,
        'Queue Size (KB)': [s / 1024.0 for s in sizes]
    })
    
    avg_delay = np.mean(receiver.delays) if receiver.delays else 0.0
    jitter = calculate_jitter(receiver.delays)
    pdr = (receiver.packets_received / receiver.packets_sent) * 100.0 if receiver.packets_sent > 0 else 0.0
    
    return {
        'AvgDelay_ms': avg_delay,
        'Jitter_ms': jitter,
        'PDR': pdr,
        'PacketsSent': receiver.packets_sent,
        'PacketsReceived': receiver.packets_received,
        'BufferDrops': receiver.drop_counts.get('Buffer Overflow', 0),
        'ChannelDrops': receiver.drop_counts.get('Channel Error', 0),
        'QueueDF': df_queue
    }

# --- GUI LAYOUT ---

st.markdown('<div class="main-title">⚡ OptiNet Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Heterogeneous Network Topology & Statistical Experimentation Software</div>', unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("🛠️ Global Configuration")

sim_duration = st.sidebar.slider("Simulation Duration (seconds)", 5, 30, 10, help="Total simulated time for each run.")
warmup_time = st.sidebar.slider("Warmup Time (seconds)", 1, 5, 1, help="Transient period discarded from statistics.")
fg_rate_mbps = st.sidebar.slider("Probe Flow Rate (Mbps)", 0.5, 10.0, 2.0, step=0.5, help="Bandwidth consumed by the foreground probe flow.")
buffer_max_kb = st.sidebar.number_input("Transmitter Buffer Size (KB)", min_value=10, max_value=5000, value=500, step=50, help="Max queue capacity in Kilobytes.")

fg_rate_bps = fg_rate_mbps * 1e6

# --- TABS CREATION ---
tab1, tab2, tab3 = st.tabs(["🎯 Single Scenario Simulator", "📊 Full Factorial Experiment", "📝 Analytical Insights & ANOVA Guide"])

# --- TAB 1: SINGLE SCENARIO ---
with tab1:
    st.subheader("Simulate a Custom Network Link")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sel_medium = st.selectbox("Transmission Medium", ['Fiber', 'Copper', 'Wireless'])
    with col2:
        sel_mtu = st.selectbox("Packet Size / MTU (Bytes)", [500, 1500, 9000], index=1)
    with col3:
        sel_load = st.slider("Background Traffic Load (%)", 0, 95, 50, step=5)
    with col4:
        st.write("") # spacing
        st.write("")
        run_btn = st.button("Run Simulation", type="primary", use_container_width=True)
        
    if run_btn or 'single_res' in st.session_state:
        if run_btn:
            with st.spinner("Simulating events..."):
                st.session_state.single_res = run_simulation(
                    sel_medium, sel_mtu, sel_load / 100.0, sim_duration, warmup_time, fg_rate_bps, buffer_max_kb
                )
                
        res = st.session_state.single_res
        
        # Display Metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            pdr_color = "#10b981" if res['PDR'] > 95 else ("#f59e0b" if res['PDR'] > 80 else "#ef4444")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Packet Delivery Ratio</div>
                <div class="metric-val" style="color: {pdr_color}">{res['PDR']:.2f}%</div>
                <div class="metric-desc">{res['PacketsReceived']} received of {res['PacketsSent']} sent</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">End-to-End Delay</div>
                <div class="metric-val" style="color: #6366f1">{res['AvgDelay_ms']:.4f} ms</div>
                <div class="metric-desc">Avg delay including queuing</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Jitter</div>
                <div class="metric-val" style="color: #a855f7">{res['Jitter_ms']:.4f} ms</div>
                <div class="metric-desc">RFC 3550 average variation</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col4:
            tot_drops = res['BufferDrops'] + res['ChannelDrops']
            drop_color = "#ef4444" if tot_drops > 0 else "#6b7280"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Packets Dropped</div>
                <div class="metric-val" style="color: {drop_color}">{tot_drops}</div>
                <div class="metric-desc">{res['BufferDrops']} Buffer | {res['ChannelDrops']} Channel</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("---")
        
        # Plot Queue occupancy over time
        st.subheader("Queue Occupancy over Time (Buffer Dynamics)")
        df_q = res['QueueDF']
        
        fig_q = px.line(
            df_q, x='Time (s)', y='Queue Size (KB)',
            title="Transmitter Buffer Occupancy (Kilobytes)",
            line_shape='hv',
            color_discrete_sequence=['#6366f1']
        )
        fig_q.add_hline(y=buffer_max_kb, line_dash="dash", line_color="#ef4444", annotation_text="Buffer Limit")
        fig_q.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#9ca3af",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", range=[0, max(buffer_max_kb * 1.1, df_q['Queue Size (KB)'].max() * 1.1)])
        )
        st.plotly_chart(fig_q, use_container_width=True)

# --- TAB 2: FULL FACTORIAL EXPERIMENT ---
with tab2:
    st.subheader("Run Full Factorial Experiment")
    st.write("Iterates through all 27 combinations of **3 Media** $\\times$ **3 MTUs** $\\times$ **3 Traffic Loads**.")
    
    run_exp_btn = st.button("Run Full Factorial Experiment (27 Runs)", type="secondary")
    
    # Load existing results if file exists, or run new
    csv_path = "simulation_results.csv"
    df_results = None
    
    if run_exp_btn:
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        results = []
        total_scenarios = len(MEDIA_PARAMS) * 3 * 3
        count = 0
        
        for medium in MEDIA_PARAMS.keys():
            for mtu in [500, 1500, 9000]:
                for load_name, load_frac in {'Low': 0.20, 'Medium': 0.50, 'High': 0.80}.items():
                    count += 1
                    status_text.write(f"Simulating Scenario {count}/{total_scenarios}: Medium={medium}, MTU={mtu}, Load={load_name}...")
                    
                    sim_res = run_simulation(
                        medium, mtu, load_frac, sim_duration, warmup_time, fg_rate_bps, buffer_max_kb
                    )
                    
                    results.append({
                        'Medium': medium,
                        'MTU': mtu,
                        'TrafficLoad': load_name,
                        'AvgDelay_ms': round(sim_res['AvgDelay_ms'], 4),
                        'Jitter_ms': round(sim_res['Jitter_ms'], 4),
                        'PacketDeliveryRatio_Percent': round(sim_res['PDR'], 2),
                        'PacketsSent': sim_res['PacketsSent'],
                        'PacketsReceived': sim_res['PacketsReceived'],
                        'BufferOverflowDrops': sim_res['BufferDrops'],
                        'ChannelErrorDrops': sim_res['ChannelDrops']
                    })
                    progress_bar.progress(count / total_scenarios)
                    
        status_text.empty()
        progress_bar.empty()
        
        df_results = pd.DataFrame(results)
        df_results.to_csv(csv_path, index=False)
        st.success("Full Factorial Experiment Completed and saved to `simulation_results.csv`!")
    elif os.path.exists(csv_path):
        df_results = pd.read_csv(csv_path)
        
    if df_results is not None:
        # Display DataFrame
        st.dataframe(df_results, use_container_width=True)
        
        # Download Button
        csv_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV for ANOVA (Minitab/SPSS)",
            data=csv_data,
            file_name="simulation_results.csv",
            mime="text/csv",
        )
        
        st.write("---")
        st.subheader("Experimental Factor Interactions & Trends")
        
        vis_col1, vis_col2 = st.columns(2)
        
        with vis_col1:
            # Interactive bar chart of PDR
            fig_pdr = px.bar(
                df_results, x='Medium', y='PacketDeliveryRatio_Percent', color='MTU',
                barmode='group', facet_col='TrafficLoad',
                title="Packet Delivery Ratio (%) by Medium, MTU, and Traffic Load",
                labels={'PacketDeliveryRatio_Percent': 'PDR (%)', 'TrafficLoad': 'Load'},
                color_continuous_scale=px.colors.sequential.Viridis
            )
            fig_pdr.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#9ca3af")
            st.plotly_chart(fig_pdr, use_container_width=True)
            
        with vis_col2:
            # Interactive line chart of Delay
            # Group by Medium and Traffic Load and average
            fig_delay = px.line(
                df_results, x='TrafficLoad', y='AvgDelay_ms', color='Medium', line_dash='MTU',
                symbol='MTU',
                title="Average End-to-End Delay (ms) by Load, Medium, and MTU",
                labels={'AvgDelay_ms': 'Delay (ms)', 'TrafficLoad': 'Background Load'},
                category_orders={'TrafficLoad': ['Low', 'Medium', 'High']}
            )
            fig_delay.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#9ca3af")
            st.plotly_chart(fig_delay, use_container_width=True)

# --- TAB 3: INSIGHTS & ANOVA ---
with tab3:
    st.subheader("Theoretical Insight & Underlying Equations")
    
    st.markdown(r"""
    ### How Packet Loss is Modeled
    The simulation models packet corruption based on the **Bit Error Rate (BER)** of the medium. When a packet of size $S$ bytes (including header overheads) is transmitted, the probability of successful transmission without any bit errors is:
    $$P_{\text{success}} = (1 - \text{BER})^{8 \times S}$$
    
    #### The Wireless and Jumbo Frame Penalty
    - **Wireless Link**: High BER ($10^{-5}$).
    - **Copper Link**: Moderate BER ($10^{-7}$).
    - **Fiber Link**: Extremely low BER ($10^{-9}$).
    
    Additionally, Wireless and Copper have a **Physical MTU limit of 1500 bytes**. Sending a **9000-byte Jumbo frame** requires splitting it into **6 fragments**. Since IP reassembly requires all fragments to arrive safely, the entire packet is dropped if any fragment fails. 
    
    For a 9000-byte packet on Wireless:
    $$P_{\text{packet\_success}} = \left((1 - 10^{-5})^{8 \times 1540}\right)^6 \approx 47.4\%$$
    This is why you see a dramatic drop in PDR for the Wireless + 9000 MTU combination.
    
    ---
    
    ### Guide: Setting up ANOVA in Minitab / SPSS
    The exported `simulation_results.csv` contains a **General Linear Model** format. Follow these steps to run a Three-Way ANOVA:
    
    #### In Minitab:
    1. Import the CSV file (**File > Open Worksheet**).
    2. Go to **Stat > ANOVA > General Linear Model > Fit General Linear Model**.
    3. In **Responses**, select `AvgDelay_ms` or `PacketDeliveryRatio_Percent`.
    4. In **Factors**, select `Medium`, `MTU`, and `TrafficLoad`.
    5. Click **Model...** to add interactions (e.g., select all three factors and click **Add** to include 2-way and 3-way interactions).
    6. Click **OK** to run. Look at the **p-values** in the Analysis of Variance table. Any p-value $< 0.05$ indicates a statistically significant effect.
    
    #### In SPSS:
    1. Import the CSV file (**File > Import Data > CSV Data**).
    2. Go to **Analyze > General Linear Model > Univariate**.
    3. Move `AvgDelay_ms` or `PacketDeliveryRatio_Percent` to the **Dependent Variable** box.
    4. Move `Medium`, `MTU`, and `TrafficLoad` to the **Fixed Factor(s)** box.
    5. Click **OK** to run the multi-factor ANOVA.
    """)
