#!/bin/env python3

import argparse
import json
import os
import re
import sys
import time

from dataclasses import dataclass, field
from typing import Any, Dict, List

# main zones like /sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj
# subzones like /sys/class/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj
POWERCAP_ROOT_DIR="/sys/devices/virtual/powercap"
POWERCAP_ENERGY_FILE="energy_uj"
ZONE_DIR_PATTERN = re.compile(r'intel-rapl(?:-mmio)?')
ZONE_PATTERN = re.compile(r'([a-zA-Z-]+):(\d+):?(\d+)?')

@dataclass
class REPLZone:
    name: str
    zone_id: str
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
                            zone_matches = ZONE_PATTERN.match(dir)
                            if zone_matches:
                                match = zone_matches.groups()
                                zone_id = f"{match[0]}:{match[1]}"
                                if zone_id in zones.keys():  # zone has been indentified previously
                                    if match[2] and f"{zone_id}:{match[2]}" not in zones[zone_id].subzones:  # new subzone identified
                                        name_path = os.path.join(root, f"{zone_id}:{match[2]}", 'name')
                                        with open(name_path, 'r') as f:
                                            name = f.read().rstrip()
                                        zones[zone_id].subzones.append(REPLZone(name = name, zone_id = f"{zone_id}:{match[2]}"))
                                else:   # new zone identified
                                    name_path = os.path.join(root, zone_id, 'name')
                                    with open(name_path, 'r') as f:
                                        name = f.read().rstrip()
                                    if match[2]:
                                        subzone_name_path = os.path.join(root, zone_id, f"{zone_id}:{match[2]}", 'name')
                                        with open(subzone_name_path, 'r') as f:
                                            subzone_name = f.read().rstrip()
                                        subzone = REPLZone(name = subzone_name, zone_id = f"{zone_id}:{match[2]}")
                                    else:
                                        subzone = None
                                    zones[zone_id] = REPLZone(
                                        name = name,
                                        zone_id = zone_id,
                                        subzones = [ subzone, ] if subzone else []
                                    )
        return zones

    @classmethod
    def get_zone(cls, zone: str) -> "REPLZone":
        zone_path = REPLZone._build_zone_path(zone)
        if not os.path.exists(zone_path):
            raise ValueError(f"Zone {zone} not found")
        with open(os.path.join(zone_path, 'name')) as f:
            name = f.read().rstrip()
        zone_obj = REPLZone(name = name, zone_id=zone)
        zone_matches = ZONE_PATTERN.findall(zone_path)
        if zone_matches:
            for match in zone_matches:
                for f in os.listdir(zone_path):
                    if zone in f: # new subzone identified
                        subzone_path = os.path.join(zone_path, f)
                        with open(os.path.join(subzone_path, 'name')) as file:
                            subzone_name = file.read().rstrip()
                        zone_obj.subzones.append(REPLZone(name=subzone_name, zone_id = f))
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

    def as_dict(
            self,
            include_data: bool = False
        ) -> Dict[str, Any]:
        zone_data = {
            "zone_id": self.zone_id,
            "name": self.name,
            "subzones": [ s.as_dict(include_data=include_data) for s in self.subzones ]
        }
        if include_data:
            zone_data["data"] = self.get_zone_data()
        return zone_data

def print_zones_text(zones: List[REPLZone]):
    for zone in zones:
        print(f"{zone.zone_id} ({zone.name}): {zone.get_zone_data()}")
        for subzone in zone.subzones:
            print(f"  \u2514 {subzone.zone_id} ({subzone.name}): {subzone.get_zone_data()}")

def print_zones_json(zones: List[REPLZone]):
    output_data = []
    for zone in zones:
        output_data.append(
            zone.as_dict(include_data=True)
        )
    print(json.dumps(output_data, indent=2))


def main():
    parser = argparse.ArgumentParser(
        prog="rapl-power-tool",
        description="A small Python script to read CPU energy usage via RAPL"
    )
    parser.add_argument('-l', '--list', action='store_true',
        help="List all available RAPL zones and subzones, with power data"                    
    )
    parser.add_argument('-z', '--zone', type=str,
        help="Get power data from this RAPL zone in watts"
    )
    parser.add_argument('-j', '--json', action='store_true',
        help="Output in JSON format"
    )
    args = parser.parse_args()

    if args.list:
        zones = REPLZone.list_zones()
        if args.json:
            print_zones_json(list(zones.values()))
        else:
            print_zones_text(list(zones.values()))
        sys.exit(0)

    if args.zone is None:
        print("ERROR: One of -z/--zone or -l/--list is required")
        parser.print_help()
        sys.exit(1)
    try:
        zone = REPLZone.get_zone(args.zone)
        if args.json:
            print(json.dumps(zone.as_dict(include_data=True)))
        else:
            print_zones_text([zone,])
    except ValueError as e:
        print(e)


if __name__ == '__main__':
    main()
