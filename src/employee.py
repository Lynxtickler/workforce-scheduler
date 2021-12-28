"""
Contains employee class.
"""


from .constants import *
from .helpers import *


class Employee:
    """Employee class with required properties.

    Attributes:
        id:
            Unique ID for every employee.
        name:
            A string representing the name of the employee.
        type_of_contract:
            An enumerator representing full-time or part-time contracts.
        min_hours:
            An integer defining the employee's minimum weekly hours.
        max_hours:
            An integer defining the employee's maximum weekly hours. Defaults to match minimum hours.
        max_shifts:
            An integer representing the maximum amount of shifts per week for the employee. Defaults to 5.
        seniority:
            A float representing employee's seniority. Defaults to 0.
        special_properties:
            PropertyFlag flags for special properties the employee satisfies. For example can open or close business.
        current_workday_streak:
            An integer representing the length of the streak of days the
            employee has worked at the end of the previous schedule.
        weekends_config:
            A dictionary where 'single' is a list of all weekend indices that the employee must have off duty. The item
            for the key 'groups' is a list of lists, where the first items of the innermost lists define the minimum
            weekends off selected from the list. The rest of the items are the weekend indices that belong to the group.
        preferences:
            A dictionary for setting special preferences for shifts. Defaults to an empty dictionary.
    """

    def __init__(self, new_id, name, type_of_contract, min_hours, max_hours=None, max_shifts=None, seniority=None,
                 special_properties=None, current_workday_streak=None, weekends_config=None, preferences=None):
        """Initialise employee."""
        self.id = new_id
        self.name = name
        self.type_of_contract = type_of_contract
        self.min_hours = min_hours
        self.max_hours = min_hours if (max_hours is None) else max_hours
        self.max_shifts = DEFAULT_WEEKLY_MAXIMUM_SHIFTS if (max_shifts is None) else max_shifts
        self.seniority = 0 if (seniority is None) else seniority
        self.special_properties = PropertyFlag.NONE if (special_properties is None) else special_properties
        self.current_workday_streak = 0 if (current_workday_streak is None) else current_workday_streak
        self.weekends_config = {} if (weekends_config is None) else weekends_config
        self.preferences = {} if (preferences is None) else preferences

    def __str__(self):
        """Return string representation of employee."""
        return self.to_text()

    def to_text(self):
        """Return a text representation of employee."""
        min_h = int(self.min_hours / PERIODS_PER_HOUR)
        max_h = int(self.max_hours / PERIODS_PER_HOUR)
        hour_range = f'{min_h}-{max_h}'
        padding = ''
        if self.min_hours == self.max_hours and False:
            hour_range = str(int(self.min_hours / PERIODS_PER_HOUR))
            padding = '   '
        preferences_text = {}
        for day, day_preference in self.preferences.items():
            preferences_text[day] = {}
            for shift, flag in day_preference.items():
                preferences_text[day][shift] = int(flag)
        return str(f'ID: {self.id}, Name: {self.name}, ' +
                   f'Contract: {self.type_of_contract.name}, ' +
                   f'Hours: {hour_range},{padding} ' +
                   f'Max shifts: {self.max_shifts}, ' +
                   f'Seniority: {self.seniority}, ' +
                   f'Properties: {self.special_properties}, ' +
                   f'Streak: {self.current_workday_streak},\n ' +
                   f'Weekends: {self.weekends_config}, ' +
                   f'Preferences: {preferences_text}')

    def set_employee_shifts(self, work_site_demands):
        """Find all employee's plausible shifts.

        Assign the list of shifts as an attribute to the employee.

        Args:
            work_site_demands:
                A list of tuples defining work site demands. Shifts will be generated in respect to opening hours.
        """
        all_shifts = []
        for day_index in range(len(work_site_demands)):
            todays_shifts = []
            days_preferences = None
            try:
                # Try to set preferences set for today.
                days_preferences = self.preferences[day_index]
            except KeyError:
                pass
            minimum_shift_length = MINIMUM_SHIFT_IN_PERIODS
            if self.special_properties & PropertyFlag.IS_IN_SCHOOL:
                minimum_shift_length = 2 * PERIODS_PER_HOUR
            for shift_length in range(minimum_shift_length, MAXIMUM_SHIFT_IN_PERIODS + 1):
                workday_periods = len(work_site_demands[day_index])
                todays_shifts += self.get_possible_shifts_for_day(workday_periods, shift_length, days_preferences)
            all_shifts.append(todays_shifts)
        self.shifts = all_shifts

    def get_possible_shifts_for_day(self, number_of_periods, shift_length=None, days_preferences=None):
        """Get all consecutive defined-length sets of periods from a given set of periods.

        Args:
            number_of_periods:
                An integer representing the number of total periods on given day.
            shift_length:
                An integer defining the length of shift in periods.
            days_preferences:
                Employee's preferences for today.

        Returns:
            A list of possible shifts, unavailabilities factored in.
        """
        if shift_length is None:
            shift_length = DEFAULT_SHIFT_IN_PERIODS
        if days_preferences is None:
            days_preferences = {}
        possible_shifts = []
        for i in range(0, number_of_periods - shift_length + 1, SHIFT_START_INTERVAL):
            eligible_shift = True
            try:
                for shift_index in days_preferences:
                    if (
                        (shift_index >= i) and
                        (shift_index < i + shift_length) and
                        (days_preferences[shift_index] == Preference.UNAVAILABLE)
                    ):
                        eligible_shift = False
            except (AttributeError):
                # Expected if preferences is not defined or it's an empty dictionary.
                pass
            if eligible_shift:
                shift_as_periods = [x for x in range(i, i + shift_length)]
                possible_shifts.append(shift_as_periods)
        return possible_shifts
