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
        recipe_lists = list(map(toRecipeData, request.recipes))
        resources = list(map(toResourceData, request.resources))

        stepResults, resource_infos = main.main(recipe_lists, resources)
        steps = map(toStepOutput, stepResults)
        grpc_resource_infos = map(toGrpcResourceInfo, resource_infos)

        return helloworld_pb2.ProcessReply(steps=steps, resourceInfos=grpc_resource_infos)


def toResourceData(grpc_resource):
    return main.Resource(grpc_resource.id, grpc_resource.amount)
def toRecipeData(grpc_recipe):
    steps = list(map(toStepData, grpc_recipe.steps))
    return main.Recipe(grpc_recipe.id, steps)

def toStepData(grpc_step):
    return main.RecipeStep(grpc_step.recipe_id, grpc_step.id, grpc_step.duration, grpc_step.resource_id, grpc_step.order_number)

def toStepOutput(step):
    return helloworld_pb2.StepOutput(recipe_id=step.recipe_id, step_id=step.recipe_id, resource_id=step.resource_id, duration=step.duration, start_time=step.start_time,
                                           time_line_index=step.time_line_index)

def toGrpcResourceInfo(resource_info):
    return helloworld_pb2.ResourceInfo(id=resource_info.id, amount=resource_info.amount, isUsedMultipleResources=resource_info.isUsedMultipleResources, used_resources_count=resource_info.used_resources_count)

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
