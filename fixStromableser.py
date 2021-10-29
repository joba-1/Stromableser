from influxdb import InfluxDBClient
from datetime import datetime
import pickle

# InfluxDB parameters
server = 'job4'
port = 8086
database = 'power'
measurement = 'energy'
field = 'watt'

# CLI interface
if __name__ == "__main__":
    # algo:
    # * read measurement
    # * remove rows where values increase when going backwards
    # * if rows removed
    #   * create backup file
    #   * drop  measurement
    #   * insert remaining rows in new measurement

    # request whole measurement
    client = InfluxDBClient(host=server, port=port, database=database)
    response = client.query(f'select * from {measurement}')
    if response.error != None:
        print(f'Reading measurements failed: {response.error}\n')
        quit()

    # create list of new influx values
    points = list(response.get_points())
    maxValue = points[-1][field]
    newPoints = []
    for point in reversed(points):
        if point[field] <= maxValue:
            maxValue = point[field]
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

    # if points removed then write backup and new measurement
    removed = len(points) - len(newPoints)
    if removed > 0:
        dt = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        with open(f'{database}-{measurement}-{dt}.bak', 'wb') as f:
            pickle.dump(points, f)

        client.query(f'drop measurement {measurement}')
        client.write_points(reversed(newPoints))

        print(f"removed {removed} measurements")
