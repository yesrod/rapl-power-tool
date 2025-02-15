#!/bin/env python3

import argparse
import os
import re
import sys
import time

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# main zones like /sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj
# subzones like /sys/class/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/energy_uj
POWERCAP_DIR="/sys/class/powercap/intel-rapl"
POWERCAP_ENERGY_FILE="energy_uj"


@dataclass
class REPLZone:
    zone_id: int
    subzones: List[int] = field(default_factory=list)

    @classmethod
    def list_zones(cls) -> Dict[int, "REPLZone"]:
        zone_pattern = re.compile(r'intel-rapl:(\d+):?(\d+)?')

        zones: Dict[int, REPLZone] = {}
        for root, dirs, files in os.walk(POWERCAP_DIR):
            #print(root)
            #print(dirs)
            #print(files)
            if POWERCAP_ENERGY_FILE in files:
                endpoint_path = os.path.join(root, POWERCAP_ENERGY_FILE)
                zone_matches = zone_pattern.findall(endpoint_path)
                #print(endpoint_path, zone_matches)
                if zone_matches:
                    for match in zone_matches:
                        if int(match[0]) in zones.keys():  # zone has been indentified previously
                            if match[1] and int(match[1]) not in zones[int(match[0])].subzones:  # new subzone identified
                                zones[int(match[0])].subzones.append(int(match[1]))
                        else:   # new zone identified
                            zones[int(match[0])] = REPLZone(
                                zone_id = int(match[0]),
                                subzones = [int(match[1]), ] if match[1] else []
                            )
        return zones

    @classmethod
    def get_zone(cls, zone: int) -> "REPLZone":
        zone_path = os.path.join(POWERCAP_DIR, f"intel-rapl:{zone}")
        if not os.path.exists(zone_path):
            raise ValueError(f"Zone {zone} not found")
        zone_pattern = re.compile(r'intel-rapl:(\d+):?(\d+)?')
        zone_matches = zone_pattern.findall(zone_path)
        zone_obj = REPLZone(zone_id=zone)
        if zone_matches:
            for match in zone_matches:
                if match[1] and int(match[1]) not in zone_obj.subzones:  # new subzone identified
                    zone_obj.subzones.append(int(match[1]))
        return zone_obj

    def get_zone_data(
        self,
        subzone: Optional[int] = None,
        data_interval: float = 0.1
    ) -> float:
        zone_dir = os.path.join(POWERCAP_DIR, f"intel-rapl:{self.zone_id}")
        if subzone:
            zone_file = os.path.join(zone_dir, f"intel-rapl:{self.zone_id}:{subzone}", POWERCAP_ENERGY_FILE)
        else:
            zone_file = os.path.join(zone_dir, POWERCAP_ENERGY_FILE)
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
            return self.get_zone_data(subzone, data_interval)
        uj_consumed = end_uj - start_uj
        #print(f"zone {self.zone_id} subzone {subzone}: duration {duration}, uj_consumed {uj_consumed}")
        return (float(uj_consumed) / 1000000) / float(duration)

def main():
    parser = argparse.ArgumentParser(
        prog="rapl-power-tool",
        description="A small Python script to read CPU energy usage via RAPL"
    )
    parser.add_argument('-l', '--list', action='store_true',
        help="List all available RAPL zones and subzones"                    
    )
    parser.add_argument('-z', '--zone', type=int,
        help="Get power data from this RAPL zone in watts"
    )
    parser.add_argument('-s', '--subzone', type=int,
        help="Get power data from this RAPL subzone in watts. Requires -z/--zone"
    )
    args = parser.parse_args()

    if args.list:
        zones = REPLZone.list_zones()
        for zone in zones.values():
            print(f"Zone {zone.zone_id}{f', subzones {",".join([str(s) for s in zone.subzones])}'}")
        sys.exit(0)

    if args.zone is None:
        print("ERROR: Zone is required")
        parser.print_help()
        sys.exit(1)

    zone = REPLZone.get_zone(args.zone)
    print(zone.get_zone_data(subzone=args.subzone))


if __name__ == '__main__':
    main()
