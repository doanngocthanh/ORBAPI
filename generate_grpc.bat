@echo off
echo Generating gRPC Python files from protobuf...

python -m grpc_tools.protoc --proto_path=protos --python_out=. --grpc_python_out=. protos/ocr.proto

if %errorlevel% equ 0 (
    echo.
    echo ✓ Generated gRPC Python files successfully:
    echo   - ocr_pb2.py ^(protobuf messages^)
    echo   - ocr_pb2_grpc.py ^(gRPC service stubs^)
    echo.
) else (
    echo.
    echo ✗ Error generating gRPC files
    echo Make sure grpcio-tools is installed: pip install grpcio-tools
    echo.
)

pause
