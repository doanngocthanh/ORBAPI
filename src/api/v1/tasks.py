import os
from urllib import response
from fastapi import APIRouter
from service.detect.CCCDDetector import CCCDDetector
from config import PtConfig
from service.yolo.YOLODetector import DetectionConfig
from fastapi import File, UploadFile
import io
from PIL import Image
import numpy as np
import json
import uuid
from datetime import datetime
from typing import Dict

router = APIRouter(
    prefix="/api/tasks",
    tags=["VietNam Citizens Card Scanner"],
    responses={
        404: {"description": "Not found"}
    }
)
LOG_DIR = "logs/tasks"
os.makedirs(LOG_DIR, exist_ok=True)
@router.get("/")
async def list_tasks():
# Get pagination parameters
    page = 1
    page_size = None  # Default to all
    offset = (page - 1) * page_size if page_size else 0
        
    # Read all task files from disk
    task_files = sorted(
        [f for f in os.listdir(LOG_DIR) if f.endswith('.json')],
        reverse=True  # Most recent first
    )
        
    # Apply pagination if page_size is specified
    if page_size:
        task_files = task_files[offset:offset + page_size]
        
    # Load task IDs from files
    task_ids = []
    for filename in task_files:
        try:
            task_id = filename.replace('.json', '')
            task_ids.append(task_id)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    return {"tasks": task_ids}
@router.get("/{task_id}")
async def get_task(task_id: str):
    task_file = os.path.join(LOG_DIR, f"{task_id}.json")
    if not os.path.isfile(task_file):
        return {"error": "Task not found"}
    
    with open(task_file, 'r', encoding='utf-8') as f:
        task_data = json.load(f)
    return task_data
