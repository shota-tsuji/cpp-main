"""Minimal jobshop example."""
import collections
from ortools.sat.python import cp_model

class RecipeStep:

    def __init__(self, recipe_id, step_id, duration, resource_id, order_number):
        self.recipe_id = recipe_id
        self.step_id = step_id
        self.duration = duration
        self.resource_id = resource_id
        self.order_number = order_number

class Resource:

    def __init__(self, resource_id, amount):
        self.resource_id = resource_id
        self.amount = amount


def main():
    resources = [
        Resource(0, 1),
        Resource(1, 2)
    ]

    """Minimal jobshop problem."""
    # Data.
    recipes_data = [  # task = (machine_id, processing_time).
        [(0, 1), (1, 4)],  # recipe0
        [(0, 1), (1, 2)],  # recipe1
    ]
    recipe_lists = [
        [RecipeStep(0, 10, 1, 0, 1), RecipeStep(0, 11, 4, 1, 2)],
        [RecipeStep(1, 12, 1, 0, 1), RecipeStep(1, 13, 2, 1, 2)]
    ]

    all_machines = range(len(resources))
    # Computes horizon dynamically as the sum of all durations.
    horizon = sum(task[1] for job in recipes_data for task in job)

    # Create the model.
    model = cp_model.CpModel()

    # Named tuple to store information about created variables.
    task_type = collections.namedtuple('task_type', 'start end interval')
    # Named tuple to manipulate solution information.
    assigned_task_type = collections.namedtuple('assigned_task_type',
                                                'start job index duration')

    # Creates job intervals and add to the corresponding machine lists.
    all_tasks = {}
    resource_intervals = collections.defaultdict(list)

    for recipe_id, recipe in enumerate(recipe_lists):
        for step_id, step in enumerate(recipe):
            suffix = f'_{recipe_id}_{step_id}'
            start_var = model.NewIntVar(0, horizon, 'start' + suffix)
            end_var = model.NewIntVar(0, horizon, 'end' + suffix)
            interval_var = model.NewIntervalVar(start_var, step.duration, end_var,
                                                'interval' + suffix)
            all_tasks[recipe_id, step_id] = task_type(start=start_var,
                                                   end=end_var,
                                                   interval=interval_var)
            resource_intervals[step.resource_id].append(interval_var)

    # Disjunctive constraint 0: Resource capacity
    for resource in resources:
        intervals = resource_intervals[resource.resource_id]
        if resource.amount == 1: #Each resource use does not overlap if its amount is one.
            model.AddNoOverlap(intervals)
        else: # Capacity of resources used simultaneously
            # Each interval requires one resource in its duration.
            demands = [1] * len(intervals)
            model.AddCumulative(intervals, demands, resource.amount)

    # Precedences inside a job.
    for job_id, job in enumerate(recipes_data):
        for task_id in range(len(job) - 1):
            model.Add(all_tasks[job_id, task_id +
                                1].start >= all_tasks[job_id, task_id].end)

    # Makespan objective.
    obj_var = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(obj_var, [
        all_tasks[job_id, len(job) - 1].end
        for job_id, job in enumerate(recipes_data)
    ])
    model.Minimize(obj_var)

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print('Solution:')
        # Create one list of assigned tasks per machine.
        assigned_jobs = collections.defaultdict(list)
        for recipe_id, recipe in enumerate(recipe_lists):
            for step_id, step in enumerate(recipe):
                assigned_jobs[step.resource_id].append(
                    assigned_task_type(start=solver.Value(
                        all_tasks[recipe_id, step_id].start),
                                       job=recipe_id,
                                       index=step_id,
                                       duration=step.duration))

        # Create per machine output lines.
        output = ''
        for machine in all_machines:
            # Sort by starting time.
            assigned_jobs[machine].sort()
            sol_line_tasks = 'Machine ' + str(machine) + ': '
            sol_line = '           '

            for assigned_task in assigned_jobs[machine]:
                name = 'job_%i_task_%i' % (assigned_task.job,
                                           assigned_task.index)
                # Add spaces to output to align columns.
                sol_line_tasks += '%-15s' % name

                start = assigned_task.start
                duration = assigned_task.duration
                sol_tmp = '[%i,%i]' % (start, start + duration)
                # Add spaces to output to align columns.
                sol_line += '%-15s' % sol_tmp

            sol_line += '\n'
            sol_line_tasks += '\n'
            output += sol_line_tasks
            output += sol_line

        # Finally print the solution found.
        print(f'Optimal Schedule Length: {solver.ObjectiveValue()}')
        print(output)
    else:
        print('No solution found.')

    # Statistics.
    print('\nStatistics')
    print('  - conflicts: %i' % solver.NumConflicts())
    print('  - branches : %i' % solver.NumBranches())
    print('  - wall time: %f s' % solver.WallTime())


if __name__ == '__main__':
    main()
