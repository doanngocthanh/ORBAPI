#!/bin/bash

# ORBAPI Docker Deployment Script
# Usage: ./deploy.sh [build|start|stop|restart|logs|status|clean]

set -e

PROJECT_NAME="orbapi-ocr"
IMAGE_NAME="orbapi-ocr:latest"
CONTAINER_NAME="orbapi-ocr-service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are available"
}

# Build image
build_image() {
    print_header "Building Docker Image"
    
    print_info "Building $IMAGE_NAME..."
    docker-compose build --no-cache
    
    print_success "Build completed successfully!"
    
    # Show image size
    SIZE=$(docker images $IMAGE_NAME --format "{{.Size}}")
    print_info "Image size: $SIZE"
}

# Start services
start_services() {
    print_header "Starting Services"
    
    print_info "Starting $PROJECT_NAME..."
    docker-compose up -d
    
    print_success "Services started!"
    
    # Wait for health check
    print_info "Waiting for service to be healthy..."
    sleep 5
    
    # Check health
    for i in {1..30}; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Service is healthy!"
            print_info "Access the API at: http://localhost:8000"
            print_info "API Documentation: http://localhost:8000/docs"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    
    print_warning "Service health check timed out. Check logs with: ./deploy.sh logs"
}

# Stop services
stop_services() {
    print_header "Stopping Services"
    
    print_info "Stopping $PROJECT_NAME..."
    docker-compose down
    
    print_success "Services stopped!"
}

# Restart services
restart_services() {
    print_header "Restarting Services"
    
    stop_services
    sleep 2
    start_services
}

# Show logs
show_logs() {
    print_header "Service Logs"
    
    if [ -z "$1" ]; then
        docker-compose logs -f --tail=100
    else
        docker-compose logs -f --tail=$1
    fi
}

# Show status
show_status() {
    print_header "Service Status"
    
    echo ""
    print_info "Docker Compose Services:"
    docker-compose ps
    
    echo ""
    print_info "Container Stats:"
    docker stats --no-stream $CONTAINER_NAME 2>/dev/null || print_warning "Container not running"
    
    echo ""
    print_info "Health Check:"
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_success "API is responding"
        curl -s http://localhost:8000/health | jq '.' 2>/dev/null || echo "Install jq for pretty JSON output"
    else
        print_error "API is not responding"
    fi
}

# Clean up
clean_up() {
    print_header "Cleanup"
    
    print_warning "This will remove all containers, images, and volumes related to $PROJECT_NAME"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping and removing containers..."
        docker-compose down -v
        
        print_info "Removing Docker image..."
        docker rmi $IMAGE_NAME 2>/dev/null || print_warning "Image not found"
        
        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled"
    fi
}

# Test API
test_api() {
    print_header "Testing API"
    
    print_info "Testing health endpoint..."
    if curl -sf http://localhost:8000/health > /dev/null; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        return 1
    fi
    
    print_info "Testing API documentation..."
    if curl -sf http://localhost:8000/docs > /dev/null; then
        print_success "API docs accessible"
    else
        print_error "API docs not accessible"
        return 1
    fi
    
    print_success "All tests passed!"
}

# Backup
backup_data() {
    print_header "Backup Data"
    
    BACKUP_DIR="backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p $BACKUP_DIR
    
    print_info "Backing up models..."
    tar -czf $BACKUP_DIR/models_$TIMESTAMP.tar.gz models/ 2>/dev/null || print_warning "Models directory not found"
    
    print_info "Backing up logs..."
    tar -czf $BACKUP_DIR/logs_$TIMESTAMP.tar.gz logs/ 2>/dev/null || print_warning "Logs directory not found"
    
    print_info "Exporting Docker image..."
    docker save $IMAGE_NAME | gzip > $BACKUP_DIR/image_$TIMESTAMP.tar.gz 2>/dev/null || print_warning "Image not found"
    
    print_success "Backup completed in $BACKUP_DIR/"
    ls -lh $BACKUP_DIR/*$TIMESTAMP*
}

# Show usage
show_usage() {
    cat << EOF
🐋 ORBAPI Docker Deployment Script

Usage: ./deploy.sh [COMMAND]

Commands:
  build       Build Docker image
  start       Start services
  stop        Stop services
  restart     Restart services
  logs        Show logs (use: logs 200 for last 200 lines)
  status      Show service status
  test        Test API endpoints
  clean       Remove all containers and images
  backup      Backup models and logs
  help        Show this help message

Examples:
  ./deploy.sh build          # Build the image
  ./deploy.sh start          # Start services
  ./deploy.sh logs           # Follow logs
  ./deploy.sh logs 50        # Show last 50 lines
  ./deploy.sh status         # Check status
  ./deploy.sh restart        # Restart services

EOF
}

# Main script
main() {
    check_docker
    
    case "${1:-help}" in
        build)
            build_image
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs "${2:-100}"
            ;;
        status)
            show_status
            ;;
        test)
            test_api
            ;;
        clean)
            clean_up
            ;;
        backup)
            backup_data
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
