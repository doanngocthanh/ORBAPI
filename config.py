import os
import importlib
from fastapi.middleware.cors import CORSMiddleware


class RouterConfig:
    def __init__(self):
        self.api_dir = os.path.join(os.path.dirname(__file__), "src/api")
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    def include_routers(self, app, current_dir, base_module_path):
        for entry in os.listdir(current_dir):
            entry_path = os.path.join(current_dir, entry)
            if os.path.isdir(entry_path):
                self.include_routers(app, entry_path, f"{base_module_path}.{entry}")
            elif entry.endswith(".py"):
                module_name = entry[:-3]
                module_path = f"{base_module_path}.{module_name}"
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, "router"):
                        app.include_router(module.router)
                        print(f"✅ Successfully loaded router: {module_path}")
                except Exception as e:
                    print(f"⚠️ Failed to load router {module_path}: {e}")
                    

class MiddlewareConfig:
    @staticmethod
    def add_cors_middleware(app):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
class PtConfig:
    def __init__(self):
        self.weights_path = os.path.join(os.path.dirname(__file__), "models","pt")
        print(f"Model weights path set to: {self.weights_path}")
    
    def get_model(self,name):
        model_path = os.path.join(self.weights_path, f"{name}.pt")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model {name} not found at {model_path}")
        return model_path
class WeightsConfig:
    def __init__(self):
        self.weights_path = os.path.join(os.path.dirname(__file__), "weights")
        print(f"Model weights path set to: {self.weights_path}")
    
    def getdir(self):
        return self.weights_path
class ImageBaseConfig:
    def __init__(self):
        self.weights_path = os.path.join(os.path.dirname(__file__), "lockup")
        print(f"Model weights path set to: {self.weights_path}")
    
    def get_image(self,name):
        model_path = os.path.join(self.weights_path, f"{name}.png")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model {name} not found at {model_path}")
        return model_path