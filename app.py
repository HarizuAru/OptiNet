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
    page_title="Endfield Industries // OptiNet Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR ARKNIGHTS: ENDFIELD THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;600;700&display=swap');

    /* Global styling */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0c0d0f !important;
        color: #c5cacc !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #111317 !important;
        border-right: 1px solid #23272f !important;
    }
    
    /* Input widgets text color */
    div[data-baseweb="select"] > div, div[role="listbox"] {
        background-color: #15181d !important;
        color: #ffffff !important;
        border: 1px solid #23272f !important;
        border-radius: 0px !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Share Tech Mono', monospace !important;
        color: #ffffff !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    /* Top Header Meta */
    .system-meta {
        font-family: 'Share Tech Mono', monospace;
        font-size: 11px;
        color: #53607c;
        letter-spacing: 2px;
        margin-bottom: 2px;
    }
    
    .main-title {
        font-family: 'Share Tech Mono', monospace !important;
        color: #ffffff !important;
        font-size: 2.8rem !important;
        font-weight: 800;
        letter-spacing: 3px;
        margin-bottom: 0px;
        text-transform: uppercase;
    }
    
    .main-title span {
        color: #ff6b00 !important; /* Endfield Orange */
    }
    
    .brand-sub {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
        color: #ff6b00;
        letter-spacing: 4px;
        margin-bottom: 20px;
        border-bottom: 1px solid #23272f;
        padding-bottom: 12px;
    }
    
    /* Hazard Stripes */
    .hazard-bar {
        height: 6px;
        background: repeating-linear-gradient(
            -45deg,
            #ff6b00,
            #ff6b00 12px,
            #0c0d0f 12px,
            #0c0d0f 24px
        );
        margin-bottom: 25px;
        border: 1px solid #ff6b00;
    }
    
    /* Tactical Metric Cards */
    .metric-card {
        background: #14171c !important;
        border: 1px solid #23272f !important;
        border-left: 4px solid #ff6b00 !important;
        border-radius: 0px !important; /* Sharp industrial corners */
        padding: 22px !important;
        position: relative;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
    }
    
    /* Small corner notch accent */
    .metric-card::after {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 6px;
        height: 6px;
        background: #ff6b00;
    }
    
    .metric-label {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #7d8b9e !important;
        text-align: left;
    }
    
    .metric-val {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 2.3rem !important;
        font-weight: 700;
        color: #ffffff;
        margin: 10px 0;
        text-align: left;
    }
    
    .metric-desc {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.72rem;
        color: #4f5a6e;
        text-align: left;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Tactical Buttons */
    .stButton>button {
        background-color: transparent !important;
        color: #ff6b00 !important;
        border: 1px solid #ff6b00 !important;
        border-radius: 0px !important;
        font-family: 'Share Tech Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        transition: all 0.25s ease !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
    }
    
    .stButton>button:hover {
        background-color: #ff6b00 !important;
        color: #0c0d0f !important;
        box-shadow: 0 0 15px rgba(255, 107, 0, 0.4) !important;
        border-color: #ff6b00 !important;
    }
    
    .stButton>button:active {
        background-color: #e66000 !important;
        border-color: #e66000 !important;
    }

    /* Download Button */
    .stDownloadButton>button {
        background-color: #ff6b00 !important;
        color: #0c0d0f !important;
        border: 1px solid #ff6b00 !important;
        border-radius: 0px !important;
        font-family: 'Share Tech Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        font-weight: bold !important;
        transition: all 0.25s ease !important;
        width: 100%;
    }
    
    .stDownloadButton>button:hover {
        background-color: transparent !important;
        color: #ff6b00 !important;
        box-shadow: 0 0 15px rgba(255, 107, 0, 0.4) !important;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #23272f;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #111317 !important;
        border: 1px solid #23272f !important;
        border-bottom: none !important;
        border-radius: 0px !important;
        color: #7d8b9e !important;
        font-family: 'Share Tech Mono', monospace !important;
        text-transform: uppercase;
        padding: 10px 20px !important;
        letter-spacing: 1.5px;
    }
    
    .stTabs [aria-selected="true"] {
        color: #ff6b00 !important;
        border-top: 3px solid #ff6b00 !important;
        background-color: #14171c !important;
        font-weight: bold;
    }
    
    /* Markdown text and alerts */
    .stAlert {
        background-color: #14171c !important;
        border: 1px solid #23272f !important;
        border-left: 4px solid #ff6b00 !important;
        border-radius: 0px !important;
        color: #c5cacc !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #ff6b00 !important;
    }
    
    /* Code block styling */
    code {
        font-family: 'Share Tech Mono', monospace !important;
        background-color: #14171c !important;
        color: #ff6b00 !important;
    }
    
    /* Data table header */
    .dataframe th {
        background-color: #111317 !important;
        color: #ff6b00 !important;
        font-family: 'Share Tech Mono', monospace !important;
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
        
        # Track queue occupancy over time
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
    if link.current_buffer_bytes + packet.size > link.buffer_max_bytes:
        if not packet.is_background:
            receiver.record_drop(packet, 'Buffer Overflow')
        return
        
    link.update_buffer(packet.size)
    
    with link.tx_resource.request() as req:
        yield req
        link.update_buffer(-packet.size)
        
        tx_time, p_success = calculate_tx_details(
            packet.size, link.physical_mtu, link.bandwidth, link.overhead_delay, link.ber
        )
        yield env.timeout(tx_time)
        
    yield env.timeout(link.prop_delay)
    
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

# --- GUI HEADER (ARKNIGHTS: ENDFIELD STYLING) ---

st.markdown('<div class="system-meta">SYSTEM.STATUS: ACTIVE // USER.AUTH: HARIZUARU // ENDFIELD INDUSTRIES INC.</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">▲ OPTINET <span>TERMINAL</span></div>', unsafe_allow_html=True)
st.markdown('<div class="brand-sub">ENDFIELD INDUSTRIES // NETWORK SIMULATION SYSTEM</div>', unsafe_allow_html=True)
st.markdown('<div class="hazard-bar"></div>', unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.markdown('<div style="font-family: \'Share Tech Mono\', monospace; color: #ff6b00; font-size: 1.2rem; font-weight: bold; border-bottom: 1px solid #23272f; padding-bottom: 5px; margin-bottom: 15px;">[SYS.CONFIG]</div>', unsafe_allow_html=True)

sim_duration = st.sidebar.slider("SIMULATION TIME (SEC)", 5, 30, 10, help="Total simulated time for each run.")
warmup_time = st.sidebar.slider("WARMUP PERIOD (SEC)", 1, 5, 1, help="Transient period discarded from statistics.")
fg_rate_mbps = st.sidebar.slider("FLOW INJECTION RATE (MBPS)", 0.5, 10.0, 2.0, step=0.5, help="Bandwidth consumed by the foreground probe flow.")
buffer_max_kb = st.sidebar.number_input("BUFFER THRESHOLD (KB)", min_value=10, max_value=5000, value=500, step=50, help="Max queue capacity in Kilobytes.")

fg_rate_bps = fg_rate_mbps * 1e6

# --- TABS CREATION ---
tab1, tab2, tab3 = st.tabs(["[01] LINK SIMULATOR", "[02] FACTORIAL EXPERIMENT", "[03] ANALYTICAL LOGS"])

# --- TAB 1: SINGLE SCENARIO ---
with tab1:
    st.write("")
    st.write("")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sel_medium = st.selectbox("MEDIUM SELECT", ['Fiber', 'Copper', 'Wireless'])
    with col2:
        sel_mtu = st.selectbox("MTU CONFIGURE (BYTES)", [500, 1500, 9000], index=1)
    with col3:
        sel_load = st.slider("BACKGROUND LOAD (%)", 0, 95, 50, step=5)
    with col4:
        st.write("") 
        st.write("")
        run_btn = st.button("EXECUTE SIMULATION", type="primary", use_container_width=True)
        
    if run_btn or 'single_res' in st.session_state:
        if run_btn:
            with st.spinner("EXECUTING PROTOCOLS..."):
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
                <div class="metric-label">[PACKET DELIVERY RATIO]</div>
                <div class="metric-val" style="color: {pdr_color}">{res['PDR']:.2f}%</div>
                <div class="metric-desc">RECV: {res['PacketsReceived']} // SENT: {res['PacketsSent']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">[END-TO-END DELAY]</div>
                <div class="metric-val" style="color: #00e5ff">{res['AvgDelay_ms']:.4f} ms</div>
                <div class="metric-desc">AVERAGE PROPAGATION + QUEUE</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">[JITTER VARIATION]</div>
                <div class="metric-val" style="color: #ff9f1c">{res['Jitter_ms']:.4f} ms</div>
                <div class="metric-desc">RFC 3550 DEVIATION</div>
            </div>
            """, unsafe_allow_html=True)
            
        with m_col4:
            tot_drops = res['BufferDrops'] + res['ChannelDrops']
            drop_color = "#ef4444" if tot_drops > 0 else "#4f5a6e"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">[LINK PACKET DROPS]</div>
                <div class="metric-val" style="color: {drop_color}">{tot_drops}</div>
                <div class="metric-desc">BUFFER: {res['BufferDrops']} // CHANNEL: {res['ChannelDrops']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("")
        st.write("---")
        
        # Plot Queue occupancy over time
        st.subheader("📊 BUFFER DYNAMICS OVER TIME")
        df_q = res['QueueDF']
        
        fig_q = px.line(
            df_q, x='Time (s)', y='Queue Size (KB)',
            line_shape='hv'
        )
        fig_q.add_hline(y=buffer_max_kb, line_dash="dash", line_color="#ef4444", annotation_text="BUFFER MAX CAPACITY")
        
        # Styled to match Arknights Endfield (Dark, sharp, orange trace)
        fig_q.update_traces(line_color="#ff6b00", line_width=2)
        fig_q.update_layout(
            plot_bgcolor="#14171c",
            paper_bgcolor="rgba(0,0,0,0)",
            font_family="'Share Tech Mono', monospace",
            font_color="#7d8b9e",
            xaxis=dict(
                showgrid=True, 
                gridcolor="#23272f", 
                linecolor="#23272f",
                title_text="SIMULATION TIME (S)"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor="#23272f", 
                linecolor="#23272f", 
                title_text="BUFFER OCCUPANCY (KB)",
                range=[0, max(buffer_max_kb * 1.1, df_q['Queue Size (KB)'].max() * 1.1)]
            ),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_q, use_container_width=True)

# --- TAB 2: FULL FACTORIAL EXPERIMENT ---
with tab2:
    st.write("")
    st.subheader("EXPERIMENT MATRIX EXECUTION")
    st.write("Automatically executes 27 protocol configurations (3 Media × 3 MTUs × 3 Loads).")
    
    run_exp_btn = st.button("INITIATE FULL FACTORIAL RUN (27 RUNS)", type="secondary")
    
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
                    status_text.write(f"🧬 RUNNING SEQUENCE {count:02d}/{total_scenarios:02d}: MEDIUM={medium.upper()} | MTU={mtu} | LOAD={load_name.upper()}...")
                    
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
        st.success("SEQUENCE COMPLETE. DATA EXPORTED TO `simulation_results.csv`.")
    elif os.path.exists(csv_path):
        df_results = pd.read_csv(csv_path)
        
    if df_results is not None:
        st.dataframe(df_results, use_container_width=True)
        
        csv_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DOWNLOAD EXPORTED DATA (.CSV)",
            data=csv_data,
            file_name="simulation_results.csv",
            mime="text/csv",
        )
        
        st.write("")
        st.write("---")
        st.subheader("📊 SEQUENCE CORRELATION ANALYSIS")
        
        vis_col1, vis_col2 = st.columns(2)
        
        with vis_col1:
            # Styled bar chart of PDR
            fig_pdr = px.bar(
                df_results, x='Medium', y='PacketDeliveryRatio_Percent', color='MTU',
                barmode='group', facet_col='TrafficLoad',
                labels={'PacketDeliveryRatio_Percent': 'PDR (%)', 'TrafficLoad': 'LOAD'},
                color_discrete_sequence=['#ff6b00', '#00e5ff', '#8892b0']
            )
            fig_pdr.update_layout(
                title_text="PACKET DELIVERY RATIO BY CONFIGURATION",
                plot_bgcolor="#14171c",
                paper_bgcolor="rgba(0,0,0,0)",
                font_family="'Share Tech Mono', monospace",
                font_color="#7d8b9e",
                xaxis=dict(showgrid=True, gridcolor="#23272f"),
                yaxis=dict(showgrid=True, gridcolor="#23272f")
            )
            st.plotly_chart(fig_pdr, use_container_width=True)
            
        with vis_col2:
            # Styled line chart of Delay
            fig_delay = px.line(
                df_results, x='TrafficLoad', y='AvgDelay_ms', color='Medium', line_dash='MTU',
                symbol='MTU',
                labels={'AvgDelay_ms': 'DELAY (MS)', 'TrafficLoad': 'TRAFFIC LOAD'},
                category_orders={'TrafficLoad': ['Low', 'Medium', 'High']},
                color_discrete_sequence=['#ff6b00', '#00e5ff', '#8892b0']
            )
            fig_delay.update_layout(
                title_text="LATENCY OVER TIME BY LOAD PATTERNS",
                plot_bgcolor="#14171c",
                paper_bgcolor="rgba(0,0,0,0)",
                font_family="'Share Tech Mono', monospace",
                font_color="#7d8b9e",
                xaxis=dict(showgrid=True, gridcolor="#23272f"),
                yaxis=dict(showgrid=True, gridcolor="#23272f")
            )
            st.plotly_chart(fig_delay, use_container_width=True)

# --- TAB 3: INSIGHTS & ANOVA ---
with tab3:
    st.write("")
    st.subheader("SYSTEM EQUATIONS & MODELING PARAMETERS")
    
    st.markdown(r"""
    ### 1. CHANNEL CORRUPTION MATRIX
    Packet loss is computed per fragment based on the physical Bit Error Rate (BER) of the selected transmission medium:
    $$P_{\text{success}} = (1 - \text{BER})^{8 \times S}$$
    
    #### CONFIGURATION CONSTANTS
    - **Fiber Link**: $\text{BER} = 10^{-9}$ (Virtual error-free transmission).
    - **Copper Link**: $\text{BER} = 10^{-7}$ (Moderate industrial shielding).
    - **Wireless Link**: $\text{BER} = 10^{-5}$ (Endfield outdoor interference/fading).
    
    ---
    
    ### 2. IP FRAGMENTATION DECAY
    For physical media with standard MTU limits (**Copper** and **Wireless** both restricted to **1500 bytes**):
    If a packet size exceeds the physical limit (such as a **9000-byte Jumbo frame**), the system fragments the payload:
    $$N = \left\lceil \frac{\text{Packet Size}}{\text{Physical MTU}} \right\rceil$$
    
    Each fragment adds a **40-byte header overhead** and triggers an inter-fragment delay (representing Wi-Fi backoffs or spacing):
    - **Wireless Overhead**: $+100 \mu s$ per fragment.
    - **Copper Overhead**: $+10 \mu s$ per fragment.
    
    ---
    
    ### 3. STATISTICAL DEPLOYMENT (ANOVA PREPARATION)
    The generated data table complies with the **General Linear Model** standard. To perform Analysis of Variance (ANOVA):
    
    #### MINITAB SETUP
    1. Import the worksheet (`simulation_results.csv`).
    2. Navigate to **Stat > ANOVA > General Linear Model > Fit General Linear Model**.
    3. Input `AvgDelay_ms` or `PacketDeliveryRatio_Percent` in **Responses**.
    4. Input `Medium`, `MTU`, and `TrafficLoad` in **Factors**.
    5. Add two-way and three-way interaction terms in the **Model** options.
    
    #### SPSS SETUP
    1. Import the file (**File > Import Data > CSV**).
    2. Navigate to **Analyze > General Linear Model > Univariate**.
    3. Map the independent factors to **Fixed Factor(s)** and your response metrics to the **Dependent Variable**.
    """)
