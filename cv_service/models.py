import os
import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel, AutoProcessor, AutoModelForCausalLM
import warnings
import sys
from unittest.mock import MagicMock

# Optimize PyTorch CPU threading for high throughput
num_cpus = os.cpu_count() or 4
torch.set_num_threads(num_cpus)
torch.set_num_interop_threads(2)

# Mock flash_attn because transformers strictly checks for it, but it's not needed for CPU
m = MagicMock()
m.__spec__ = MagicMock()
sys.modules['flash_attn'] = m

warnings.filterwarnings("ignore")

class CVModels:
    def __init__(self):
        self.device = "cpu"
        print(f"Loading CV models on {self.device} with {num_cpus} threads...")
        
        # 1. CLIP for room validation and object categorization
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.clip_model.eval()

        # Precompute static text embeddings once at startup to avoid repeated text transformer passes
        self.indoor_labels = [
            "a photo of an indoor physical room",
            "a blueprint, floor plan, or architectural drawing",
            "a generic graphic, icon, cartoon, logo, or illustration",
            "a landscape outdoors",
            "a close up of a face or person"
        ]
        indoor_inputs = self.clip_processor(text=self.indoor_labels, return_tensors="pt", padding=True).to(self.device)
        with torch.inference_mode():
            feat = self.clip_model.get_text_features(**indoor_inputs)
            self.indoor_text_features = feat / feat.norm(p=2, dim=-1, keepdim=True)

        self.category_labels = [
            # Index 0-1: Pre-filter skip categories
            "a person, human body, face, pet, or animal",                          # 0: living_being
            "temporary items like food, drink, phone, laptop, bag, or clothing",   # 1: temporary_item
            # Index 2-21: Hazard evaluation categories
            "structural hardware like a hinge, strike plate, or latch",            # 2: structural_hardware
            "operable hardware like a door handle, knob, switch, or button",       # 3: operable_hardware
            "an interior room door, bathroom door, or bedroom door",               # 4: interior_door
            "an exterior door, front door, exit door, or fire escape",             # 5: restricted_exit
            "a cupboard, wardrobe, kitchen cabinet, or closed storage unit",       # 6: storage_cabinet
            "seating or sleeping furniture like a chair, sofa, bed, or toilet",    # 7: seating_sleeping
            "sharp rigid furniture like a table, desk, or countertop",             # 8: sharp_furniture
            "a soft floor covering like a rug, mat, or carpet",                    # 9: soft_floor_covering
            "a hard floor surface like tile, wood, or linoleum",                   # 10: hard_floor
            "a transparent glass object like a window, glass door, or glass table",# 11: glass_transparent
            "a mirror or highly reflective dark surface",                          # 12: mirror_reflective
            "a light fixture, lamp, or ceiling light",                             # 13: light_source
            "stairs, steps, or a staircase",                                       # 14: stair_step
            "a sign, label, notice, or wayfinding marker",                         # 15: signage_label
            "a plain wall, wallpaper, or wall panel",                              # 16: wall_surface
            "a power cord, cable, threshold strip, or small floor-level obstacle", # 17: floor_obstacle
            "a wall-mounted TV, floating shelf, hanging light, or protruding object", # 18: protruding_object
            "a clock, painting, artwork, vase, or decorative landmark",            # 19: landmark_wayfinding
            "a curtain, blind, or window covering",                                # 20: curtain_blind
            "other safe indoor object",                                            # 21: other
        ]
        self.category_map = [
            "living_being",        # 0
            "temporary_item",      # 1
            "structural_hardware", # 2
            "operable_hardware",   # 3
            "interior_door",       # 4
            "restricted_exit",     # 5
            "storage_cabinet",     # 6
            "seating_sleeping",    # 7
            "sharp_furniture",     # 8
            "soft_floor_covering", # 9
            "hard_floor",          # 10
            "glass_transparent",   # 11
            "mirror_reflective",   # 12
            "light_source",        # 13
            "stair_step",          # 14
            "signage_label",       # 15
            "wall_surface",        # 16
            "floor_obstacle",      # 17
            "protruding_object",   # 18
            "landmark_wayfinding", # 19
            "curtain_blind",       # 20
            "other",               # 21
        ]
        cat_inputs = self.clip_processor(text=self.category_labels, return_tensors="pt", padding=True).to(self.device)
        with torch.inference_mode():
            cfeat = self.clip_model.get_text_features(**cat_inputs)
            self.category_text_features = cfeat / cfeat.norm(p=2, dim=-1, keepdim=True)
        
        # 2. Florence-2 for detection, segmentation, OCR, and VQA
        model_id = "microsoft/Florence-2-base"
        try:
            self.flo_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            self.flo_model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True).to(self.device)
            self.flo_model.eval()
        except Exception as e:
            print(f"Failed to load Florence-2: {e}")
            self.flo_model = None
            
        print("Models loaded successfully with precomputed embeddings.")

    def is_indoor_room(self, image: Image.Image) -> bool:
        inputs = self.clip_processor(images=image, return_tensors="pt").to(self.device)
        with torch.inference_mode():
            img_feat = self.clip_model.get_image_features(**inputs)
            img_feat = img_feat / img_feat.norm(p=2, dim=-1, keepdim=True)
            logit_scale = self.clip_model.logit_scale.exp()
            logits = torch.matmul(img_feat, self.indoor_text_features.t()) * logit_scale
            probs = logits.softmax(dim=-1).cpu().numpy()[0]
        return np.argmax(probs) == 0

    def run_florence_task(self, image: Image.Image, task: str, text_input: str = None):
        if not self.flo_model:
            return {}
            
        prompt = task if text_input is None else task + text_input
        inputs = self.flo_processor(text=prompt, images=image, return_tensors="pt").to(self.device)
        
        with torch.inference_mode():
            generated_ids = self.flo_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                do_sample=False,
                num_beams=1,
            )
            
        generated_text = self.flo_processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = self.flo_processor.post_process_generation(
            generated_text, 
            task=task, 
            image_size=(image.width, image.height)
        )
        return parsed_answer

    def get_segmentation_mask(self, image: Image.Image, target: str) -> np.ndarray:
        """
        Uses Florence-2 REFERRING_EXPRESSION_SEGMENTATION to generate a binary mask
        for a target region (e.g., "floor", "wall").
        Returns a binary numpy array (H, W) where 1 = target region, 0 = not.
        """
        if not self.flo_model:
            return np.zeros((image.height, image.width), dtype=np.uint8)
        
        try:
            result = self.run_florence_task(image, "<REFERRING_EXPRESSION_SEGMENTATION>", target)
            seg_data = result.get('<REFERRING_EXPRESSION_SEGMENTATION>', {})
            polygons = seg_data.get('polygons', [])
            
            import cv2
            mask = np.zeros((image.height, image.width), dtype=np.uint8)
            for polygon_group in polygons:
                for polygon in polygon_group:
                    pts = np.array(polygon, dtype=np.int32).reshape(-1, 2)
                    if len(pts) >= 3:
                        cv2.fillPoly(mask, [pts], 1)
            return mask
        except Exception:
            return np.zeros((image.height, image.width), dtype=np.uint8)

    def classify_object_category(self, image_crop: Image.Image) -> str:
        """
        Classifies a cropped object image into one of 22 semantic categories
        using precomputed CLIP text embeddings for ultra-fast vector dot-product scoring.
        """
        if not self.clip_model:
            return "other"
        
        try:
            inputs = self.clip_processor(images=image_crop, return_tensors="pt").to(self.device)
            with torch.inference_mode():
                img_feat = self.clip_model.get_image_features(**inputs)
                img_feat = img_feat / img_feat.norm(p=2, dim=-1, keepdim=True)
                logit_scale = self.clip_model.logit_scale.exp()
                logits = torch.matmul(img_feat, self.category_text_features.t()) * logit_scale
                probs = logits.softmax(dim=-1).cpu().numpy()[0]
                
            idx = int(np.argmax(probs))
            if float(np.max(probs)) > 0.15:
                return self.category_map[idx]
        except Exception:
            pass
        return "other"

cv_models = CVModels()
