"""
Basic Sri Lankan Gas Station Simulation
- Octane 92 & 95 share 2 pumps (1 pipe per side)
- Diesel: 2 pumps, 2 pipes each
- Metrics: wait time, total time, queue length
- I've used the Hanwella cypetco petrol station
"""

import simpy
import random
import matplotlib.pyplot as plt
import statistics

# -----------------------------
# Simulation parameters
# -----------------------------
RANDOM_SEED = 42
SIM_HOURS = 8
SIM_TIME = SIM_HOURS * 60  # in minutes

# Fuel types
FUEL_TYPES = ['Octane92', 'Octane95', 'Diesel']

# Vehicle distribution probabilities
VEHICLE_PROBS = [0.4, 0.4, 0.2]

# Liters distribution (triangular)
LITERS_DIST = {
    'Octane92': (10, 25, 40),
    'Octane95': (10, 25, 40),
    'Diesel': (20, 50, 100)
}

# Payment time (triangular, minutes)
PAYMENT_TIME_DIST = (0.5, 1.0, 2.0)

# Pump flow rate (liters/min)
FLOW_RATE = 3.0

# Number of pipes per fuel type
PIPES_CONFIG = {
    'Octane92': 2,   # shared over 2 pumps (1 pipe per side each)
    'Octane95': 2,   # shared over 2 pumps (1 pipe per side each)
    'Diesel': 4      # 2 pumps, 2 pipes each
}

# Arrival rate (vehicles per hour)
ARRIVAL_RATE = 20

# -----------------------------
# Helper functions
# -----------------------------
def triangular_sample(tpl):
    return random.triangular(*tpl)

def sample_liters(fuel_type):
    return triangular_sample(LITERS_DIST[fuel_type])

def sample_payment_time():
    return triangular_sample(PAYMENT_TIME_DIST)

def choose_fuel_type():
    return random.choices(FUEL_TYPES, weights=VEHICLE_PROBS, k=1)[0]

def interarrival_time(rate_per_hour):
    mean_minutes = 60.0 / rate_per_hour
    return random.expovariate(1.0 / mean_minutes)

# -----------------------------
# Gas station class
# -----------------------------
class GasStation:
    def __init__(self, env):
        self.env = env
        # Create resources for each fuel type
        self.resources = {fuel: simpy.Resource(env, capacity=PIPES_CONFIG[fuel]) for fuel in FUEL_TYPES}
        
        # Metrics
        self.wait_times = {fuel: [] for fuel in FUEL_TYPES}
        self.total_times = {fuel: [] for fuel in FUEL_TYPES}
        self.service_times = {fuel: [] for fuel in FUEL_TYPES}
        self.queue_length_series = {fuel: [] for fuel in FUEL_TYPES}

    def record_queue(self):
        for fuel in FUEL_TYPES:
            self.queue_length_series[fuel].append((self.env.now, len(self.resources[fuel].queue)))

    def customer_process(self, fuel_type, name):
        arrival_time = self.env.now
        with self.resources[fuel_type].request() as req:
            self.record_queue()
            yield req
            wait_time = self.env.now - arrival_time
            self.wait_times[fuel_type].append(wait_time)
            
            liters = sample_liters(fuel_type)
            fueling_time = liters / FLOW_RATE
            payment_time = sample_payment_time()
            total_service = fueling_time + payment_time
            self.service_times[fuel_type].append(total_service)

            yield self.env.timeout(total_service)
            self.total_times[fuel_type].append(self.env.now - arrival_time)
            self.record_queue()

    def arrival_generator(self, arrival_rate):
        i = 0
        while self.env.now < SIM_TIME:
            iat = interarrival_time(arrival_rate)
            yield self.env.timeout(iat)
            i += 1
            fuel_type = choose_fuel_type()
            self.env.process(self.customer_process(fuel_type, f'Vehicle-{i}'))

# -----------------------------
# Run the simulation
# -----------------------------
def main():
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    station = GasStation(env)
    env.process(station.arrival_generator(ARRIVAL_RATE))
    env.run(until=SIM_TIME)

    # Print basic metrics
    for fuel in FUEL_TYPES:
        avg_wait = statistics.mean(station.wait_times[fuel]) if station.wait_times[fuel] else 0
        avg_total = statistics.mean(station.total_times[fuel]) if station.total_times[fuel] else 0
        print(f'{fuel} - Avg Wait Time: {avg_wait:.2f} min, Avg Total Time: {avg_total:.2f} min')

    # Plot queue length for each fuel type
    for fuel in FUEL_TYPES:
        series = station.queue_length_series[fuel]
        if series:
            times, qlens = zip(*series)
            plt.figure(figsize=(10,5))
            plt.step(times, qlens, where='post')
            plt.xlabel('Time (minutes)')
            plt.ylabel('Queue Length')
            plt.title(f'Queue Length Over Time ({fuel})')
            plt.show()

if __name__ == "__main__":
    main()
