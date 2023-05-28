"""Minimal jobshop example."""
import collections
from ortools.sat.python import cp_model
import functools

from concurrent import futures
import logging

import grpc
import helloworld_pb2
import helloworld_pb2_grpc


class Greeter(helloworld_pb2_grpc.GreeterServicer):

    def SayHello(self, request, context):
        print(f'got a request: {request.name}, {request.state}')
        titles = ["aiko0", "aiko1", "aiko bon"]
        resource_infos = [helloworld_pb2.ResourceInfo(id=1, amount=2, isUsedMultiple=True)]
        return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name, status=2000, titles=titles, resourceInfos=resource_infos)

    def Process(self, request, context):
        steps = [helloworld_pb2.StepOutput(recipe_id="0", step_id="0", resource_id=1, duration=1, start_time=1, time_line_index=1)]
        return helloworld_pb2.ProcessReply(steps=steps)


class RecipeStep:

    def __init__(self, recipe_id, step_id, duration, resource_id, order_number):
        self.recipe_id = recipe_id
        self.id = step_id
        self.duration = duration
        self.resource_id = resource_id
        self.order_number = order_number

    def __str__(self):
        return f'RecipeStep: {self.recipe_id}, {self.id}, {self.resource_id}, {self.order_number}'

    def __repr__(self):
        return f'RecipeStep: {self.recipe_id}, {self.id}, {self.resource_id}, {self.order_number}'

class Recipe:

    def __init__(self, recipe_id, steps):
        self.id = recipe_id
        self.steps = steps


class Resource:

    def __init__(self, resource_id, amount):
        self.resource_id = resource_id
        self.amount = amount


class StepOutput:

    def __init__(self, recipe_id, step_id, duration, resource_id, start_time, time_line_index):
        self.recipe_id = recipe_id
        self.step_id = step_id
        self.duration = duration
        self.resource_id = resource_id
        self.start_time = start_time
        self.time_line_index = time_line_index

    def __str__(self):
        end_time = self.start_time + self.duration
        return f'(resource={self.resource_id}, start={self.start_time}, end={end_time}, recipe={self.recipe_id}, step={self.step_id}, tli={self.time_line_index})'

    def __repr__(self):
        end_time = self.start_time + self.duration
        return f'(resource={self.resource_id}, start={self.start_time}, end={end_time}, recipe={self.recipe_id}, step={self.step_id}, tli={self.time_line_index})'



def main():
    resources = [
        Resource(0, 1),
        Resource(1, 2)
    ]

    recipe_lists = [
        Recipe(0, [RecipeStep(0, 10, 1, 0, 1), RecipeStep(0, 11, 4, 1, 2)]),
        Recipe(1, [RecipeStep(1, 12, 1, 0, 1), RecipeStep(1, 13, 2, 1, 2)]),
        Recipe(2, [RecipeStep(2, 14, 1, 0, 1), RecipeStep(2, 15, 1, 1, 2)]),
        Recipe(3, [RecipeStep(3, 18, 2, 0, 1), RecipeStep(3, 19, 2, 1, 2)])
    ]

    # Named tuple to store information about created variables.
    task_type = collections.namedtuple('task_type', 'start end interval order step_id duration, resource_id, recipe_id')

    # Computes horizon dynamically as the sum of all durations.
    horizon = sum(step.duration for recipe in recipe_lists for step in recipe.steps)

    model = cp_model.CpModel()

    # Creates job intervals and add to the corresponding machine lists.
    all_steps = {}
    resource_intervals = collections.defaultdict(list)

    for recipe in recipe_lists:
        for step in recipe.steps:
            suffix = f'_{recipe.id}_{step.id}'

            start_var = model.NewIntVar(0, horizon, 'start' + suffix)
            end_var = model.NewIntVar(0, horizon, 'end' + suffix)
            interval_var = model.NewIntervalVar(start_var, step.duration, end_var,
                                                'interval' + suffix)
            task = task_type(start=start_var, end=end_var, interval=interval_var, order=step.order_number,
                             step_id=step.id, duration=step.duration, resource_id=step.resource_id, recipe_id=step.recipe_id)

            if recipe.id in all_steps:
                all_steps[recipe.id].append(task)
            else:
                all_steps[recipe.id] = [task]

            resource_intervals[step.resource_id].append(interval_var)

    model = set_resource_constraint(model, resources, resource_intervals)
    model = set_step_constraint(model, all_steps)
    model = set_time_constraint(model, horizon, all_steps)

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        step_outputs = get_step_outputs(solver, all_steps, resources)
        for step_output in step_outputs:
            print(step_output)

        print(f'Optimal Schedule Length: {solver.ObjectiveValue()}')
    else:
        print('No solution found.')

    print('  - conflicts: %i' % solver.NumConflicts())
    print('  - wall time: %f s' % solver.WallTime())


# Disjunctive constraint 0: Resource capacity
def set_resource_constraint(model, resources, resource_intervals):
    for resource in resources:
        intervals = resource_intervals[resource.resource_id]
        if resource.amount == 1:  # Each resource use does not overlap if its amount is one.
            model.AddNoOverlap(intervals)
        else:  # Capacity of resources used simultaneously
            # Each interval requires one resource in its duration.
            demands = [1] * len(intervals)
            model.AddCumulative(intervals, demands, resource.amount)

    return model


# Disjunctive constraint 1: Sequential recipe process
def set_step_constraint(model, all_steps):
    for recipe_id, steps in all_steps.items():
        steps.sort(key=lambda step: step.order)

        # Next step does not start until current step ends
        for i in range(len(steps) - 1):
            model.Add(steps[i + 1].start >= steps[i].end)

    return model


# Disjunctive constraint 2: Total time is at most sum of all recipe process times
def set_time_constraint(model, horizon, all_steps):
    # Objective value (total time) which will be minimized.
    obj_var = model.NewIntVar(0, horizon, 'timeline')

    # select end time of last step of recipes
    recipe_ends = []
    for recipe_id, steps in all_steps.items():
        last_step = sorted(steps, key=lambda step: step.order)[-1]
        # print(last_step)
        recipe_ends.append(last_step.end)

    model.AddMaxEquality(obj_var, recipe_ends)
    model.Minimize(obj_var)

    return model


# recipe_lists と variable.start の組み合わせを取得
def get_step_outputs(solver, all_steps, resources):
    step_outputs = []
    resources_use = {}
    resources_dict = {}
    for resource in resources:
        resources_use[resource.resource_id] = []
        resources_dict[resource.resource_id] = resource.amount

    for steps in all_steps.values():
        for step in steps:
            if resources_dict[step.resource_id] > 1:
                resources_use[step.resource_id].append(step)
                continue
            start_time = solver.Value(step.start)
            step_outputs.append(StepOutput(step.recipe_id, step.step_id, step.duration, step.resource_id, start_time, 0))

    def step_cmp(a, b):
        if solver.Value(a.start) < solver.Value(b.start):
            return -1
        elif solver.Value(a.start) == solver.Value(b.start):
            if solver.Value(a.end) < solver.Value(b.end):
                return -1
            elif solver.Value(a.end) > solver.Value(b.end):
                return 1
            else:
                return 0
        else:
            return 1

    #print(resources_use)
    for resource in filter(lambda r: r.amount > 1, resources):
        timelines = [None] * resource.amount
        print(timelines)
        steps = resources_use[resource.resource_id]
        #resources_use[resource.resource_id].reverse()
        steps.sort(key=functools.cmp_to_key(step_cmp))
        #print(steps)

        for step in steps:
            start_time = solver.Value(step.start)

            # loop until current step is scheduled in one of timelines
            for i, timeline in enumerate(timelines):
                print(timelines)
                if timeline is None:
                    timelines[i] = [step]
                    step_outputs.append(StepOutput(step.recipe_id, step.step_id, step.duration, step.resource_id, start_time, i))
                    break
                else:
                    # compare to check if the step is scheduled
                    print(f'timeline: {timeline[-1].end}')
                    print(f'step: {step}')
                    if solver.Value(timeline[-1].end) <= solver.Value(step.start):
                        timeline.append(step)
                        step_outputs.append(StepOutput(step.recipe_id, step.step_id, step.duration, step.resource_id, start_time, i))

        print(timelines)

    return step_outputs

def serve():
    port = '50051'
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    main()
    serve()
