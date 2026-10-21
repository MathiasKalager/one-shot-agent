# device_info.py
import logging

import asyncssh

from ..utils.common import get_client
from ..utils.routers import get_router


async def get_running_config(router_name: str) -> dict:
    router = get_router(router_name)
    logging.info(f"Fetching running config from {router.name} ({router.host})")
    base = f"https://{router.host}/restconf"

    async with get_client(router) as client:
        try:
            # Hent hele native-blokken
            r = await client.get(f"{base}/data/Cisco-IOS-XE-native:native")
            r.raise_for_status()
            data = r.json().get("Cisco-IOS-XE-native:native", {})

            # Filtrer på klient-siden
            return {
                "hostname": data.get("hostname"),
                "ios_xe_version": data.get("version"),
                "interfaces": data.get("interface"),
                "routing": data.get("ip", {}).get("route"),
                "access_lists": data.get("ip", {}).get("access-list"),
                "users": data.get("username"),
                "license": data.get("license", {}).get("udi"),
            }

        except Exception as e:
            logging.warning(f"Failed to get running config from {router.name}: {e}")
            return {"error": str(e)}

async def get_cdp_neighbors(router_name: str, detail: bool = False) -> dict:
    router = get_router(router_name)
    logging.info(f"Fetching CDP neighbors from {router.name} ({router.host})")

    cmd = "show cdp neighbors detail" if detail else "show cdp neighbors"

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd, check=True)
            return {"output": result.stdout.strip()}
    except Exception as e:
        logging.warning(f"CDP fetch failed on {router.name}: {e}")
        return {"error": str(e)}


async def get_lldp_neighbors(router_name: str, detail: bool = False) -> dict:
    router = get_router(router_name)
    logging.info(f"Fetching LLDP neighbors from {router.name} ({router.host})")

    cmd = "show lldp neighbors detail" if detail else "show lldp neighbors"

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd, check=True)
            return {"output": result.stdout.strip()}
    except Exception as e:
        logging.warning(f"LLDP fetch failed on {router.name}: {e}")
        return {"error": str(e)}


async def get_syslog(router_name: str, include_filter: str = None) -> dict:
    router = get_router(router_name)
    logging.info(f"Fetching syslogs from {router.name} ({router.host})")

    cmd = "show logging"
    # Append pipe filter if user wants to search for specific logs (e.g. "BGP" or "down")
    if include_filter:
        cmd += f" | include {include_filter}"

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd, check=True)
            return {"output": result.stdout.strip()}
    except Exception as e:
        logging.warning(f"Syslog fetch failed on {router.name}: {e}")
        return {"error": str(e)}



def register_config_tools(mcp):
    mcp.tool(
        description=(
            "Fetch key sections of the running configuration for troubleshooting and baseline checks "
            "(hostname, interfaces, routes, ACLs, users, license/UDI)."
        )
    )(get_running_config)
    mcp.tool(
        description=(
            "Run 'show cdp neighbors' from the router CLI to discover directly connected Cisco devices. "
            "Set detail=True for IP addresses and capabilities."
        )
    )(get_cdp_neighbors)
    
    mcp.tool(
        description=(
            "Run 'show lldp neighbors' from the router CLI to discover directly connected multi-vendor devices. "
            "Set detail=True for IP addresses and port info."
        )
    )(get_lldp_neighbors)
    
    mcp.tool(
        description=(
            "Run 'show logging' from the router CLI to retrieve the device syslog buffer. "
            "Use the include_filter parameter to grep for specific strings (e.g., 'BGP', 'down', 'error')."
        )
    )(get_syslog)
