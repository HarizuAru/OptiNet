# OptiNet - Heterogeneous Network Topology Simulator

An interactive, high-fidelity Python software application designed to investigate and visualize the effects of transmission media, Maximum Transmission Unit (MTU) sizes, and background traffic loads on key network performance metrics: **End-to-End Delay**, **Jitter**, and **Packet Delivery Ratio (PDR)**.

The project features a discrete-event simulation core built with `simpy` and an interactive web-based dashboard built with `streamlit`.

---

## Features

- **Interactive GUI**: A beautiful, modern interface running locally in your browser.
- **Single Scenario Simulator**: Select a custom medium, MTU, and background load. Run the simulation to see real-time KPI cards and an interactive step-chart of the transmitter's queue occupancy over time.
- **Full Factorial Experiment**: Run the entire 27-scenario experiment ($3 \times 3 \times 3$ design) with a single click.
- **Data Visualizations**: Interactively analyze relationships using Plotly bar and line charts.
- **Data Export**: One-click download of the simulation results as a structured `simulation_results.csv` file.
- **ANOVA Ready**: The exported dataset is formatted for direct import into statistical software like **Minitab**, **SPSS**, or **R**.

---

## Installation & Setup

### Prerequisites
Ensure you have Python (version 3.8 or higher) installed on your system.

### 1. Install Dependencies
Install the required libraries via pip:
```bash
pip install simpy pandas streamlit plotly numpy
```
*(If on Windows with the Python Launcher, use `py -m pip install simpy pandas streamlit plotly numpy`)*

### 2. Run the Software
To launch the interactive web application, run the following command in your terminal:
```bash
streamlit run app.py
```
*(If on Windows with the Python Launcher, use `py -m streamlit run app.py`)*

After running, the application will automatically open in your default web browser (usually at `http://localhost:8501`).

---

## Underlying Simulation Logic & Mathematical Modeling

The simulation models a single-hop network link where foreground probe traffic competes with background traffic for a shared transmission channel.

### 1. Transmission Media Parameters
Three media types are modeled with distinct physical characteristics:

| Medium | Bandwidth (bps) | Propagation Delay (ms) | Bit Error Rate (BER) | Physical MTU (Bytes) | Fragmentation Overhead Delay (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fiber** | 1,000 Mbps (1 Gbps) | 0.1 | $10^{-9}$ | 9,000 (Jumbo) | 0.0 |
| **Copper** | 100 Mbps | 1.0 | $10^{-7}$ | 1,500 (Standard) | 0.01 (10 $\mu$s) |
| **Wireless** | 54 Mbps | 5.0 | $10^{-5}$ | 1,500 (Standard) | 0.10 (100 $\mu$s) |

### 2. IP Fragmentation and Overhead
If a packet size (configured by the experimental **MTU** factor) exceeds the physical MTU limit of the transmission medium:
1. The packet is fragmented into $N$ fragments:
   $$N = \left\lceil \frac{\text{Packet Size}}{\text{Physical MTU}} \right\rceil$$
2. Each fragment is appended with a **40-byte header overhead** (simulating IP and MAC layer headers).
3. The total transmission time on the link includes an **inter-fragment gap (overhead delay)** to simulate MAC-layer acknowledgement, backoffs, or inter-frame spacing (IFS) on copper and wireless links:
   $$T_{\text{tx\_total}} = \sum_{i=1}^{N} \frac{8 \times \text{Fragment Size}_i}{\text{Bandwidth}} + (N - 1) \times T_{\text{overhead\_delay}}$$

### 3. Packet Loss Modeling
Packet loss can occur due to two distinct real-world phenomena:
- **Buffer Overflow**: The link transmitter has a finite buffer queue (default **500 KB**). If a packet arrives when the buffer is full, it is dropped.
- **Channel Corruption**: Each fragment is subject to independent bit errors based on the medium's Bit Error Rate (BER). The probability of a single fragment arriving successfully is:
   $$P_{\text{frag\_success}} = (1 - \text{BER})^{8 \times \text{Fragment Size}}$$
   For the entire packet to be successfully received, **all $N$ fragments must arrive without error**. If any fragment is corrupted, the entire packet is dropped (IP reassembly failure):
   $$P_{\text{packet\_success}} = \prod_{i=1}^{N} P_{\text{frag\_success}, i}$$

This mathematical formulation heavily penalizes **Wireless** links (high BER) and **large MTUs** (more bits, higher probability of corruption, and fragmentation requirements).

### 4. Background Traffic
Background traffic is modeled as a **Poisson process** (exponentially distributed inter-arrival times). The arrival rate is dynamically calculated for each run to consume a target percentage of the link's total bandwidth (e.g., 20% for Low, 50% for Medium, 80% for High).

---

## Interpreting the CSV Output

After running the Full Factorial Experiment, you can export the results to `simulation_results.csv`. This file is formatted with clean column headers and is ready to be directly imported into statistical software.

### Column Descriptions

| Column Header | Data Type | Description | Role in ANOVA |
| :--- | :--- | :--- | :--- |
| `Medium` | Categorical | The transmission medium type (`Fiber`, `Copper`, `Wireless`). | Independent Variable (Factor 1) |
| `MTU` | Quantitative | The Maximum Transmission Unit size in bytes (`500`, `1500`, `9000`). | Independent Variable (Factor 2) |
| `TrafficLoad` | Categorical | The background traffic load intensity (`Low`, `Medium`, `High`). | Independent Variable (Factor 3) |
| `AvgDelay_ms` | Quantitative | The average end-to-end delay (transmission + queuing + propagation) of successfully received foreground packets in milliseconds. | Dependent Variable (Response 1) |
| `Jitter_ms` | Quantitative | The average variation in delay between consecutive packets in milliseconds (calculated per RFC 3550). | Dependent Variable (Response 2) |
| `PacketDeliveryRatio_Percent` | Quantitative | The percentage of sent foreground packets that were successfully received. | Dependent Variable (Response 3) |
| `PacketsSent` | Quantitative | Total foreground packets sent during the measurement window. | Metadata / Verification |
| `PacketsReceived` | Quantitative | Total foreground packets successfully received. | Metadata / Verification |
| `BufferOverflowDrops` | Quantitative | Number of foreground packets dropped due to transmitter queue buffer overflow. | Diagnostic |
| `ChannelErrorDrops` | Quantitative | Number of foreground packets dropped due to bit errors on the link. | Diagnostic |

### ANOVA Setup Example (Minitab / SPSS)
1. Import `simulation_results.csv` into your worksheet.
2. Go to **Stat > ANOVA > General Linear Model > Fit General Linear Model**.
3. Set your **Responses** to `AvgDelay_ms`, `Jitter_ms`, or `PacketDeliveryRatio_Percent`.
4. Set your **Factors** to `Medium`, `MTU`, and `TrafficLoad`.
5. Under **Model**, include main effects and two-way/three-way interactions (e.g., `Medium * MTU` to verify the wireless/jumbo frame interaction effect).
