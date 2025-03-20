# rapl-power-tool

## A small Python script to read CPU energy usage via RAPL

This was thrown together in an afternoon to handle getting power data from AMD Zen processors, since the zenpower kernel driver doesn't build on kernels 6.14+ and is unlikely to be updated.

This should work on:
- any Intel system running kernel 3.14 or newer
- any AMD Zen based system:
  - Zen / Zen+ / Zen 2 from kernel 5.8 up
  - Zen 3 / Zen 3+ / Zen 4 from kernel 5.11 up
  - Zen 5 from kernel 6.12 up

## Usage
```
usage: rapl-power-tool [-h] [-l] [-z ZONE]

A small Python script to read CPU energy usage via RAPL

options:
  -h, --help            show this help message and exit
  -l, --list            List all available RAPL zones and subzones
  -z ZONE, --zone ZONE  Get power data from this RAPL zone in watts
```

## Running without root

Normally `setcap` can be used to give executables arbitrary permissions, like bypassing file permission checks for reads (`CAP_DAC_READ_SEARCH`), but that gets complicated with scripts, since the actual executable is the interpreter, in this case `python3`.

This can be worked around with [pyinstaller](https://pyinstaller.org/en/stable/), since pyinstaller produces a self-contained binary from a Python script or module.

```
# install pyinstaller
python3 -m venv ~/venv/pyinstaller
. ~/venv/pyinstaller/bin/activate
python3 -m pip install pyinstaller

# generate executable
pyinstaller -F ./rapl-power-tool.py

# give generated executable special powers
sudo setcap CAP_DAC_READ_SEARCH=+ep ./dist/rapl-power-tool
```
