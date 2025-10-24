"""
Basic Sri Lankan Gas Station Simulation
- Octane 92 & 95 share 2 pumps (1 pipe per side)
- Diesel: 2 pumps, 2 pipes each
- Metrics: wait time, total time, queue length
- Scenarios: Normal, Peak Traffic, Extra Pumps
- I've used the Hanwella cypetco petrol station
"""

import simpy
import random
import matplotlib.pyplot as plt
import statistics


                                # ------- Simulation parameters ----------

RANDOM_SEED = 42
SIM_HOURS = 8
SIM_TIME = SIM_HOURS * 60  # in minutes

# Fuel types
FUEL_TYPES = ['Octane92', 'Octane95', 'Diesel']

# Liters distribution (triangular)
LITERS_DIST = {
    'Motorcycle_Octane92': (1, 3, 5),
    'Car_Octane92': (10, 25, 40),
    'Car_Octane95': (10, 25, 40),
    'Lorry_Diesel': (20, 50, 100)
}

# Payment time (triangular, minutes)
PAYMENT_TIME_DIST = (0.5, 1.0, 2.0)

# Pump flow rate (liters/min)
FLOW_RATE = 3.0


                            # ------ Scenario configurations -----------

SCENARIOS = {
    'Normal': {
        'PIPES_CONFIG': {'Octane92': 2, 'Octane95': 2, 'Diesel': 4},
        'ARRIVAL_RATES': {'Octane92': 12, 'Octane95': 3, 'Diesel': 7}
    },
    'PeakTraffic': {
        'PIPES_CONFIG': {'Octane92': 2, 'Octane95': 2, 'Diesel': 4},
        'ARRIVAL_RATES': {'Octane92': 20, 'Octane95': 6, 'Diesel': 12}
    },
    'ExtraPumps': {
        'PIPES_CONFIG': {'Octane92': 3, 'Octane95': 3, 'Diesel': 6},
        'ARRIVAL_RATES': {'Octane92': 20, 'Octane95': 6, 'Diesel': 12}
    }
}


                            # ------ Helper functions -----------

def triangular_sample(tpl):
    return random.triangular(*tpl)

def sample_liters(fuel_type):
    mapping = {
        'Octane92': 'Car_Octane92',
        'Octane95': 'Car_Octane95',
        'Diesel': 'Lorry_Diesel'
    }
    return triangular_sample(LITERS_DIST[mapping[fuel_type]])

def sample_payment_time():
    return triangular_sample(PAYMENT_TIME_DIST)

def interarrival_time(rate_per_hour):
    mean_minutes = 60.0 / rate_per_hour
    return random.expovariate(1.0 / mean_minutes)



                        # ----- Gas station class --------

class GasStation:
    def __init__(self, env, pipes_config):
        self.env = env
        self.resources = {fuel: simpy.Resource(env, capacity=pipes_config[fuel]) for fuel in FUEL_TYPES}
        self.wait_times = {fuel: [] for fuel in FUEL_TYPES}
        self.total_times = {fuel: [] for fuel in FUEL_TYPES}
        self.queue_length_series = {fuel: [] for fuel in FUEL_TYPES}

    def record_queue(self):
        for fuel in FUEL_TYPES:
            self.queue_length_series[fuel].append((self.env.now, len(self.resources[fuel].queue)))

    def customer_process(self, fuel_type, name):
        arrival_time = self.env.now
        self.record_queue()
        with self.resources[fuel_type].request() as req:
            yield req
            wait_time = self.env.now - arrival_time
            self.wait_times[fuel_type].append(wait_time)

            liters = sample_liters(fuel_type)
            fueling_time = liters / FLOW_RATE
            payment_time = sample_payment_time()
            total_service = fueling_time + payment_time
            yield self.env.timeout(total_service)

            self.total_times[fuel_type].append(self.env.now - arrival_time)
            self.record_queue()

    def arrival_generator(self, fuel_type, arrival_rate):
        i = 0
        while self.env.now < SIM_TIME:
            iat = interarrival_time(arrival_rate)
            yield self.env.timeout(iat)
            i += 1
            self.env.process(self.customer_process(fuel_type, f'{fuel_type}-{i}'))

                                    # ------ Run the simulation ----------

def run_scenario(name, config):
    print(f"\n--- Scenario: {name} ---")
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    station = GasStation(env, config['PIPES_CONFIG'])

    for fuel, rate in config['ARRIVAL_RATES'].items():
        env.process(station.arrival_generator(fuel, rate))

    env.run(until=SIM_TIME)

    # Print metrics
    for fuel in FUEL_TYPES:
        avg_wait = statistics.mean(station.wait_times[fuel]) if station.wait_times[fuel] else 0
        avg_total = statistics.mean(station.total_times[fuel]) if station.total_times[fuel] else 0
        print(f'{fuel} - Avg Wait Time: {avg_wait:.2f} min, Avg Total Time: {avg_total:.2f} min')

    # Plot queue lengths
    for fuel in FUEL_TYPES:
        series = station.queue_length_series[fuel]
        if series:
            times, qlens = zip(*series)
            plt.figure(figsize=(10,5))
            plt.step(times, qlens, where='post')
            plt.xlabel('Time (minutes)')
            plt.ylabel('Queue Length')
            plt.title(f'{fuel} Queue Length Over Time ({name})')
            plt.show()

if __name__ == "__main__":
    for scenario_name, scenario_config in SCENARIOS.items():
        run_scenario(scenario_name, scenario_config)
