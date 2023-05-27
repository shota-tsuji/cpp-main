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

    def __str__(self):
        return f'RecipeStep: {self.recipe_id}, {self.step_id}, {self.resource_id}, {self.order_number}'

    def __repr__(self):
        return f'RecipeStep: {self.recipe_id}, {self.step_id}, {self.resource_id}, {self.order_number}'

class Resource:

    def __init__(self, resource_id, amount):
        self.resource_id = resource_id
        self.amount = amount

class StepOutput:

    def __init__(self, recipe_id, step_id, duration, resource_id, start_time):
        self.recipe_id = recipe_id
        self.step_id = step_id
        self.duration = duration
        self.resource_id = resource_id
        self.start_time = start_time

    def to_string(self):
        end_time = self.start_time + self.duration
        return f'({self.resource_id}, [{self.start_time}, {end_time}], [{self.recipe_id}, {self.step_id}])'

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

    # Computes horizon dynamically as the sum of all durations.
    horizon = sum(step.duration for recipe in recipe_lists for step in recipe)

    # Create the model.
    model = cp_model.CpModel()

    # Named tuple to store information about created variables.
    task_type = collections.namedtuple('task_type', 'start end interval order step_id duration, resource_id')
    # Named tuple to manipulate solution information.

    # Creates job intervals and add to the corresponding machine lists.
    all_steps = {}
    resource_intervals = collections.defaultdict(list)

    for recipe_id, recipe in enumerate(recipe_lists):
        for step_id, step in enumerate(recipe):
            suffix = f'_{recipe_id}_{step_id}'
            start_var = model.NewIntVar(0, horizon, 'start' + suffix)
            end_var = model.NewIntVar(0, horizon, 'end' + suffix)
            interval_var = model.NewIntervalVar(start_var, step.duration, end_var,
                                                'interval' + suffix)
            # use as dict
            task = task_type(start=start_var, end=end_var, interval=interval_var, order=step.order_number, step_id=step.step_id, duration=step.duration, resource_id=step.resource_id)
            if recipe_id in all_steps:
                all_steps[recipe_id].append(task)
            else:
                all_steps[recipe_id] = [task]
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

    # Disjunctive constraint 1: Sequential recipe process
    for recipe_id, steps in all_steps.items():
        steps.sort(key=lambda step: step.order)

        # Next step does not start until current step ends
        for i in range(len(steps) - 1):
            model.Add(steps[i + 1].start >= steps[i].end)

    # Objective value (total time) which will be minimized.
    obj_var = model.NewIntVar(0, horizon, 'timeline')

    # select end time of last step of recipes
    recipe_ends = []
    for recipe_id, steps in all_steps.items():
        last_step = sorted(steps, key=lambda step: step.order)[-1]
        #print(last_step)
        recipe_ends.append(last_step.end)

    # Disjunctive constraint 2: Total time is at most sum of all recipe process times
    model.AddMaxEquality(obj_var, recipe_ends)
    model.Minimize(obj_var)

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print('Solution:')
        # use as dict
        step_outputs = get_step_outputs(solver, all_steps)
        for step_output in step_outputs:
            print(step_output.to_string())

        print(f'Optimal Schedule Length: {solver.ObjectiveValue()}')
    else:
        print('No solution found.')

    # Statistics.
    print('\nStatistics')
    print('  - conflicts: %i' % solver.NumConflicts())
    print('  - branches : %i' % solver.NumBranches())
    print('  - wall time: %f s' % solver.WallTime())

# recipe_lists と variable.start の組み合わせを取得
def get_step_outputs(solver, all_steps):
    step_outputs = []
    for recipe_id, steps in all_steps.items():
        for step in steps:
            start_time = solver.Value(step.start)
            step_outputs.append(StepOutput(recipe_id, step.step_id, step.duration, step.resource_id, start_time))

    return step_outputs

if __name__ == '__main__':
    main()
