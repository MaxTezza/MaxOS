"""gRPC server implementation for MaxOS."""

import asyncio
import json
from concurrent import futures
from typing import Iterator

import grpc
import structlog

from max_os.core.orchestrator import AIOperatingSystem
from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc


class MaxOSServiceServicer(maxos_pb2_grpc.MaxOSServiceServicer):
    """Implementation of MaxOSService gRPC service."""

    def __init__(self, orchestrator: AIOperatingSystem | None = None):
        self.orchestrator = orchestrator or AIOperatingSystem()
        self.logger = structlog.get_logger("max_os.grpc")
        self.logger.info("gRPC service initialized")

    def HandleText(
        self, request: maxos_pb2.TextRequest, context: grpc.ServicerContext
    ) -> maxos_pb2.AgentResponse:
        """Handle a text request and return agent response."""
        self.logger.info("HandleText called", extra={"text": request.text})

        try:
            # Convert context map to dict
            ctx = dict(request.context) if request.context else {}

            # Run async handler in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(self.orchestrator.handle_text(request.text, ctx))
            finally:
                loop.close()

            # Convert payload dict to map<string, string> for proto
            payload_map = {}
            if response.payload:
                for key, value in response.payload.items():
                    # Convert all values to strings for proto compatibility
                    if isinstance(value, (dict, list)):
                        payload_map[key] = json.dumps(value)
                    else:
                        payload_map[key] = str(value)

            return maxos_pb2.AgentResponse(
                agent=response.agent,
                status=response.status,
                message=response.message,
                payload=payload_map,
            )
        except Exception as e:
            self.logger.exception("Error handling text request")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return maxos_pb2.AgentResponse(
                agent="grpc_server",
                status="error",
                message=f"Error processing request: {str(e)}",
                payload={},
            )

    def StreamOperations(
        self, request: maxos_pb2.TextRequest, context: grpc.ServicerContext
    ) -> Iterator[maxos_pb2.OperationUpdate]:
        """Stream operation updates for long-running operations."""
        self.logger.info("StreamOperations called", extra={"text": request.text})

        try:
            # Convert context map to dict
            ctx = dict(request.context) if request.context else {}

            # Yield initial update
            yield maxos_pb2.OperationUpdate(
                progress=0, status="started", message="Processing request..."
            )

            # Process the request
            yield maxos_pb2.OperationUpdate(
                progress=30, status="processing", message="Analyzing intent..."
            )

            # Run async handler in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(self.orchestrator.handle_text(request.text, ctx))
            finally:
                loop.close()

            yield maxos_pb2.OperationUpdate(
                progress=70, status="processing", message="Executing agent..."
            )

            # Final update with result
            if response.status == "success":
                yield maxos_pb2.OperationUpdate(
                    progress=100,
                    status="completed",
                    message=f"Success: {response.message}",
                )
            else:
                yield maxos_pb2.OperationUpdate(
                    progress=100,
                    status="error",
                    message=f"Error: {response.message}",
                )

        except Exception as e:
            self.logger.exception("Error in streaming operation")
            yield maxos_pb2.OperationUpdate(
                progress=100,
                status="error",
                message=f"Error processing request: {str(e)}",
            )

    def GetSystemHealth(
        self, request: maxos_pb2.HealthRequest, context: grpc.ServicerContext
    ) -> maxos_pb2.HealthResponse:
        """Get system health status."""
        self.logger.debug("GetSystemHealth called")

        try:
            metrics = {
                "orchestrator": "ready",
                "agents": str(len(self.orchestrator.agents)),
                "memory_limit": str(self.orchestrator.memory.limit),
            }

            return maxos_pb2.HealthResponse(
                status="healthy",
                version="0.1.0",
                metrics=metrics,
            )
        except Exception as e:
            self.logger.exception("Error getting system health")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return maxos_pb2.HealthResponse(
                status="unhealthy",
                version="0.1.0",
                metrics={"error": str(e)},
            )


def serve(port: int = 50051, orchestrator: AIOperatingSystem | None = None):
    """Start the gRPC server."""
    logger = structlog.get_logger("max_os.grpc")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    maxos_pb2_grpc.add_MaxOSServiceServicer_to_server(
        MaxOSServiceServicer(orchestrator), server
    )

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server")
        server.stop(0)


if __name__ == "__main__":
    serve()
