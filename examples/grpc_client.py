#!/usr/bin/env python3
"""Example gRPC client for MaxOS.

This demonstrates how to use the MaxOS gRPC API to:
1. Send text requests
2. Stream operation updates
3. Check system health
"""

import grpc

from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc


def run_handle_text(stub):
    """Demonstrate HandleText RPC."""
    print("\n=== HandleText Example ===")

    # Create a text request
    request = maxos_pb2.TextRequest(
        text="What files are in my home directory?",
        context={"domain": "filesystem"},
    )

    # Call the RPC
    response = stub.HandleText(request)

    print(f"Agent: {response.agent}")
    print(f"Status: {response.status}")
    print(f"Message: {response.message}")
    print(f"Payload: {dict(response.payload)}")


def run_stream_operations(stub):
    """Demonstrate StreamOperations RPC."""
    print("\n=== StreamOperations Example ===")

    # Create a text request
    request = maxos_pb2.TextRequest(
        text="Create a new Python project called 'hello-world'",
        context={"domain": "developer"},
    )

    # Stream operation updates
    for update in stub.StreamOperations(request):
        print(f"Progress: {update.progress}% | Status: {update.status} | {update.message}")


def run_get_health(stub):
    """Demonstrate GetSystemHealth RPC."""
    print("\n=== GetSystemHealth Example ===")

    # Create a health request
    request = maxos_pb2.HealthRequest()

    # Call the RPC
    response = stub.GetSystemHealth(request)

    print(f"Status: {response.status}")
    print(f"Version: {response.version}")
    print(f"Metrics: {dict(response.metrics)}")


def main():
    """Run all examples."""
    # Connect to gRPC server
    channel = grpc.insecure_channel("localhost:50051")
    stub = maxos_pb2_grpc.MaxOSServiceStub(channel)

    print("Connected to MaxOS gRPC server at localhost:50051")

    try:
        # Run examples
        run_get_health(stub)
        run_handle_text(stub)
        run_stream_operations(stub)

    except grpc.RpcError as e:
        print(f"\nError: {e.code()} - {e.details()}")
    finally:
        channel.close()


if __name__ == "__main__":
    main()
