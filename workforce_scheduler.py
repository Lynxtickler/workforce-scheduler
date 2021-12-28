"""Program to automate and optimise a workforce schedule."""


import random
import time
from math import isclose
from pulp import *
from src.constants import *
from src.helpers import *
from src.employees import Employees


class Scheduler:
    """Scheduler class.

    Maximises employee preferences while minimising costs.

    Attributes:
        employees:
            Employees object from which the schedule will be generated.
        work_site_schedule:
            A list of tuples representing work site needs. Elements of the list are workdays and elements of the tuples
            are the required amount of employees for every period of the day. The length of the tuples are the total
            periods that the site is open for that day.
        weights:
            A length 3 tuple representing objective function weights.
            Format: (preference, shift lengths, excess workforce)
        start_day:
            An integer between 0-6, representing the weekday from where scheduling is started.
            Affects weekends allocation in the model.
        shift_start_interval:
            An integer defining the number of time periods between every new starting shift.
        accuracy:
            A float representing the desired solver accuracy. As soon as the best known solution is within
            this fraction of the best possible solution, the solver will return.
        time_limit:
            Maximum allowed running time in seconds.
        debug:
            A boolean to define whether to print debug messages. Defaults to False
    """

    def __init__(self, employees, work_site_demands, weights=None, start_day=None, shift_start_interval=None,
                 accuracy=None, time_limit=None, debug=False):
        """Initialise scheduler with list of employees."""
        self.employees = employees
        self.work_site_demands = work_site_demands
        self.workday_count = len(work_site_demands)
        self.workdays_period_demand = [len(all_periods_needs) for all_periods_needs in work_site_demands]
        self.weights = weights
        if (weights is None) or not isclose(sum(weights.values()), 1):
            print('No objective weights provided or their sum is not 1. Using defaults.')
            self.weights = DEFAULT_WEIGHTS
        self.start_day = start_day if start_day else 0
        self.shift_start_interval = SHIFT_START_INTERVAL if (shift_start_interval is None) else shift_start_interval
        self.accuracy = accuracy if accuracy else DEFAULT_OPTIMISATION_ACCURACY
        self.time_limit = time_limit
        self.debug = debug
        [print(x.to_text()) for _, x in self.employees.collection.items()]

    def run(self, time_limit=None):
        """Create LP problem from employees.

        Solve the created problem and return a schedule.

        Args:
            time_limit:
                Optional time limit in seconds. This overrides the time limit property for this run.
        """
        print('workdays:', self.workday_count)
        decision_variables = self.create_lp_problem()
        if not time_limit:
            time_limit = self.time_limit
        self.problem.solve(PULP_CBC_CMD(gapRel=self.accuracy, timeLimit=time_limit))
        print(f'Solved in {time.time() - START_TIME}s')
        self.print_results(decision_variables, self.workday_count / 7, self.problem.status)

    def create_lp_problem(self):
        """Create the LP problem for this scheduler."""
        self.problem = LpProblem('schedule', LpMinimize)
        for _, employee in self.employees.collection.items():
            employee.set_employee_shifts(self.work_site_demands)
        print(f'All shifts created in {time.time() - START_TIME}s')
        decision_variables = self.create_decision_variables()
        time_passed = time.time() - START_TIME
        print(f'Decision variables created in {time_passed}s')
        self.create_objective(decision_variables)
        print(f'Objective created in {time.time() - START_TIME}s')
        self.create_constraints(decision_variables)
        print(f'Constraints created in {time.time() - START_TIME}s')

        print('decision variables:', len(self.problem.variables()))
        print('constraints:', len(self.problem.constraints))
        return decision_variables

    def print_results(self, decision_variables, number_of_weeks=None, status=None, print_daily=False):
        """Print out the results given by the solved model.

        Args:
            decision_variables:
                Problem decision variables
            number_of_weeks:
                Number of weeks scheduled. Defaults to None. If not provided, employee hours
                in console show the total for the whole schedule.
            status:
                Problem status.
            print_daily:
                If daily excess hours should be printed or not. Defaults to False.
        """
        x = decision_variables['shifts']
        y = decision_variables['workforce']
        d = decision_variables['days']
        w = decision_variables['weekends']
        if not number_of_weeks:
            number_of_weeks = 1
        for key, employee in x.items():
            employee_hours = 0
            for day in employee:
                for shift in day:
                    if shift.value() != 0:
                        employee_id, day_index, shift_index = self.get_decision_var_ids(shift)
                        print(shift, '->', shift.value(), '->',
                              self.employees.collection[employee_id].shifts[day_index][shift_index])
                        employee_hours += len(self.employees.collection[employee_id].shifts[day_index][shift_index])

            min_h = self.employees.collection[key].min_hours / PERIODS_PER_HOUR
            max_h = self.employees.collection[key].max_hours / PERIODS_PER_HOUR
            raw_h = employee_hours / PERIODS_PER_HOUR / number_of_weeks
            print(f'Employee {key} hours:', round(raw_h, 2), f'{min_h}-{max_h}')
            days_off_list = []
            for day_off_var in d[key]:
                if day_off_var.value() == 1:
                    days_off_list.append(self.get_decision_var_ids(day_off_var)[1])
            print('Days off:', days_off_list)
        total_excess_hours = 0
        for day in y:
            for lpvariable in day:
                if print_daily:
                    print(lpvariable.name, '->', lpvariable.value())
                total_excess_hours += lpvariable.value()
        print('Weekends off:')
        for key, employee in w.items():
            print(key, [weekend[0].value() for weekend in employee])

        print('obj value:', self.problem.objective.value())
        print('excess hours:', total_excess_hours / PERIODS_PER_HOUR)
        print('problem status (1=opt):', status)

    def get_decision_var_ids(self, variable):
        """Return parsed variables's IDs as integers.

        Args:
            variable: A decision variable to process.

        Returns:
            A tuple of IDs. Length depends on the type of the decision variable being processed.
        """
        return [int(x) for x in variable.name[1:].split(':')]

    def create_decision_variables(self):
        """Create decision variables for the LP model.

        Returns:
            A dictionary of different kinds of decision variables:
            shifts:
                Dictionary of lists of lists. Defines if employee i is assigned to day j:s shift k.
            workforce:
                List of lists. Keeps track of excess employees on day i:s period j.
            days_off:
                Dictionary of lists. Defines if employee i:s day j is off duty.
            day_pairs:
                Dictionary of lists. Defines if employee i has days j and j+1 both off duty.
            weekends:
                Dictionary of lists of tuples. Defines if either Fri-Sat or Sat-Sun of employee i:s week j is off.
                Innermost tuple consists of: (decision_variable, [Fri and/or Sat indices])
        """
        # 1. Create decision variables in format:
        #   x{employee_id: [day_index][shift_index]}
        #   These determine if a shift is assigned to employee.
        # 2. Create surplus variables representing days off for all employees.
        # 3. Create binary variables for every subsequent two days off. The variables will "overlap".
        x_eds = {}
        days_off = {}
        subsequent_days_off = {}
        weekends_off = {}
        recent_days_off = {}
        for _, employee in self.employees.collection.items():
            x_eds[employee.id] = []
            days_off[employee.id] = []
            subsequent_days_off[employee.id] = []
            recent_days_off[employee.id] = []
            weekend_indices = []
            for day_index in range(len(employee.shifts)):
                # Add employee-shift -assignment variables.
                x_eds[employee.id].append([])
                day_shift_count = len(employee.shifts[day_index])
                for shift_index in range(day_shift_count):
                    lp_var_name = str(f'x{employee.id}:{day_index}:' + f'{shift_index}')
                    x_eds[employee.id][day_index].append(LpVariable(lp_var_name, 0, 1, 'Integer'))

                # Add days off variables.
                days_off[employee.id].append(LpVariable(f'd{employee.id}:{day_index}', 0, 1, 'Integer'))

                # Add binary variables to define if a consecutive pair of days is off-duty for the employee.
                if (day_index + 1 < len(employee.shifts)):
                    subsequent_days_var = LpVariable(f'p{employee.id}:{day_index}-{day_index + 1}', 0, 1, 'Integer')
                    subsequent_days_off[employee.id].append(subsequent_days_var)
                    if (self.start_day + day_index) % 7 in (WEEKDAY_FRI, WEEKDAY_SAT):
                        weekend_indices.append(day_index)

            # Combine same weekend's indices to pairs. If start day is Saturday, start splitting to
            # pairs from index 1. The first item will then be a single item list because the first
            # weekend only has Sat-Sun pair but not a Fri-Sat pair.
            weekends_off[employee.id] = []
            split_start_idx = 1 if (self.start_day == WEEKDAY_SAT) else 0
            weekends_split = [weekend_indices[i:i + 2] for i in range(split_start_idx, len(weekend_indices), 2)]
            for pair in weekends_split:
                weekend_variable_idx = len(weekends_off[employee.id])
                weekend_variable = LpVariable(f'w{employee.id}:{weekend_variable_idx}', 0, 1, 'Integer')
                weekends_off[employee.id].append((weekend_variable, pair))

        # Create more decision variables in format:
        # y[day_index][period_index]
        # These represent the excess employees working during every period of day.
        y_dp = []
        for i, day_length in enumerate(self.workdays_period_demand):
            y_dp.append([])
            for j in range(day_length):
                lp_var_name = f'y{i}:{j}'
                y_dp[i].append(LpVariable(lp_var_name, 0, cat='Integer'))
        return {'shifts': x_eds, 'workforce': y_dp, 'days': days_off,
                'pairs': subsequent_days_off, 'weekends': weekends_off}

    def create_objective(self, decision_variables):
        """Create objective function for LP model.

        Args:
            decision_variables:
                A dictionary of decision variables in correct format.
        """
        objective = []
        main_variables = decision_variables['shifts']
        period_surplus_variables = decision_variables['workforce']
        day_pairs = decision_variables['pairs']
        weekends_off = decision_variables['weekends']
        for _, employee in self.employees.collection.items():
            shift_count = len(employee.shifts)
            for day_index in range(shift_count):
                for shift_index, shift in enumerate(employee.shifts[day_index]):
                    preference_factor = 1
                    try:
                        if (employee.preferences[day_index][shift_index] & Preference.UNDESIRABLE):
                            # Violating a preference results in a hefty rise in the objective value.
                            # The multiplier needs to be big since preferences are relatively rare
                            # considering the total amount of terms in the objective function.
                            preference_factor = int(Preference.UNDESIRABLE)
                    except KeyError:
                        pass
                    # Add employee's dissatisfaction towards a certain shift into the objective.
                    final_preference_factor = self.weights['preference'] * preference_factor
                    objective += [final_preference_factor * main_variables[employee.id][day_index][shift_index]]

                # Add one off-duty subsequent day pair to the objective each week.
                if (day_index % 7 == 6):
                    # Default ending offset set to 1 due to range function behaviour.
                    # Set to 0 in case the current day is the last in the schedule.
                    offset = 0 if (day_index == shift_count - 1) else 1
                    indices = range(day_index - 6, day_index - offset)
                    random_index = random.choice(indices)
                    objective += [-self.weights['day_pairs_off'] * day_pairs[employee.id][random_index]]

            # Add off-duty weekends to the objective.
            weight_key = 'weekends_off'
            objective += [(-self.weights[weight_key] * weekend_tuple[0]) for weekend_tuple in weekends_off[employee.id]]

        # Add excess workers for each shift to the objective to minimise expenses.
        objective += [(self.weights['excess_workforce'] * period_variable for period_variable in day) for day in (
            period_surplus_variables)]
        self.problem += lpSum(objective)

    def create_constraints(self, decision_variables):
        """Create constraints to LP model.

        Args:
            decision_variables:
                A dictionary of decision variables in correct format.
        """
        main_variables = decision_variables['shifts']
        period_surplus_variables = decision_variables['workforce']
        day_off_surplus_variables = decision_variables['days']
        day_pair_off_variables = decision_variables['pairs']
        weekend_variables = decision_variables['weekends']
        # Prepare first constraints of a kind to be added to debug messages.
        db_msgs = []
        first_constraint = 11 * [True]
        # Add constraints for fulfilling all work site's time period needs. Iterate over all days in work site schedule.
        for day_index in range(len(self.work_site_demands)):
            # Create vectors to hold all opening and closing shifts from eligible employees.
            all_open_capable_employees_shifts = []
            all_close_capable_employees_shifts = []
            # Iterate over every period in every day.
            period_count = len(self.work_site_demands[day_index])
            for period_index in range(period_count):
                # Create a vector to hold all shifts that contain said period.
                all_shifts_matching_period = []
                # Iterate over each employee.
                for _, employee in self.employees.collection.items():
                    # Iterate over each open shift for the employee on the given day.
                    shift_count = len(employee.shifts[day_index])
                    for shift_index in range(shift_count):
                        # If current processed shift contains current period, add decision variable to vector.
                        if period_index in employee.shifts[day_index][shift_index]:
                            all_shifts_matching_period.append(main_variables[employee.id][day_index][shift_index])

                            # If current shift is also an opening shift and employee can open, add to vector.
                            # Do the equivalent for closing as well.
                            if (period_index == 0) and (employee.special_properties & PropertyFlag.CAN_OPEN):
                                all_open_capable_employees_shifts.append(main_variables[employee.id][day_index][shift_index])
                            last_period_index = period_count - 1
                            if (period_index == last_period_index) and (employee.special_properties & PropertyFlag.CAN_CLOSE):
                                all_close_capable_employees_shifts.append(main_variables[employee.id][day_index][shift_index])

                # Ensure all periods of the day have enough shifts overlapping them.
                constraint = (lpSum(all_shifts_matching_period) - (
                    period_surplus_variables[day_index][(period_index)])) == self.work_site_demands[(day_index)][period_index]
                self.problem += constraint
                if first_constraint[0]:
                    db_msgs.append(constraint)
                    first_constraint[0] = False

            # For every first and last period per day, ensure that an employee who can open or close is at work.
            constraint = lpSum(all_open_capable_employees_shifts) >= 1
            self.problem += constraint
            if first_constraint[1]:
                    db_msgs.append(constraint)
                    first_constraint[1] = False
            constraint = lpSum(all_close_capable_employees_shifts) >= 1
            self.problem += constraint
            if first_constraint[2]:
                    db_msgs.append(constraint)
                    first_constraint[2] = False

        # Add multiple constraints employee by employee.
        # Iterate over employees.
        for _, employee in self.employees.collection.items():
            employee_weekly_shifts = []
            streaks_start_index = MAXIMUM_CONSECUTIVE_WORKDAYS - employee.current_workday_streak
            # Iterate over every day for each employee.
            for day_index in range(len(employee.shifts)):
                # Any employee mustn't be assigned to more than one shift per day.
                constraint = lpSum([x for x in main_variables[employee.id][day_index]]) + (
                        day_off_surplus_variables[employee.id][day_index]) == 1
                self.problem += constraint
                if first_constraint[3]:
                    db_msgs.append(constraint)
                    first_constraint[3] = False

                # Weekly working hours have lower and upper bounds. Also any worker mustn't work more than the maximum
                # number of shifts defined for them. Resolve weekly shift boundaries for every seven days passed.
                # Weekly shifts are (length, decision variable) -pairs.
                shift_count = len(employee.shifts[day_index])
                for shift_index in range(shift_count):
                    employee_weekly_shifts.append((len(employee.shifts[day_index][shift_index]),
                                                   main_variables[employee.id][day_index][shift_index]))

                if (day_index % 7 == 6):
                    # Limit the number of periods (hours) in weekly shifts.
                    if employee.min_hours == employee.max_hours:
                        constraint = lpSum([l * x for l, x in employee_weekly_shifts]) == employee.min_hours
                        self.problem += constraint
                        if first_constraint[4]:
                            db_msgs.append(constraint)
                            first_constraint[4] = False
                    else:
                        self.problem += lpSum([l * x for l, x in employee_weekly_shifts]) >= employee.min_hours
                        constraint = lpSum([l * x for l, x in employee_weekly_shifts]) <= employee.max_hours
                        self.problem += constraint
                        if first_constraint[4]:
                            db_msgs.append(constraint)
                            first_constraint[4] = False

                    # Limit the number of weekly shifts.
                    constraint = lpSum([x for _, x in employee_weekly_shifts]) <= employee.max_shifts
                    employee_weekly_shifts = []
                    self.problem += constraint
                    if first_constraint[5]:
                        db_msgs.append(constraint)
                        first_constraint[5] = False

                # For every day, ensure that the previous n days have at least one day off. This prevents
                # over n day-long consecutive streaks. Some first days in schedule get ignored.
                if day_index >= streaks_start_index:
                    first_streak_day = day_index - MAXIMUM_CONSECUTIVE_WORKDAYS
                    if first_streak_day < 0:
                        first_streak_day = 0
                    # Use i+1 as the endpoint due to range function behaviour.
                    vars_list = [day_off_surplus_variables[employee.id][i] for i in range(first_streak_day, day_index + 1)]
                    constraint = lpSum(vars_list) >= 1
                    self.problem += constraint
                    if first_constraint[6]:
                        db_msgs.append(constraint)
                        first_constraint[6] = False

            # For each two-day pair, assign a binary variable that takes the value of
            # day1 * day2, i.e. works as an AND logical operator.
            pair_count = len(day_pair_off_variables[employee.id])
            for pair_idx in range(pair_count):
                day1_off = day_off_surplus_variables[employee.id][pair_idx]
                day2_off = day_off_surplus_variables[employee.id][pair_idx + 1]
                pair_off_variable = day_pair_off_variables[employee.id][pair_idx]
                self.problem += pair_off_variable <= day1_off
                self.problem += pair_off_variable <= day2_off
                constraint = pair_off_variable >= day1_off + day2_off - 1
                self.problem += constraint
                if first_constraint[7]:
                    db_msgs.append(constraint)
                    first_constraint[7] = False

            # For each weekend per employee, assign a new binary variable that takes the value of day1*day2, i.e.
            # create an AND logical operator. These will be later combined to ensure enough weekends off for everyone.
            weekend_count = len(weekend_variables[employee.id])
            for weekend_idx in range(weekend_count):
                weekend_variable, day_indices = weekend_variables[employee.id][weekend_idx]
                pair1_off = day_pair_off_variables[employee.id][day_indices[0]]
                if len(day_indices) > 1:
                    pair2_off = day_pair_off_variables[employee.id][day_indices[1]]
                    self.problem += weekend_variable >= pair1_off
                    self.problem += weekend_variable >= pair2_off
                    constraint = weekend_variable <= pair1_off + pair2_off
                    self.problem += constraint
                    if first_constraint[8]:
                        db_msgs.append(constraint)
                        first_constraint[8] = False
                else:
                    # Weekend only has one pair because it was cut in half.
                    constraint = weekend_variable == pair1_off
                    self.problem += constraints
                    if first_constraint[8]:
                        db_msgs.append(constraint)
                        first_constraint[8] = False

            # Add constraints for ensuring the required weekends off.
            try:
                for obligatory_weekend_off_idx in employee.weekends_config['single']:
                    constraint = weekend_variables[employee.id][obligatory_weekend_off_idx][0] == 1
                    self.problem += constraint
                    if first_constraint[9]:
                        db_msgs.append(constraint)
                        first_constraint[9] = False
                    print(f'free weekend {obligatory_weekend_off_idx}', f'for {employee.id}')
            except KeyError:
                # Employee has no single weekend constraints.
                pass
            try:
                key = 'groups'
                for weekend_group_off in employee.weekends_config[key]:
                    minimum_weekends = weekend_group_off[0]
                    weekend_indices = weekend_group_off[1:]
                    constraint = lpSum([weekend_variables[employee.id][i][0] for i in weekend_indices]) >= minimum_weekends
                    self.problem += constraint
                    if first_constraint[10]:
                        db_msgs.append(constraint)
                        first_constraint[10] = False
            except KeyError:
                # Employee has no multi weekend constraints.
                pass

        if self.debug:
            for msg in db_msgs:
                line_len = 50
                print(line_len * '-')
                print(msg)
                print(line_len * '-')
                print()


if __name__ == '__main__':
    # Testing code goes here.
    # Example process to test the program:
    # 1. Create a matrix (nested list or tuple) that holds workforce
    # demands for each day.
    # 2. Create employees.
    # 3. Create scheduler with desired parameters.
    # 4. Run scheduler.
    demands = []
    for i in range(7 * 3):
        demands.append([1, 1, 2, 2, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 4, 4, 3, 3, 2, 2, 2, 2, 1, 1])
    employees = Employees()
    employees.create_dummy_employees(10, demands)
    scheduler = Scheduler(employees, demands, weights=None, start_day=None, shift_start_interval=None, accuracy=None, time_limit=None, debug=False)
    scheduler.run(6000)
    #scheduler.print_results(decision_variables, number_of_weeks=None, status=None, print_daily=False)