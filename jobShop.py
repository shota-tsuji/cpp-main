import grpc
import logging
from concurrent import futures

import helloworld_pb2
import helloworld_pb2_grpc
import main

class Greeter(helloworld_pb2_grpc.GreeterServicer):

    def SayHello(self, request, context):
        print(f'got a request: {request.name}, {request.state}')
        titles = ["aiko0", "aiko1", "aiko bon"]
        resource_infos = [helloworld_pb2.ResourceInfo(id=1, amount=2, isUsedMultiple=True)]
        return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name, status=2000, titles=titles,
                                         resourceInfos=resource_infos)

    def Process(self, request, context):
        recipe_lists = [
            main.Recipe(0, [main.RecipeStep(0, 10, 1, 0, 1), main.RecipeStep(0, 11, 4, 1, 2)]),
            main.Recipe(1, [main.RecipeStep(1, 12, 1, 0, 1), main.RecipeStep(1, 13, 2, 1, 2)]),
            main.Recipe(2, [main.RecipeStep(2, 14, 1, 0, 1), main.RecipeStep(2, 15, 1, 1, 2)]),
            main.Recipe(3, [main.RecipeStep(3, 18, 2, 0, 1), main.RecipeStep(3, 19, 2, 1, 2)])
        ]

        resources = [
            main.Resource(0, 1),
            main.Resource(1, 2)
        ]
        print(request.recipes)
        print(request.resources)
        stepResults = main.main(recipe_lists, resources)
        #steps = [helloworld_pb2.StepOutput(recipe_id="0", step_id="0", resource_id=1, duration=1, start_time=1, time_line_index=1)]

        steps = map(toStepOutput, stepResults)
        return helloworld_pb2.ProcessReply(steps=steps)


def toStepOutput(step):
    return helloworld_pb2.StepOutput(recipe_id=step.recipe_id, step_id=step.recipe_id, resource_id=step.resource_id, duration=step.duration, start_time=step.start_time,
                                           time_line_index=step.time_line_index)

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
    serve()
