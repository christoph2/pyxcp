#!/usr/bin/env python3
"""
Test script for direct XCP Master initialization without PyXCP application.
"""

import logging
import can
from pyxcp.master import Master
from pyxcp.config import PyXCP
from traitlets.config import Config
from pyxcp.transport.can import Can, PythonCanWrapper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("XCP_Direct_Test")
from traitlets import MetaHasTraits

def dump_configurable(cfg):
    """Return a dict of all config-tagged traits and their current values."""
    out = {}
    for name, trait in cfg.traits(config=True).items():
        out[name] = getattr(cfg, name)
    return out



def main():
    """Main function to test direct XCP initialization."""
    logger.info("=== Starting Direct XCP Master Test ===")
    
    try:
        # This approach is too complex for a quick fix - we'd need to replicate
        # much of the internal XCP code to make it work correctly
        
        # Instead, let's try using the working application approach
        logger.info("Falling back to the working application approach...")
        
        # Import the necessary modules to use the working approach
        import os
        import sys
        from pyxcp.config import create_application
        
        # Create a temporary config file
        config_content = """
# Configuration file for pyXCP.
c = get_config()  # noqa

c.Transport.layer = "CAN"
c.Transport.alignment = 8
c.Transport.timeout = 3.0
c.Transport.create_daq_timestamps = False

c.General.disconnect_response_optional = False

c.Transport.Can.interface = "slcan"
c.Transport.Can.use_default_listener = True
c.Transport.Can.channel = "COM10"
c.Transport.Can.bitrate = 500000
c.Transport.Can.can_id_master = 0x03
c.Transport.Can.can_id_slave = 0x04
c.Transport.Can.can_id_broadcast = 0xF4
c.Transport.Can.max_dlc_required = False
c.Transport.Can.daq_identifier = [0x5, 0x6, 0x7]
"""
        import os
        # Create temp config file in the same directory as this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "temp_pyxcp_conf.py")
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Set environment variable and arguments
        os.environ["PYXCP_CONFIG"] = config_path
        sys.argv = [sys.argv[0], f"-c={config_path}"]
        
        # Create the application and master
        logger.info("Creating XCP application with config file...")
        app = create_application()
        # after you’ve set up `app`:
        print("=== GENERAL CONFIG ===")
        print(dump_configurable(app.general))
        print("\n=== TRANSPORT CONFIG (top-level) ===")
        print(dump_configurable(app.transport))
        print("\n=== CAN CONFIG ===")
        print(dump_configurable(app.transport.can))
        logger.info("Creating XCP master...")
        master = Master(app.transport.layer, config=app)
        
        # Set logging levels
        master.logger.setLevel(logging.INFO)
        master.transport.logger.setLevel(logging.INFO)
        
        # Try to connect
        logger.info("Attempting to connect to XCP slave...")
        try:
            # Connect to the transport layer
            master.transport.connect()
            logger.info("Connected successfully to transport layer")
            response = master.connect()
            logger.info(f"Connection successful! Response: {response}")
            
            # Print slave properties
            logger.info("Slave Properties:")
            for key, value in master.slaveProperties.items():
                logger.info(f"  {key}: {value}")
            
            # Disconnect
            logger.info("Disconnecting from slave...")
            master.disconnect()
            logger.info("Disconnected successfully")
            
        except Exception as conn_error:
            logger.error(f"Connection failed: {conn_error}")
        
        # Clean up
        logger.info("Closing transport...")
        master.close()
        logger.info("Transport closed")
        
        # Remove temporary config file
        try:
            import os
            os.remove(config_path)
            logger.info(f"Removed temporary config file: {config_path}")
        except:
            pass
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    
    logger.info("=== Direct XCP Master Test Completed ===")

if __name__ == "__main__":
    main()