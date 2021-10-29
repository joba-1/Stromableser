from influxdb import InfluxDBClient
import pickle
import sys

# InfluxDB parameters
server = 'job4'
port = 8086
database = 'power'
measurement = 'energy'
field = 'watt'

# CLI interface
if __name__ == "__main__":
    fname = sys.argv[1]

    # read backup created with fixStromableser.py
    with open(fname, 'rb') as f:
        points = pickle.load(f)

    # reformat entries as influx points
    newPoints = []
    for point in points:
        newPoint = {
            "measurement": measurement,
            "tags": {
                "meter": point["meter"],
            },
            "time": point["time"],
            "fields": {
                field: point[field]
            }
        }
        newPoints.append(newPoint)

    # rewrite whole measurement
    client = InfluxDBClient(host=server, port=port, database=database)
    client.query(f'drop measurement {measurement}')
    client.write_points(newPoints)
    print(f"restored {len(newPoints)} measurements")
