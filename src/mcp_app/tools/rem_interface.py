# interface_tools.py
import logging

from ..utils.common import encode_intf, get_client
from ..utils.routers import get_router


async def enable_interface(router_name: str, interface_name: str) -> dict:
    """
    Enable a specific interface (no shutdown) using RESTCONF DELETE.
    """
    router = get_router(router_name)

    interface_type = "".join(filter(str.isalpha, interface_name))
    interface_id = interface_name[len(interface_type) :]
    encoded_id = encode_intf(interface_id)

    path = (
        f"https://{router.host}/restconf/data/"
        f"Cisco-IOS-XE-native:native/interface/"
        f"{interface_type}={encoded_id}/shutdown"
    )

    logging.info(f"Enabling interface {interface_name} on {router.name} ({router.host})")

    async with get_client(router) as client:
        try:
            r = await client.delete(path)

            if r.status_code == 404:
                return {
                    "status": "success",
                    "message": f"Interface {interface_name} is already enabled.",
                }

            r.raise_for_status()
            return {
                "status": "success",
                "message": f"Interface {interface_name} enabled successfully",
            }

        except Exception as e:
            logging.error(f"Failed to enable interface {interface_name} on {router.name}: {e}")
            return {"status": "error", "message": str(e)}


async def disable_interface(router_name: str, interface_name: str) -> dict:
    """
    Disable a specific interface (shutdown) using RESTCONF PATCH.
    """
    router = get_router(router_name)

    interface_type = "".join(filter(str.isalpha, interface_name))
    interface_id = interface_name[len(interface_type) :]
    encoded_id = encode_intf(interface_id)

    path = (
        f"https://{router.host}/restconf/data/"
        f"Cisco-IOS-XE-native:native/interface/"
        f"{interface_type}={encoded_id}"
    )

    payload = {
        f"Cisco-IOS-XE-native:{interface_type}": {
            "name": interface_id,
            "shutdown": [None],
        }
    }

    logging.info(f"Disabling interface {interface_name} on {router.name} ({router.host})")

    async with get_client(router) as client:
        try:
            r = await client.patch(path, json=payload)
            r.raise_for_status()

            return {
                "status": "success",
                "message": f"Interface {interface_name} disabled successfully",
            }

        except Exception as e:
            logging.error(f"Failed to disable interface {interface_name} on {router.name}: {e}")
            return {"status": "error", "message": str(e)}


async def set_interface_state(
    router_name: str,
    interface_name: str,
    state: str,
) -> dict:
    """
    Wrapper tool that calls enable_interface or disable_interface.

    Args:
        state: "up" or "down"
    """
    if state.lower() == "up":
        return await enable_interface(router_name, interface_name)

    if state.lower() == "down":
        return await disable_interface(router_name, interface_name)

    return {
        "status": "error",
        "message": "state must be 'up' or 'down'",
    }


async def configure_interface(
    router_name: str,
    interface_name: str,
    ip: str,
    mask: str,
) -> dict:

    router = get_router(router_name)

    interface_type = "".join(filter(str.isalpha, interface_name))
    interface_id = interface_name[len(interface_type) :]

    base = f"https://{router.host}/restconf/data/Cisco-IOS-XE-native:native"

    payload = {
        "Cisco-IOS-XE-native:native": {
            "interface": {
                interface_type: [
                    {
                        "name": interface_id,
                        "ip": {
                            "address": {
                                "primary": {
                                    "address": ip,
                                    "mask": mask,
                                }
                            }
                        },
                    }
                ]
            }
        }
    }

    logging.info(f"Configuring {interface_name} with {ip} {mask} on {router.name} ({router.host})")

    async with get_client(router) as client:
        try:
            r = await client.patch(base, json=payload)
            r.raise_for_status()

            return {
                "status": "success",
                "message": f"{interface_name} configured with {ip}/{mask}",
            }

        except Exception as e:
            logging.error(f"Failed to configure {interface_name} on {router.name}: {e}")
            return {"status": "error", "message": str(e)}


async def remove_interface(
    router_name: str,
    interface_name: str,
) -> dict:

    router = get_router(router_name)

    interface_type = "".join(filter(str.isalpha, interface_name))
    interface_id = interface_name[len(interface_type) :]
    encoded_id = encode_intf(interface_id)

    path = (
        f"https://{router.host}/restconf/data/"
        f"Cisco-IOS-XE-native:native/interface/"
        f"{interface_type}={encoded_id}"
    )

    logging.info(f"Removing interface {interface_name} from {router.name} ({router.host})")

    async with get_client(router) as client:
        try:
            r = await client.delete(path)
            r.raise_for_status()

            return {
                "status": "success",
                "message": f"Interface {interface_name} removed successfully",
            }

        except Exception as e:
            logging.error(f"Failed to remove interface {interface_name} on {router.name}: {e}")
            return {"status": "error", "message": str(e)}






import asyncio
import asyncssh

async def set_interface_description(
    router_name: str, interface_name: str, description: str
) -> dict:
    router = get_router(router_name)
    logging.info(f"Setting description for {interface_name} on {router.name} ({router.host})")

    # Kommandoene vi skal skrive inn i terminalen
    commands = [
        "configure terminal",
        f"interface {interface_name}",
        f"description {description}",
        "end",
        "exit"
    ]

    try:
        async with asyncssh.connect(
            router.host,
            username=router.user,
            password=router.password,
            known_hosts=None,
        ) as conn:
            
            # Opprett en interaktiv prosess (PTY) som lurer ruteren til å tro vi er en ekte terminal
            async with conn.create_process(term_type='vt100') as process:
                
                # Send én og én kommando med en kort pause
                for cmd in commands:
                    process.stdin.write(cmd + '\n')
                    await asyncio.sleep(0.2)  # Gi Cisco-ruteren tid til å prosessere linjen
                
                # Lukk inndata-strømmen slik at vi kan lese resultatet uten å henge
                process.stdin.write_eof()
                
                # Les all tekst ruteren spyttet ut tilbake
                output = await process.stdout.read()
                
            return {
                "result": f"Description set on {interface_name}",
                "output": output.strip()
            }
            
    except Exception as e:
        logging.error(f"Failed to set description on {router.name} ({router.host}): {e}")
        return {"error": str(e)}

async def configure_subinterface(
    router_name: str,
    interface_name: str,
    sub_id: int,
    vlan_id: int,
    ip_address: str,
    subnet_mask: str
) -> dict:
    router = get_router(router_name)
    subinterface = f"{interface_name}.{sub_id}"
    logging.info(f"Configuring RoaS on {subinterface} (VLAN {vlan_id}) on {router.name} ({router.host})")

    # The sequence of commands to set up the subinterface and enable the physical port
    cmds = [
        "configure terminal",
        f"interface {subinterface}",
        f"encapsulation dot1Q {vlan_id}",
        f"ip address {ip_address} {subnet_mask}",
        "exit",
        f"interface {interface_name}",
        "no shutdown",  # Physical interface must be up for subinterfaces to work
        "end"
    ]
    
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
                "message": f"Subinterface {subinterface} configured as gateway for VLAN {vlan_id}.",
                "details": result.stdout.strip()
            }
    except Exception as e:
        logging.warning(f"Failed to configure subinterface on {router.name}: {e}")
        return {"error": str(e)}


async def remove_subinterface(
    router_name: str,
    interface_name: str,
    sub_id: int
) -> dict:
    router = get_router(router_name)
    subinterface = f"{interface_name}.{sub_id}"
    logging.info(f"Removing subinterface {subinterface} from {router.name} ({router.host})")

    cmd_string = f"configure terminal\nno interface {subinterface}\nend"

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
                "message": f"Subinterface {subinterface} deleted.",
                "details": result.stdout.strip()
            }
    except Exception as e:
        logging.warning(f"Failed to remove subinterface {subinterface} on {router.name}: {e}")
        return {"error": str(e)}

def rem_interface_tools(mcp):
    mcp.tool(
        description=(
            "Administratively enable or disable an interface. "
            "Use to remediate link state issues or isolate faults."
        )
    )(set_interface_state)

    mcp.tool(
        description=("Configure primary IPv4 address on an interface.")
    )(configure_interface)

    mcp.tool(
        description=(
            "Delete an interface configuration stanza from the router. "
            "Use with caution as dependent services may break."
        )
    )(remove_interface)

    mcp.tool(
        description=("Set interface description text for documentation and operational clarity.")
    )(set_interface_description)

    mcp.tool(
        description=(
            "Configure a router-on-a-stick subinterface with 802.1Q encapsulation and an IP address via SSH. "
            "Pass the base interface_name (e.g. 'GigabitEthernet1/0'), sub_id (e.g. 10), vlan_id, ip_address, and subnet_mask. "
            "This automatically enables the physical parent interface."
        )
    )(configure_subinterface)
    
    mcp.tool(
        description=(
            "Remove a router-on-a-stick subinterface via SSH. "
            "Pass the base interface_name and sub_id (e.g. interface_name='GigabitEthernet1/0', sub_id=10)."
        )
    )(remove_subinterface)
