Configuration
=============

Parameters live in `JSON` or `TOML` :file:`pyxcp/examples` contains some example configurations.

General pyXCP Parameters
------------------------

eth
~~~

These parameters are rather self-explanatory.

* `HOST`:                   str,                "localhost"
* `PORT`:                   int,                5555
* `PROTOCOL`:               str,                "TCP",    "TCP" | "UDP"
* `IPV6`:                   bool,               False
* `TCP_NODELAY`:            bool,               False

sxi
~~~

Again, obvious parameters.

`PORT`:                     str,                "COM1"
`BITRATE`:                  int,                38400
`BYTESIZE`:                 int,                8
`PARITY`:                   str,                "N"
`STOPBITS`:                 int,                1


General CAN Parameters
----------------------

* `CAN_DRIVER`:               str,             REQUIRED -- "Canalystii" | "IsCAN" | "Ixxat" | "Kvaser" | "Neovi" | "NiCan" |
                                                           "PCan" | "Serial" | "SlCan" | "SocketCAN" | "Systec" | "Usb2Can" | "Vector"
                                                           (the driver names reflect the correspondending class names).
* `CHANNEL`:                  str,             ""       -- Highly driver specific value, see documentation.
* `MAX_DLC_REQUIRED`:         bool,            False    -- if True, DLC is set to MAX_DLC, e.g. 8 on CAN Classic, unused bytes are set to zero.
* `CAN_USE_DEFAULT_LISTENER`: bool,            True     -- if True, the default listener thread is used.
                                                           If the canInterface implements a listener service, this parameter
                                                           can be set to False, and the default listener thread won't be started.
* `CAN_ID_MASTER`:            int,             REQUIRED
* `CAN_ID_SLAVE`:             int,             REQUIRED
* `CAN_ID_BROADCAST`:         int,             REQUIRED
* `BITRATE`:                  int,             250000
* `RECEIVE_OWN_MESSAGES`:     bool,            False


Specific CAN Drivers
--------------------

Every driver has some additional parameters, not further explained here, please refer to the
`python-can documentation. <https://python-can.readthedocs.io/en/master/interfaces.html>`_


canalystii
~~~~~~~~~~
* `BAUD`:                     int,              None    -- Uses `BAUD` instead of `BITRATE`.
* `TIMING0`:                  int,              None
* `TIMING1`:                  int,              None

iscan
~~~~~
* `POLL_INTERVAL`:            float,            0.01

ixxat
~~~~~

* `UNIQUE_HARDWARE_ID`:       str,              None
* `RX_FIFO_SIZE`:             int,              16
* `TX_FIFO_SIZE`:             int,              16

kvaser
~~~~~~

* `ACCEPT_VIRTUAL`:           bool,             True
* `DRIVER_MODE`:              bool,             True
* `NO_SAMP`:                  int,              1
* `SJW`:                      int,              2
* `TSEG1`:                    int,              5
* `TSEG2`:                    int,              2
* `SINGLE_HANDLÈ`:            bool,             True
* `FD`:                       bool,             False
* `DATA_BITRATE`:             int,              None

neovi
~~~~~

* `FD`:                       bool,             False
* `DATA_BITRATE`:             int,              None
* `USE_SYSTEM_TIMESTAMP`:     bool,             False
* `SERIAL`:                   str,              None
* `OVERRIDE_LIBRARY_NAME`:    str,              None

nican
~~~~~

* `LOG_ERRORS`:               bool,             False

pcan
~~~~

* `STATE`:                    str,              "ACTIVE"

serial
~~~~~~

* `BAUDRATE`                  int,              115200      -- Uses `BAUDRATE` instead of `BITRATE`.
* `TIMEOUT`:                  float,            0.1
* `RTSCTS`:                   bool,             False

slcan
~~~~~

* `TTY_BAUDRATE`:             int,              115200
* `POLL_INTERVAL`:            float,            0.01
* `SLEEP_AFTER_OPEN`:         float,            2.0
* `RTSCTS`:                   bool,             False

socketcan
~~~~~~~~~

* `FD`:                       bool,             False

systec
~~~~~~

* `DEVICE_NUMBER`:           int,               255
* `RX_BUFFER_ENTRIES`:       int,               4096
* `TX_BUFFER_ENTRIES`:       int,               4096
* `STATE`:                   str,               "ACTIVE"

usb2can
~~~~~~~

`FLAGS`:                     int,               0

vector
~~~~~~

* `POLL_INTERVAL`:           float,              0.01
* `APP_NAME`:                str,                ""
* `SERIAL`:                  int,                None
* `RX_QUEUE_SIZE`:           int,                16384
* `FD`:                      bool,               False
* `DATA_BITRATE`:            int,                None

