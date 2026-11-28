#!/usr/bin/env python3
#!/usr/bin/env python3
"""
XCP SLCAN Example Usage
=======================

This script provides a stand-alone diagnostic utility for testing XCP (Universal Measurement and Calibration Protocol)
connections over CAN bus interfaces without requiring the full PyXCP application infrastructure.

Key features:
- Direct initialization of an XCP Master for CAN communication
- Configuration of CAN parameters (IDs, bitrate, channel)
- Rich visual output with colored logs and formatted tables
- Comprehensive error reporting and connection diagnostics

The tool performs the following steps:
1. Creates a PyXCP configuration tailored for CAN-SLCAN interfaces
2. Establishes a transport layer connection to the CAN bus
3. Initiates the XCP protocol connection to the slave device
4. Retrieves and displays device properties from the slave
5. Performs a clean disconnect and resource cleanup

Usage:
    Simply run the script to test connectivity with default parameters,
    or modify the create_direct_pyxcp_can() function parameters to match
    your specific CAN configuration.

Requirements:
    - pyxcp library
    - python-can library
    - rich library for enhanced output

This is primarily a diagnostic tool for debugging XCP over CAN connections
and validating proper communication with ECUs and other XCP slave devices.
"""

import logging
import can
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install
from rich.table import Table
from rich import print as rprint
from pyxcp.master import Master
from pyxcp.config import PyXCP
from traitlets.config import Config
from pyxcp.transport.can import Can, PythonCanWrapper
from traitlets import MetaHasTraits

# Set up Rich traceback handling
install(show_locals=True)

# Create Rich console
console = Console()

# Set up Rich logging
FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger("XCP_Direct_Test")

def dump_configurable(cfg):
    """Return a formatted Rich table of all config-tagged traits and their current values."""
    table = Table(title=f"{cfg.__class__.__name__} Configuration")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    for name, trait in cfg.traits(config=True).items():
        value = getattr(cfg, name)
        # Format lists and complex types for better display
        if isinstance(value, (list, tuple)):
            value = str(value)
        table.add_row(name, str(value))
    
    return table

from pyxcp.config import PyXCP, General, Transport

def create_direct_pyxcp_can(
    channel: str         = "COM10",
    bitrate: int         = 500_000,
    can_id_master: int   = 0x03,
    can_id_slave: int    = 0x04,
    can_id_broadcast: int= 0xF4,
    daq_identifier: list = (0x5, 0x6, 0x7),
    timeout: float       = 3.0,
    alignment: int       = 8,
    disconnect_response_optional: bool = False,
    create_daq_timestamps: bool        = False,
) -> PyXCP:
    """
    Return a PyXCP app pre-configured for CAN-SLCAN.
    You can then do:
        app = create_direct_pyxcp_can(...)
        master = Master(app.transport.layer, config=app)
    """
    logger.info("[bold blue]Creating PyXCP configuration for CAN-SLCAN[/bold blue]")
    
    app = PyXCP()
    # replicate what start() would do internally
    app.general   = General(config=app.config, parent=app)
    app.transport = Transport(parent=app)

    # General settings
    app.general.disconnect_response_optional = disconnect_response_optional

    # Transport settings
    app.transport.layer             = "CAN"
    app.transport.timeout           = timeout
    app.transport.alignment         = alignment
    app.transport.create_daq_timestamps = create_daq_timestamps

    # CAN-interface settings
    cancfg = app.transport.can
    cancfg.interface       = "slcan"
    cancfg.channel         = channel
    cancfg.bitrate         = bitrate
    cancfg.can_id_master   = can_id_master
    cancfg.can_id_slave    = can_id_slave
    cancfg.can_id_broadcast= can_id_broadcast
    cancfg.daq_identifier  = list(daq_identifier)
    
    logger.info("[green]PyXCP configuration created successfully[/green]")
    return app

def main():
    """Main function to test direct XCP initialization."""
    with console.status("[bold green]Starting XCP Direct Test...", spinner="dots") as status:
        logger.info("[bold yellow]===== Starting Direct XCP Master Test =====[/bold yellow]")
        
        try:
            # Create the application and master
            status.update("[bold blue]Creating XCP application with direct config...[/bold blue]")
            logger.info("Creating XCP application with direct config...")
            app = create_direct_pyxcp_can()
            
            # Display configurations using Rich tables
            console.print("\n[bold blue]Configuration Details:[/bold blue]")
            console.print(dump_configurable(app.general))
            console.print(dump_configurable(app.transport))
            console.print(dump_configurable(app.transport.can))
            
            status.update("[bold blue]Creating XCP master...[/bold blue]")
            logger.info("Creating XCP master...")
            master = Master(app.transport.layer, config=app)
            
            # Set logging levels
            master.logger.setLevel(logging.INFO)
            master.transport.logger.setLevel(logging.INFO)
            
            # Try to connect
            status.update("[bold green]Attempting to connect to XCP slave...[/bold green]")
            logger.info("Attempting to connect to XCP slave...")
            try:
                # Connect to the transport layer
                master.transport.connect()
                logger.info("[green]Connected successfully to transport layer[/green]")
                
                response = master.connect()
                logger.info(f"[bold green]Connection successful to SLAVE! Response: {response}[/bold green]")
                
                # Print slave properties in a table
                properties_table = Table(title="Slave Properties")
                properties_table.add_column("Property", style="cyan")
                properties_table.add_column("Value", style="green")
                
                for key, value in master.slaveProperties.items():
                    properties_table.add_row(str(key), str(value))
                
                console.print(properties_table)
                
                # Disconnect
                status.update("[bold blue]Disconnecting from slave...[/bold blue]")
                logger.info("Disconnecting from slave...")
                master.disconnect()
                logger.info("[green]Disconnected successfully[/green]")
                
            except Exception as conn_error:
                logger.error(f"[bold red]Connection failed: {conn_error}[/bold red]")
                console.print_exception()
            
            # Clean up
            status.update("[bold blue]Cleaning up resources...[/bold blue]")
            logger.info("Closing transport...")
            master.close()
            logger.info("[green]Transport closed[/green]")
            
        except Exception as e:
            logger.error(f"[bold red]Test failed with error: {e}[/bold red]")
            console.print_exception()
        
        logger.info("[bold yellow]===== Direct XCP Master Test Completed =====[/bold yellow]")

if __name__ == "__main__":
    main()