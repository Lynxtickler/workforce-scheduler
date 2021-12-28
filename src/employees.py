"""
Contains the definition for a collection of employees.
"""

import random
from string import ascii_lowercase
from .constants import *
from .helpers import *
from .employee import Employee


class Employees:
    """Maintains a list of employees.

    Capable of creating random collections of employees for testing purposes.

    Attributes:
        collection:
            A dictionary of current employees. Keys are employee IDs and items instances of Employee class.
    """

    def __init__(self, employee_list=None):
        """Initialise the object with an existing dictionary of employees or empty dictionary."""
        self.collection = {} if (employee_list is None) else employee_list

    def count(self):
        """Return the number of current employees."""
        return len(self.collection)

    def add(self, employee):
        """Add employee to dictionary.

        Args:
            employee: Employee instance to add to the dictionary.

        Returns:
            A boolean value. True if adding successful, False if not.
        """
        if not isinstance(employee, Employee):
            return False
        self.collection[employee.id] = employee
        return True

    def remove(self, employee):
        """Remove employee from dictionary.

        Args:
            employee:
                Employee instance to remove from dictionary.
        """
        self.collection.pop(employee.id, None)

    def generate_employee_id(self):
        """Create ID for employee randomly.

        Return None if no unique ID is available after a pre-defined maximum amount of tries.
        """
        maximum_iterations = 2500
        for _ in range(maximum_iterations):
            new_id = random.randint(ID_LOWER_BOUND, ID_UPPER_BOUND)
            if not self.id_exists(new_id):
                return new_id
        return None

    def id_exists(self, checked_id):
        """Check if ID exists within existing employees.

        Args:
            checked_id: ID whose value is checked for uniqueness.
        """
        for _, employee in self.collection.items():
            if checked_id == employee.id:
                return True
        return False

    def create_dummy_employees(self, count_of_employees, work_site_demands, fixed_hours=False, start_day=0):
        """Create a random list of employees for testing purposes.

        Args:
            count_of_employees:
                Number of employees to be created. If None, employees are created as long
                as needed to fulfill the total hours in work site demands.
            work_site_demands:
                List of tuples defining future work site schedules.
                Employee preferences are created in respect to opening hours.
            fixed_hours:
                A boolean defining if random employees will have a fixed number of hours
                in their contracts instead of a range. Defaults to False.
            start_day:
                Index of the weekday from where scheduling starts. Affects the number of full weekends.
                Defaults to 0 i.e. Monday.

        Returns:
            Boolean value. True if employees' total hours are above the first week's demands.
        """
        fulfill_hours = False
        if not count_of_employees:
            fulfill_hours = True
            count_of_employees = sys.maxsize
        weeks_in_schedule = len(work_site_demands) / 7
        total_weekly_hours = sum([sum(x) for x in work_site_demands])
        total_weekly_hours /= weeks_in_schedule
        employee_hours_currently = 0
        seniors_created = 0
        print('total needed hours:', total_weekly_hours / PERIODS_PER_HOUR)
        extras = 0
        needed_extras = 0
        for i in range(count_of_employees):
            new_employee = self.create_random_employee(work_site_demands, fixed_hours, start_day)
            if new_employee is None:
                break
            if new_employee.seniority != 0:
                seniors_created += 1
            self.collection[new_employee.id] = new_employee
            employee_hours_currently += ((new_employee.min_hours + new_employee.max_hours) / 2)
            # Add ~7% extra employees for more probable feasibility.
            if i % 15 == 0:
                needed_extras += 1
            if extras >= needed_extras:
                break
            if ((employee_hours_currently > total_weekly_hours) and fulfill_hours):
                extras += 1
        print('total (avg) hours :',
              employee_hours_currently / PERIODS_PER_HOUR)
        if not seniors_created:
            _, random_employee = random.choice(list(self.collection.items()))
            random_employee.seniority = 1
        return employee_hours_currently >= total_weekly_hours

    def create_random_employee(self, work_site_demands,
                               fixed_hours=False, start_day=0):
        """Create random employee and return the instance.

        Args:
            work_site_demands:
                List of tuples defining work site schedule. Preferences are created in respect to opening hours.
            fixed_hours:
                A boolean defining if the employee will have a fixed number of
                hours in their contract instead of a range. Defaults to False.
            start_day:
                Index of the weekday from where scheduling starts. Affects the number of full weekends.
                Defaults to 0 i.e. Monday.
        """
        contract_type = random.choice((Contract.FULLTIME, Contract.PARTTIME))
        if contract_type == Contract.FULLTIME:
            min_hours = 38 * PERIODS_PER_HOUR
            max_hours = (38 if fixed_hours else 40) * PERIODS_PER_HOUR
        else:
            min_hours = random.choice(range(15 * PERIODS_PER_HOUR, 30 * PERIODS_PER_HOUR, 2))
            max_hours = random.choice(range(min_hours, 30 * PERIODS_PER_HOUR, 2))
        if fixed_hours:
            min_hours = max_hours
        max_shifts = None
        if max_hours is None:
            pass
        elif max_hours < 20 * PERIODS_PER_HOUR:
            max_shifts = 4
        elif max_hours < 15 * PERIODS_PER_HOUR:
            max_shifts = 3
        random_id = self.generate_employee_id()
        if random_id is None:
            return None
        random_name = ''
        for _ in range(8):
            random_name += random.choice(ascii_lowercase)
        random_seniority = 1 if (random.random() < .05) else 0
        random_properties = PropertyFlag.NONE
        if random.random() < RANDOM_CHANCES['open_and_close']:
            random_properties += PropertyFlag.CAN_OPEN
            random_properties += PropertyFlag.CAN_CLOSE
        random_streak = random.choice([6] + 2 * [5] + 3 * [4] + 4 * [3] + 5 * [2] + 6 * [1] + 7 * [0])
        random_weekends = {}
        if random.random() < RANDOM_CHANCES['weekend']:
            s = 1 if (start_day == WEEKDAY_SUN) else 0
            weekend_range = range(int(len(work_site_demands) / 7) - s)
            random_weekends['single'] = [random.choice(weekend_range)]
        random_weekends['groups'] = []
        if len(work_site_demands) / 7 > 3:
            week_count = int(len(work_site_demands) / 7)
            weekend_list = list(range(0, week_count))
            slice_length = 5
            groups = [weekend_list[i:i + slice_length] for i in range(0, len(weekend_list), slice_length)]
            for split_group in groups:
                if random.random() < RANDOM_CHANCES['weekend']:
                    weekends_off = random.choice((1, 2))
                    random_weekends['groups'].append([weekends_off] + split_group)
        random_preferences = {}
        for i in range(len(work_site_demands)):
            rand = random.random()
            if rand < RANDOM_CHANCES['absence']:
                unavailable_period_index = random.choice(range(len(work_site_demands[i])))
                random_preferences[i] = {unavailable_period_index: Preference.UNAVAILABLE}
            elif (rand < RANDOM_CHANCES['absence'] + RANDOM_CHANCES['preference']):
                undesirable_period_index = random.choice(range(len(work_site_demands[i])))
                random_preferences[i] = {undesirable_period_index: Preference.UNDESIRABLE}

        return Employee(random_id, random_name, contract_type, min_hours, max_hours, max_shifts, random_seniority,
                        random_properties, random_streak, random_weekends, random_preferences)
