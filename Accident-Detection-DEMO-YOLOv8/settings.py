from pathlib import Path
import os

class AccidentDetectionSettings:
    def __init__(self):
        self.root = Path(__file__).parent.resolve()
        self.weights_dir = self.root / 'weights'
        self.snapshots_dir = self.root / 'snapshots'
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.model_path = self.weights_dir / 'best.pt'  

        self.confidence_threshold = 0.4  
        self.max_videos = 6  

        self.class_ids = [0, 1]  # 0: "nehoda", 1: "vazna nehoda"
    
