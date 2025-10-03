#!/bin/bash

# Generate Python gRPC code from protobuf
python -m grpc_tools.protoc \
    --proto_path=protos \
    --python_out=. \
    --grpc_python_out=. \
    protos/ocr.proto

echo "Generated gRPC Python files:"
echo "- ocr_pb2.py (protobuf messages)"
echo "- ocr_pb2_grpc.py (gRPC service stubs)"
