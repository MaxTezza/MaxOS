# gRPC API Documentation

MaxOS now provides a gRPC API alongside the existing REST API, enabling efficient, type-safe, and streaming communication for clients.

## Features

- **Type-safe communication** using Protocol Buffers
- **Streaming support** for long-running operations
- **Concurrent operation** with REST API (gRPC on port 50051, REST on port 8000)
- **Full orchestrator access** - All MaxOS features available via gRPC
- **Health monitoring** endpoint for service status checks

## Architecture

```
┌─────────────┐
│   Client    │
└─────┬───────┘
      │
      ├─── REST API :8000 ───┐
      │                      │
      └─── gRPC API :50051 ──┤
                             │
                    ┌────────▼──────────┐
                    │  AI Orchestrator  │
                    └───────────────────┘
                             │
                    ┌────────▼──────────┐
                    │  Agent Registry   │
                    └───────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install grpcio grpcio-tools
```

### 2. Start the gRPC Server

```bash
# Standalone
python -m max_os.interfaces.grpc.server

# Or via systemd
sudo systemctl start maxos-grpc
```

### 3. Use the Client

```python
import grpc
from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc

# Connect to server
channel = grpc.insecure_channel("localhost:50051")
stub = maxos_pb2_grpc.MaxOSServiceStub(channel)

# Send a text request
request = maxos_pb2.TextRequest(
    text="List files in my home directory",
    context={"domain": "filesystem"}
)
response = stub.HandleText(request)

print(f"Agent: {response.agent}")
print(f"Status: {response.status}")
print(f"Message: {response.message}")
```

## API Reference

### Services

#### MaxOSService

The main service providing access to MaxOS functionality.

##### HandleText

Process a text request and return an agent response.

```protobuf
rpc HandleText(TextRequest) returns (AgentResponse);
```

**Request:**
- `text` (string): The user's natural language input
- `context` (map<string, string>): Optional context information

**Response:**
- `agent` (string): Name of the agent that handled the request
- `status` (string): Status of the operation (success, error, etc.)
- `message` (string): Human-readable response message
- `payload` (map<string, string>): Additional structured data

**Example:**
```python
request = maxos_pb2.TextRequest(
    text="Check system health",
    context={"verbose": "true"}
)
response = stub.HandleText(request)
```

##### StreamOperations

Stream operation updates for long-running tasks.

```protobuf
rpc StreamOperations(TextRequest) returns (stream OperationUpdate);
```

**Request:**
- Same as HandleText

**Response Stream:**
- `progress` (int32): Progress percentage (0-100)
- `status` (string): Current status (started, processing, completed, error)
- `message` (string): Status update message

**Example:**
```python
request = maxos_pb2.TextRequest(
    text="Create a new Python project",
    context={"project_name": "my-app"}
)

for update in stub.StreamOperations(request):
    print(f"{update.progress}% - {update.status}: {update.message}")
```

##### GetSystemHealth

Check the health status of the MaxOS service.

```protobuf
rpc GetSystemHealth(HealthRequest) returns (HealthResponse);
```

**Request:**
- Empty message

**Response:**
- `status` (string): Service health status (healthy, unhealthy)
- `version` (string): MaxOS version
- `metrics` (map<string, string>): System metrics

**Example:**
```python
request = maxos_pb2.HealthRequest()
response = stub.GetSystemHealth(request)
print(f"Status: {response.status}")
print(f"Version: {response.version}")
print(f"Agents: {response.metrics['agents']}")
```

## Examples

### Basic Text Request

```python
#!/usr/bin/env python3
import grpc
from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc

def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = maxos_pb2_grpc.MaxOSServiceStub(channel)
    
    request = maxos_pb2.TextRequest(
        text="What's my system uptime?",
        context={}
    )
    
    response = stub.HandleText(request)
    print(f"{response.agent}: {response.message}")
    
    channel.close()

if __name__ == "__main__":
    main()
```

### Streaming Operations

```python
#!/usr/bin/env python3
import grpc
from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc

def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = maxos_pb2_grpc.MaxOSServiceStub(channel)
    
    request = maxos_pb2.TextRequest(
        text="Deploy my application",
        context={"app_name": "myapp"}
    )
    
    print("Deployment progress:")
    for update in stub.StreamOperations(request):
        print(f"[{update.progress:3d}%] {update.message}")
    
    channel.close()

if __name__ == "__main__":
    main()
```

### Error Handling

```python
import grpc
from max_os.interfaces.grpc.protos import maxos_pb2, maxos_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = maxos_pb2_grpc.MaxOSServiceStub(channel)

try:
    request = maxos_pb2.TextRequest(text="some command")
    response = stub.HandleText(request, timeout=5)
    
    if response.status == "error":
        print(f"Command failed: {response.message}")
    else:
        print(f"Success: {response.message}")
        
except grpc.RpcError as e:
    print(f"RPC failed: {e.code()} - {e.details()}")
finally:
    channel.close()
```

## Deployment

### Systemd Service

A systemd service file is provided for running the gRPC server:

```bash
# Copy service file
sudo cp scripts/maxos-grpc.service /etc/systemd/system/

# Edit paths in the service file
sudo nano /etc/systemd/system/maxos-grpc.service

# Enable and start
sudo systemctl enable maxos-grpc
sudo systemctl start maxos-grpc

# Check status
sudo systemctl status maxos-grpc
```

### Running Both APIs

REST and gRPC APIs can run concurrently:

```bash
# Terminal 1 - REST API
python -m uvicorn max_os.interfaces.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - gRPC API
python -m max_os.interfaces.grpc.server
```

### Docker Compose (Example)

```yaml
version: '3.8'
services:
  maxos-rest:
    image: maxos:latest
    command: uvicorn max_os.interfaces.api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
  
  maxos-grpc:
    image: maxos:latest
    command: python -m max_os.interfaces.grpc.server
    ports:
      - "50051:50051"
```

## Performance

gRPC offers several performance advantages over REST:

- **Binary Protocol**: Smaller message sizes
- **HTTP/2**: Multiplexing, header compression
- **Streaming**: Efficient for long-running operations
- **Type Safety**: Compile-time checks with Protocol Buffers

## Security Considerations

The current implementation uses **insecure channels** for local development. For production:

1. **Use TLS/SSL**: Implement secure channels with certificates
2. **Authentication**: Add token-based or mutual TLS authentication
3. **Authorization**: Implement role-based access control
4. **Rate Limiting**: Add request rate limiting
5. **Network Security**: Use firewall rules to restrict access

Example secure channel:

```python
# Server side
server_credentials = grpc.ssl_server_credentials(
    [(private_key, certificate)]
)
server.add_secure_port("[::]:50051", server_credentials)

# Client side
channel_credentials = grpc.ssl_channel_credentials(
    root_certificates=ca_cert
)
channel = grpc.secure_channel("localhost:50051", channel_credentials)
```

## Testing

Run the gRPC tests:

```bash
pytest tests/test_grpc_server.py -v
```

Run all tests including gRPC:

```bash
pytest tests/
```

## Troubleshooting

### Connection Refused

If you get "Connection refused" errors:

1. Check the server is running: `ps aux | grep grpc`
2. Verify the port: `netstat -tulpn | grep 50051`
3. Check firewall rules

### Proto Import Errors

If you get import errors for proto files:

```bash
# Regenerate proto files
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. \
    max_os/interfaces/grpc/protos/maxos.proto
```

### Redis Connection Errors

The orchestrator requires Redis. Ensure Redis is running:

```bash
# Start Redis
sudo systemctl start redis

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

For testing without Redis, use the fakeredis package (already in dev dependencies).

## Future Enhancements

- [ ] TLS/SSL support
- [ ] Authentication and authorization
- [ ] Bidirectional streaming for interactive sessions
- [ ] gRPC-Web support for browser clients
- [ ] Load balancing and service mesh integration
- [ ] Metrics and tracing (OpenTelemetry)

## References

- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers Guide](https://protobuf.dev/)
- [MaxOS Architecture](ARCHITECTURE.md)
