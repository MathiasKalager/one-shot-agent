## Environment Setup (Linux)

1. Clone the repository and navigate to the project root.

2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   ```bash
   pip install -e .
   ```

4. Copy and configure the environment file:
   ```bash
   cp .env.example .env  # If example exists, otherwise create .env
   ```

5. Configure routers in `src/mcp/utils/routers.py`:
   - Update the `ROUTERS` dictionary with your actual router details (IP addresses, usernames, passwords).
   - Each router must have RESTCONF enabled to use MCP tools.
   - For ping and traceroute functionality, routers must have SSH enabled.

## Configure the routing on eth0 before attaching the ethernet cable 
```bash
sudo nmcli connection modify "eth0"   connection.autoconnect yes   ipv4.method manual   ipv4.addresses 192.168.0.2/24   ipv4.gateway "192.168.0.1"   ipv4.never-default yes   ipv4.routes "172.16.0.0/24 192.168.0.1, 1.1.1.1/32 192.168.0.1, 2.2.2.0/24 192.168.0.1, 3.3.3.0/24 192.168.0.1"
sudo nmcli connection up "eth0"
```
## Running the System

use python or python3 depending on which is used

### Start MCP and Agent Together

From the project root, start both processes with:

```bash
chmod +x ./run-all.sh
./run-all.sh
```
