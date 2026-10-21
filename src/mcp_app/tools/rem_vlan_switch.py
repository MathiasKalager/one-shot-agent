# vlan_tools.py
import logging

import asyncssh

from ..utils.routers import get_router


async def get_vlan_brief(router_name: str) -> dict:
    router = get_router(router_name)
    logging.info(f"Fetching VLAN status from {router.name} ({router.host})")

    cmd = "show vlan brief"

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
        logging.warning(f"VLAN brief fetch failed on {router.name}: {e}")
        return {"error": str(e)}


async def create_or_update_vlan(router_name: str, vlan_id: int, vlan_name: str = None) -> dict:
    router = get_router(router_name)
    logging.info(f"Configuring VLAN {vlan_id} on {router.name} ({router.host})")

    # Build the multi-line CLI configuration script
    cmds = ["configure terminal", f"vlan {vlan_id}"]
    if vlan_name:
        cmds.append(f"name {vlan_name}")
    cmds.append("end")
    
    cmd_string = "\n".join(cmds)

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd_string, check=True)
            return {
                "status": "success", 
                "message": f"VLAN {vlan_id} configured.", 
                "details": result.stdout.strip()
            }
    except Exception as e:
        logging.warning(f"Failed to configure VLAN {vlan_id} on {router.name}: {e}")
        return {"error": str(e)}


async def assign_interface_vlan(
    router_name: str, 
    interface_name: str, 
    vlan_id: int, 
    mode: str = "access"
) -> dict:
    router = get_router(router_name)
    logging.info(f"Assigning {interface_name} to VLAN {vlan_id} ({mode}) on {router.name} ({router.host})")

    cmds = ["configure terminal", f"interface {interface_name}"]
    
    if mode.lower() == "access":
        cmds.extend([
            "switchport mode access",
            f"switchport access vlan {vlan_id}"
        ])
    elif mode.lower() == "trunk":
        cmds.extend([
            "switchport mode trunk",
            f"switchport trunk allowed vlan add {vlan_id}"
        ])
    else:
        return {"error": "Invalid mode. Use 'access' or 'trunk'."}
        
    cmds.append("end")
    cmd_string = "\n".join(cmds)

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd_string, check=True)
            return {
                "status": "success", 
                "message": f"{interface_name} updated successfully.", 
                "details": result.stdout.strip()
            }
    except Exception as e:
        logging.warning(f"Interface VLAN assignment failed on {router.name}: {e}")
        return {"error": str(e)}


async def delete_vlan(router_name: str, vlan_id: int) -> dict:
    router = get_router(router_name)
    logging.info(f"Deleting VLAN {vlan_id} from {router.name} ({router.host})")

    cmd_string = f"configure terminal\nno vlan {vlan_id}\nend"

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            result = await conn.run(cmd_string, check=True)
            return {
                "status": "success", 
                "message": f"VLAN {vlan_id} deleted.", 
                "details": result.stdout.strip()
            }
    except Exception as e:
        logging.warning(f"Failed to delete VLAN {vlan_id} on {router.name}: {e}")
        return {"error": str(e)}


def rem_vlan_tools(mcp):
    mcp.tool(
        description=(
            "Run 'show vlan brief' from the switch CLI to inspect active VLAN assignments "
            "and verify configurations."
        )
    )(get_vlan_brief)

    mcp.tool(
        description=(
            "Create a new VLAN or update an existing VLAN's name in the global VLAN database via SSH. "
            "Pass the integer vlan_id and an optional vlan_name string."
        )
    )(create_or_update_vlan)

    mcp.tool(
        description=(
            "Assign a switchport interface to an access VLAN or add a VLAN to a trunk port via SSH. "
            "Pass interface_name (e.g. 'GigabitEthernet1/0/1'), vlan_id, and mode ('access' or 'trunk')."
        )
    )(assign_interface_vlan)

    mcp.tool(
        description=(
            "Remove a VLAN instance from the switch global database via SSH. "
            "Requires the integer vlan_id."
        )
    )(delete_vlan)