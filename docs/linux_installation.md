There are several things to consider:
- minimum required Python version is currently 3.8.
- Eigentlich ist this document about installation of pyXCP on Linux, aber das folgende trifft auch die Installation von Python packages on modern Linux distros in general.
... trift auf moderne Linux distros im allgemeinen zu.

Wir starten gleich mit dem Fazit:
The upshort: Use virtual environments (???LINK) when ever possible!

You may want to start with `pip install pyxcp`, but this ????,
??? but you may run into problems???
so read on.

For the sake of reproduceability, lets start with a `Dockerfile`:

``` Docker
FROM ubuntu:24.04

RUN apt update
RUN apt upgrade -y
RUN apt install -y pkg-config
RUN apt install -y gcc git cmake libssl-dev python3 python3-pip python3-venv python3-poetry pipx rustc cargo libffi-dev
RUN apt install -y zsh nano tmux

CMD ["/bin/zsh"]
```
Note
----
Depending on your distro there seem to be two main differences (besides the package manager):
- `libssl-dev` vs. `openssl-devel`
- `libffi` vs. `libffi-dev`


```shell
 find /usr -name "libpython*.so"
```

``` shell
raspi% find /usr -name "libpython*.so"
/usr/lib/aarch64-linux-gnu/libpeas-1.0/loaders/libpython3loader.so
/usr/lib/aarch64-linux-gnu/libpython3.11.so
/usr/lib/aarch64-linux-gnu/libpython3.11d.so
/usr/lib/python3.11/config-3.11d-aarch64-linux-gnu/libpython3.11.so
/usr/lib/python3.11/config-3.11d-aarch64-linux-gnu/libpython3.11d.so
/usr/lib/python3.11/config-3.11-aarch64-linux-gnu/libpython3.11.so
find: ‘/usr/share/polkit-1/rules.d’: Keine Berechtigung
```

```shell
 find /usr -name "libpython*.a"
```

```shell
raspi% find /usr -name "libpython*.a"
/usr/lib/aarch64-linux-gnu/libpython3.11.a
/usr/lib/aarch64-linux-gnu/libpython3.11d.a
/usr/lib/python3.11/config-3.11d-aarch64-linux-gnu/libpython3.11d.a
/usr/lib/python3.11/config-3.11-aarch64-linux-gnu/libpython3.11.a
/usr/lib/python3.11/config-3.11-aarch64-linux-gnu/libpython3.11-pic.a
find: ‘/usr/share/polkit-1/rules.d’: Keine Berechtigung

```

 find /usr -name "libpython*.a"


After building an image and running a container from it you may run
``` shell
pipx install pyxcp
```
and you're done.

![Screenshot](./images/docker01.png "Screenshot / Docker")

But wait, it's probably not that easy on your Linux box!

- can be confusing at best and outright break the entire underlying operating system at worst.

While this could be brute-forced away with
`pip install --break-system-packages --ignore-installed  <package>`
~/.config/pip/pip.conf:
[global]
break-system-packages = true
and in other situations
`pip install --user  <package>`
may work, the user is highly advised to use `pipx` as package installer.

This is really nice, if one is installing .... like `csvkit`

See:
- [externally managed environments](https://packaging.python.org/en/latest/specifications/externally-managed-environments/#externally-managed-environments)
- [PEP-668 (historical)](https://peps.python.org/pep-0668/)

