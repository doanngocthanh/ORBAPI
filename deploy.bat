@echo off
REM ORBAPI Docker Deployment Script for Windows
REM Usage: deploy.bat [build|start|stop|restart|logs|status|clean]

setlocal enabledelayedexpansion

set PROJECT_NAME=orbapi-ocr
set IMAGE_NAME=orbapi-ocr:latest
set CONTAINER_NAME=orbapi-ocr-service

REM Colors (limited in Windows CMD)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "NC=[0m"

goto :main

:print_info
    echo %BLUE%[INFO]%NC% %~1
    exit /b

:print_success
    echo %GREEN%[SUCCESS]%NC% %~1
    exit /b

:print_warning
    echo %YELLOW%[WARNING]%NC% %~1
    exit /b

:print_error
    echo %RED%[ERROR]%NC% %~1
    exit /b

:print_header
    echo ================================
    echo   %~1
    echo ================================
    exit /b

:check_docker
    where docker >nul 2>&1
    if errorlevel 1 (
        call :print_error "Docker is not installed!"
        exit /b 1
    )
    
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        call :print_error "Docker Compose is not installed!"
        exit /b 1
    )
    
    call :print_success "Docker and Docker Compose are available"
    exit /b 0

:build_image
    call :print_header "Building Docker Image"
    
    call :print_info "Building %IMAGE_NAME%..."
    docker-compose build --no-cache
    
    if errorlevel 1 (
        call :print_error "Build failed!"
        exit /b 1
    )
    
    call :print_success "Build completed successfully!"
    
    REM Show image size
    for /f "tokens=*" %%i in ('docker images %IMAGE_NAME% --format "{{.Size}}"') do set SIZE=%%i
    call :print_info "Image size: !SIZE!"
    exit /b 0

:start_services
    call :print_header "Starting Services"
    
    call :print_info "Starting %PROJECT_NAME%..."
    docker-compose up -d
    
    if errorlevel 1 (
        call :print_error "Failed to start services!"
        exit /b 1
    )
    
    call :print_success "Services started!"
    
    call :print_info "Waiting for service to be healthy..."
    timeout /t 5 /nobreak >nul
    
    REM Check health (simplified for Windows)
    call :print_info "Checking service health..."
    curl -sf http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        call :print_warning "Service may not be ready yet. Check logs with: deploy.bat logs"
    ) else (
        call :print_success "Service is healthy!"
        call :print_info "Access the API at: http://localhost:8000"
        call :print_info "API Documentation: http://localhost:8000/docs"
    )
    exit /b 0

:stop_services
    call :print_header "Stopping Services"
    
    call :print_info "Stopping %PROJECT_NAME%..."
    docker-compose down
    
    call :print_success "Services stopped!"
    exit /b 0

:restart_services
    call :print_header "Restarting Services"
    
    call :stop_services
    timeout /t 2 /nobreak >nul
    call :start_services
    exit /b 0

:show_logs
    call :print_header "Service Logs"
    
    if "%~1"=="" (
        docker-compose logs -f --tail=100
    ) else (
        docker-compose logs -f --tail=%~1
    )
    exit /b 0

:show_status
    call :print_header "Service Status"
    
    echo.
    call :print_info "Docker Compose Services:"
    docker-compose ps
    
    echo.
    call :print_info "Container Stats:"
    docker stats --no-stream %CONTAINER_NAME% 2>nul
    if errorlevel 1 call :print_warning "Container not running"
    
    echo.
    call :print_info "Health Check:"
    curl -sf http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        call :print_error "API is not responding"
    ) else (
        call :print_success "API is responding"
        curl -s http://localhost:8000/health
    )
    exit /b 0

:clean_up
    call :print_header "Cleanup"
    
    call :print_warning "This will remove all containers, images, and volumes related to %PROJECT_NAME%"
    set /p "CONFIRM=Are you sure? (y/N): "
    
    if /i "!CONFIRM!"=="y" (
        call :print_info "Stopping and removing containers..."
        docker-compose down -v
        
        call :print_info "Removing Docker image..."
        docker rmi %IMAGE_NAME% 2>nul
        
        call :print_success "Cleanup completed!"
    ) else (
        call :print_info "Cleanup cancelled"
    )
    exit /b 0

:test_api
    call :print_header "Testing API"
    
    call :print_info "Testing health endpoint..."
    curl -sf http://localhost:8000/health >nul 2>&1
    if errorlevel 1 (
        call :print_error "Health check failed"
        exit /b 1
    )
    call :print_success "Health check passed"
    
    call :print_info "Testing API documentation..."
    curl -sf http://localhost:8000/docs >nul 2>&1
    if errorlevel 1 (
        call :print_error "API docs not accessible"
        exit /b 1
    )
    call :print_success "API docs accessible"
    
    call :print_success "All tests passed!"
    exit /b 0

:backup_data
    call :print_header "Backup Data"
    
    set BACKUP_DIR=backups
    set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set TIMESTAMP=%TIMESTAMP: =0%
    
    if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%
    
    call :print_info "Backing up models..."
    tar -czf %BACKUP_DIR%\models_%TIMESTAMP%.tar.gz models\ 2>nul
    
    call :print_info "Backing up logs..."
    tar -czf %BACKUP_DIR%\logs_%TIMESTAMP%.tar.gz logs\ 2>nul
    
    call :print_info "Exporting Docker image..."
    docker save %IMAGE_NAME% | gzip > %BACKUP_DIR%\image_%TIMESTAMP%.tar.gz 2>nul
    
    call :print_success "Backup completed in %BACKUP_DIR%\"
    dir %BACKUP_DIR%\*%TIMESTAMP%*
    exit /b 0

:show_usage
    echo.
    echo 🐋 ORBAPI Docker Deployment Script for Windows
    echo.
    echo Usage: deploy.bat [COMMAND]
    echo.
    echo Commands:
    echo   build       Build Docker image
    echo   start       Start services
    echo   stop        Stop services
    echo   restart     Restart services
    echo   logs        Show logs (use: logs 200 for last 200 lines)
    echo   status      Show service status
    echo   test        Test API endpoints
    echo   clean       Remove all containers and images
    echo   backup      Backup models and logs
    echo   help        Show this help message
    echo.
    echo Examples:
    echo   deploy.bat build          # Build the image
    echo   deploy.bat start          # Start services
    echo   deploy.bat logs           # Follow logs
    echo   deploy.bat logs 50        # Show last 50 lines
    echo   deploy.bat status         # Check status
    echo   deploy.bat restart        # Restart services
    echo.
    exit /b 0

:main
    call :check_docker
    if errorlevel 1 exit /b 1
    
    set COMMAND=%~1
    if "%COMMAND%"=="" set COMMAND=help
    
    if "%COMMAND%"=="build" (
        call :build_image
    ) else if "%COMMAND%"=="start" (
        call :start_services
    ) else if "%COMMAND%"=="stop" (
        call :stop_services
    ) else if "%COMMAND%"=="restart" (
        call :restart_services
    ) else if "%COMMAND%"=="logs" (
        call :show_logs %~2
    ) else if "%COMMAND%"=="status" (
        call :show_status
    ) else if "%COMMAND%"=="test" (
        call :test_api
    ) else if "%COMMAND%"=="clean" (
        call :clean_up
    ) else if "%COMMAND%"=="backup" (
        call :backup_data
    ) else if "%COMMAND%"=="help" (
        call :show_usage
    ) else if "%COMMAND%"=="--help" (
        call :show_usage
    ) else if "%COMMAND%"=="-h" (
        call :show_usage
    ) else (
        call :print_error "Unknown command: %COMMAND%"
        echo.
        call :show_usage
        exit /b 1
    )
    
    exit /b 0
