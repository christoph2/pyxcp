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

    return app
