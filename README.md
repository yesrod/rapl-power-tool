# rapl-power-tool

## A small Python script to read CPU energy usage via RAPL

This was thrown together in an afternoon to handle getting power data from AMD Zen processors, since the zenpower kernel driver doesn't build on kernels 6.14+ and is unlikely to be updated.

Root access is required to read RAPL counters; use sudo or something.

This should work on:
- any Intel system running kernel 3.14 or newer
- any AMD Zen based system:
  - Zen / Zen+ / Zen 2 from kernel 5.8 up
  - Zen 3 / Zen 3+ / Zen 4 from kernel 5.11 up
  - Zen 5 with an additional [one-liner patch](https://lore.kernel.org/lkml/20240719101234.50827-1-Dhananjay.Ugwekar@amd.com/T/) that hasn't landed yet as far as I am aware

## Usage
```
usage: rapl-power-tool [-h] [-l] [-z ZONE] [-s SUBZONE]

A small Python script to read CPU energy usage via RAPL

options:
  -h, --help            show this help message and exit
  -l, --list            List all available RAPL zones and subzones
  -z ZONE, --zone ZONE  Get power data from this RAPL zone in watts
  -s SUBZONE, --subzone SUBZONE
                        Get power data from this RAPL subzone in watts. Requires -z/--zone
```