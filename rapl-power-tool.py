#!/bin/env python3

import argparse
import os
import re
import sys
import time

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# main zones like /sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj
# subzones like /sys/class/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj
POWERCAP_ROOT_DIR="/sys/devices/virtual/powercap"
POWERCAP_ENERGY_FILE="energy_uj"
ZONE_DIR_PATTERN = re.compile(r'intel-rapl(?:-mmio)?')
ZONE_PATTERN = re.compile(r'([a-zA-Z-]+):(\d+):?(\d+)?')

@dataclass
class REPLZone:
    #name: str
    zone_id: str
    #subzones: List[Tuple[int, str]] = field(default_factory=list)
    subzones: List["REPLZone"] = field(default_factory=list)

    @classmethod
    def list_zones(cls) -> Dict[str, "REPLZone"]:
        zones: Dict[str, REPLZone] = {}
        for root, dirs, files in os.walk(POWERCAP_ROOT_DIR):
            for root_dir in dirs:
                if ZONE_DIR_PATTERN.findall(root_dir):
                    POWERCAP_DIR = os.path.join(POWERCAP_ROOT_DIR, root_dir)
                    for root, dirs, files in os.walk(POWERCAP_DIR):
                        for dir in dirs:
                            endpoint_path = os.path.join(root, POWERCAP_ENERGY_FILE)
                            zone_matches = ZONE_PATTERN.match(dir)
                            if zone_matches:
                                match = zone_matches.groups()
                                zone_id = f"{match[0]}:{match[1]}"
                                if zone_id in zones.keys():  # zone has been indentified previously
                                    if match[2] and f"{zone_id}:{match[2]}" not in zones[zone_id].subzones:  # new subzone identified
                                        zones[zone_id].subzones.append(REPLZone(zone_id = f"{zone_id}:{match[2]}"))
                                else:   # new zone identified
                                    zones[zone_id] = REPLZone(
                                        zone_id = zone_id,
                                        subzones = [ REPLZone(zone_id = f"{zone_id}:{match[2]}"), ] if match[2] else []
                                    )
        return zones

    @classmethod
    def get_zone(cls, zone: str) -> "REPLZone":
        zone_path = REPLZone._build_zone_path(zone)
        if not os.path.exists(zone_path):
            raise ValueError(f"Zone {zone} not found")
        zone_matches = ZONE_PATTERN.findall(zone_path)
        zone_obj = REPLZone(zone_id=zone)
        if zone_matches:
            for match in zone_matches:
                if match[2] and f"{zone}:{match[2]}" not in zone_obj.subzones:  # new subzone identified
                    zone_obj.subzones.append(REPLZone(zone_id = f"{zone}:{match[2]}"))
        return zone_obj

    @staticmethod
    def _build_zone_path(zone: str):
        split_zone = zone.split(':')
        if len(split_zone) == 2:
            return os.path.join(POWERCAP_ROOT_DIR, split_zone[0], zone)
        elif len(split_zone) == 3:
            return os.path.join(POWERCAP_ROOT_DIR, split_zone[0], f"{split_zone[0]}:{split_zone[1]}", zone)
        else:
            raise ValueError(f"Invalid zone ID {zone}")

    def get_zone_data(
        self,
        data_interval: float = 0.1
    ) -> float:
        zone_file = os.path.join(
            REPLZone._build_zone_path(self.zone_id),
            POWERCAP_ENERGY_FILE
        )
        try:
            with open(zone_file, 'r') as f:
                start_uj = int(f.read())
                start_time = time.perf_counter()
            time.sleep(data_interval)
            with open(zone_file, 'r') as f:
                end_uj = int(f.read())
                end_time = time.perf_counter()
            duration = end_time - start_time
            if duration < 0:
                print("Counter rollover detected, remeasuring")
                return self.get_zone_data(data_interval)
            uj_consumed = end_uj - start_uj
            return round((float(uj_consumed) / 1000000) / float(duration), 2)
        except FileNotFoundError:
            raise ValueError(f"No such zone {self.zone_id}")

def main():
    parser = argparse.ArgumentParser(
        prog="rapl-power-tool",
        description="A small Python script to read CPU energy usage via RAPL"
    )
    parser.add_argument('-l', '--list', action='store_true',
        help="List all available RAPL zones and subzones"                    
    )
    parser.add_argument('-z', '--zone', type=str,
        help="Get power data from this RAPL zone in watts"
    )
    args = parser.parse_args()

    if args.list:
        zones = REPLZone.list_zones()
        for zone in zones.values():
            print(zone.zone_id)
            for subzone in zone.subzones:
                print(f"  \u2514 {subzone.zone_id}")
        sys.exit(0)

    if args.zone is None:
        print("ERROR: Zone is required")
        parser.print_help()
        sys.exit(1)
    try:
        zone = REPLZone.get_zone(args.zone)
        print(zone.get_zone_data())
    except ValueError as e:
        print(e)


if __name__ == '__main__':
    main()
