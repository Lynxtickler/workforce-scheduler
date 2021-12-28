"""
Defines all constants used by the program.
"""


import time


START_TIME = time.time()
DEFAULT_OPTIMISATION_ACCURACY = .15
ID_LOWER_BOUND = 10000000
ID_UPPER_BOUND = 99999999
NUMBER_OF_WORKDAYS = 7
MAXIMUM_CONSECUTIVE_WORKDAYS = 7
PERIODS_PER_HOUR = 2
SHIFT_START_INTERVAL = 1
DEFAULT_SHIFT_IN_PERIODS = 8 * PERIODS_PER_HOUR
MINIMUM_SHIFT_IN_PERIODS = 4 * PERIODS_PER_HOUR
MAXIMUM_SHIFT_IN_PERIODS = DEFAULT_SHIFT_IN_PERIODS
DEFAULT_WEEKLY_MAXIMUM_SHIFTS = 5
PREFERENCE_MULTIPLIER = 4
DEFAULT_WEIGHTS = {'preference': .25, 'day_pairs_off': .25,
                   'weekends_off': .25, 'excess_workforce': .25}
WEEKDAY_FRI = 4
WEEKDAY_SAT = 5
WEEKDAY_SUN = 6
RANDOM_CHANCES = {'absence': .05, 'preference': .06,
                  'open_and_close': .87, 'weekend': .1}
