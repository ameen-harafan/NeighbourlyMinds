import os
import uuid
import io
import base64
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from models import cv_models
from PIL import Image, UnidentifiedImageError
import warnings
warnings.filterwarnings("ignore")

# Same 10 MB limit as the Node API. Pixel cap stops "decompression bomb" images using all RAM.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000
CV_DEBUG = os.getenv("CV_DEBUG", "false").lower() == "true"

def debug_log(message):
    if CV_DEBUG:
        print(message)

app = FastAPI(title="NeighbourlyMinds CV Microservice")

# Only the Node API calls this service (inside Docker network), so browsers do not need access.
cv_allowed_origins = [o.strip() for o in os.getenv("CV_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cv_allowed_origins,
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# ═══════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class Suggestion(BaseModel):
    id: str
    category: str
    title: str
    lrv_score: float
    object_lrv: float
    background_lrv: float
    rule_type: str
    recommendation: str
    location_box: List[int]
    polygon: List[List[int]]

class AuditResponse(BaseModel):
    status: str
    is_valid_indoor: bool
    original_annotated_url: Optional[str] = None
    transformed_after_url: Optional[str] = None
    barriers_found: int
    suggestions: List[Suggestion]

# ═══════════════════════════════════════════════════════════════
# PRE-FILTER KEYWORD SETS (Phase 2 — Zero CPU Cost)
# ═══════════════════════════════════════════════════════════════

LIVING_BEING_KEYWORDS = {
    "person", "man", "woman", "child", "baby", "people", "boy", "girl",
    "dog", "cat", "pet", "bird", "animal", "face", "head", "body",
    "figure", "standing", "sitting", "walking"
}

TEMPORARY_ITEM_KEYWORDS = {
    "food", "drink", "cup", "plate", "bowl", "bottle", "glass of",
    "phone", "laptop", "remote", "book", "magazine", "newspaper",
    "bag", "backpack", "purse", "handbag", "suitcase",
    "clothing", "shirt", "shoe", "jacket", "coat", "hat", "towel",
    "keys", "pen", "toy", "ball"
}

# ═══════════════════════════════════════════════════════════════
# HAZARD DESCRIPTION DICTIONARY (Phase 6 — Generalized Templates)
# ═══════════════════════════════════════════════════════════════

HAZARD_DESCRIPTIONS = {
    # ── RULE 1: Camouflage ──
    "camouflage_standard": {
        "title": "Low-Contrast Object",
        "category": "Camouflage",
        "issue": "This area blends into its background (color difference: {lrv:.0f}%), making it hard to see. Someone with dementia might not notice it at all.",
        "suggestion": "Use a different color to make it stand out. Try adding bright tape, a cover, or a sticker so it's clearly visible against the wall."
    },
    "camouflage_floor_bg": {
        "title": "Seat Blends Into Floor",
        "category": "Camouflage",
        "issue": "This seat is almost the same color as the floor (color difference: {lrv:.0f}%). This makes it hard to see where the seat ends and the floor begins, which can cause falls when sitting down.",
        "suggestion": "Place a bright, contrasting cushion or throw blanket over the seat so it stands out clearly from the floor."
    },
    "camouflage_exit_seeking": {
        "title": "Highly Visible Exit Door",
        "category": "Wandering",
        "issue": "This door stands out strongly from the wall (color difference: {lrv:.0f}%). A bright or obvious exit door can act as a magnet, encouraging unsafe wandering.",
        "suggestion": "Paint the door and doorframe the exact same color as the surrounding wall to disguise it. Making the door 'disappear' reduces the urge to leave."
    },
    "camouflage_structural": {
        "title": "High-Contrast Fixture",
        "category": "Hardware",
        "issue": "This fixture stands out sharply against the wall (color difference: {lrv:.0f}%). Unnecessary bright objects can cause confusion or anxiety.",
        "suggestion": "Paint or cover this fixture so it matches the wall color and blends in quietly."
    },

    # ── RULE 2: Visual Confusion ──
    "visual_confusion_floor": {
        "title": "High-Contrast Floor Transition",
        "category": "Floor Hazard",
        "issue": "This spot is a very different color from the rest of the floor (color difference: {lrv:.0f}%). People with dementia might see this dark spot as a deep hole or a step, causing them to freeze or stumble.",
        "suggestion": "Try to make the floor color consistent. Remove dark mats on light floors, or cover the area with a rug that matches the surrounding floor color."
    },
    "visual_confusion_stairs": {
        "title": "Invisible Stair Edges",
        "category": "Floor Hazard",
        "issue": "The edge of this step blends right into the stair below it (color difference: {lrv:.0f}%). Without a visible edge, the stairs look like a flat ramp, making falls very likely.",
        "suggestion": "Add bright, non-slip tape to the edge of every step so each one is clearly visible."
    },
    "doorway_low_contrast": {
        "title": "Low Contrast Entrance Frame",
        "category": "Wayfinding & Doorways",
        "issue": "This entrance frame blends into the surrounding corridor wall (color difference: {lrv:.0f}% LRV, below the 30% Victorian Dementia-Friendly standard). Older adults with perceptual impairment cannot identify the doorway threshold.",
        "suggestion": "Paint the doorway frame/architrave in a contrasting hue with at least 30% LRV difference in accordance with AS 1428.1 and Victorian Dementia-Friendly Guidelines."
    },
    "corridor_glare_hotspot": {
        "title": "Harsh Flooring Glare Hotspot",
        "category": "Specular Glare",
        "issue": "Polished corridor surface generates harsh specular glare hotspots ({lrv:.0f}% LRV), which appears as deep voids or standing water to people experiencing dementia.",
        "suggestion": "Apply an anti-glare matte coating or install matte visual runners to eliminate disorientation and gait freezing."
    },

    # ── RULE 3: Camouflaged Trip Hazards ──
    "camouflaged_trip": {
        "title": "Invisible Floor Obstacle",
        "category": "Floor Hazard",
        "issue": "This obstacle is almost the same color as the floor (color difference: {lrv:.0f}%), making it nearly invisible and a major trip hazard.",
        "suggestion": "Move this object out of the walking path. If it can't be moved, mark it with bright tape."
    },

    # ── RULE 4: Specular Glare ──
    "specular_glare": {
        "title": "Specular Glare",
        "category": "Glare",
        "issue": "This area is very shiny and reflects light brightly. People with dementia might mistake these bright, shiny spots for wet puddles, ice, or holes on the floor, making them afraid to walk here.",
        "suggestion": "Cover the shiny area with a matte (non-shiny) material. For floors, use a matte finish or place a plain, non-slip rug over the glare."
    },

    # ── RULE 5: Direct Glare ──
    "direct_glare_bulb": {
        "title": "Unshielded Light Bulb",
        "category": "Lighting",
        "issue": "This bare light bulb is blindingly bright. Staring directly into harsh, unshaded light can temporarily blind older eyes, hiding other hazards in the room.",
        "suggestion": "Add a lampshade, diffuser, or frosted cover so the bare bulb isn't visible. Soft, even lighting is much better than harsh bright spots."
    },
    "direct_glare_window": {
        "title": "Blinding Window Glare",
        "category": "Lighting",
        "issue": "This window is letting in blindingly bright sunlight. Staring into harsh, unshaded daylight can temporarily blind older eyes, hiding other hazards in the room.",
        "suggestion": "Add sheer curtains or adjustable blinds to soften the incoming sunlight. This provides bright, even daylight without the harsh glare."
    },

    # ── RULE 6: Busy Patterns ──
    "busy_pattern": {
        "title": "Busy Visual Pattern",
        "category": "Surfaces",
        "issue": "This area has a busy, complex pattern. Busy patterns can look like they are moving, crawling, or acting as physical obstacles, causing dizziness and confusion.",
        "suggestion": "Replace the busy pattern with a solid, plain color. Calm, simple surfaces are much easier on the eyes and brain."
    },

    # ── RULE 7: Sharp Edges ──
    "sharp_edges": {
        "title": "Sharp Edge/Corner Hazard",
        "category": "Safety",
        "issue": "This area has sharp corners. Since dementia affects depth perception, a person might misjudge the distance and bump into it, causing serious bruising or cuts.",
        "suggestion": "Add soft, padded corner guards to the sharp edges, or replace it with something that has rounded, safe edges."
    },

    # ── RULE 8: Transparency ──
    "transparency": {
        "title": "Invisible Glass Barrier",
        "category": "Safety",
        "issue": "This clear glass has no markings on it. Since older eyes struggle to see clear glass, a person might try to walk right through it and get badly hurt.",
        "suggestion": "Place bright stickers, frosted tape, or decals at eye level so the glass is obvious and looks solid."
    },

    # ── RULE 9: Ghosting ──
    "ghosting": {
        "title": "Mirror/Reflection Hazard",
        "category": "Psychological",
        "issue": "This area acts like a mirror. People with dementia sometimes forget what they look like, and seeing their own reflection might make them think a stranger is in the room, causing fear.",
        "suggestion": "Cover the mirror with a curtain or cloth when it's not being used, or remove it entirely."
    },

    # ── RULE 10: Protruding Hazards ──
    "protruding": {
        "title": "Protruding Obstacle",
        "category": "Safety",
        "issue": "This object sticks out into the walking path at head or chest height, but has nothing resting on the floor. A person walking with their head down might crash right into it.",
        "suggestion": "Place a plant, a small table, or a floor marker directly underneath it so the person notices something is blocking the path."
    },

    # ── RULE 11: Hidden Affordances ──
    "hidden_affordance": {
        "title": "Unlabeled Door/Cabinet",
        "category": "Cognitive",
        "issue": "This door or cabinet has no sign on it. Someone with memory loss might forget what is inside or where the bathroom is, causing distress.",
        "suggestion": "Put a simple, clear sign with a picture and a word (like 'Toilet' or 'Kitchen') right at eye level."
    },

    # ── RULE 12: Structural Boundary Loss ──
    "boundary_loss": {
        "title": "Invisible Wall-Floor Boundary",
        "category": "Camouflage",
        "issue": "The wall and the floor are almost the exact same color. This makes the room look like an endless space without walls, which can be deeply disorienting and cause falls.",
        "suggestion": "Paint the bottom edge of the wall a different color, or add a dark wooden baseboard so the person can clearly see where the floor ends and the wall begins."
    },

    # ── RULE 13: Striped Shadows ──
    "striped_shadows": {
        "title": "Gait-Freezing Shadow Pattern",
        "category": "Surfaces",
        "issue": "There are striped shadows on the floor (usually from window blinds). These stripes can look like a set of stairs or a ditch, making the person freeze in their tracks and potentially fall.",
        "suggestion": "Adjust the blinds or use sheer curtains to soften the sunlight so the harsh stripes disappear from the floor."
    },

    # ── RULE 14: Deep Shadows ──
    "deep_shadows": {
        "title": "Deep Shadows on Floor",
        "category": "Lighting",
        "issue": "There are very dark shadows on the floor. To a person with dementia, dark patches look like deep holes or sudden drop-offs, making them scared to walk forward.",
        "suggestion": "Add soft overhead lighting or lamps to brighten up the dark corners and eliminate the shadows."
    },

    # ── RULE 15: Signage Usability ──
    "signage_placement": {
        "title": "Sign Placed Too High",
        "category": "Signage",
        "issue": "The sign '{text}' is placed way too high. Older adults often walk looking slightly downward and will completely miss signs placed above eye level.",
        "suggestion": "Move the sign lower, to about chest or eye level (around 1.3 meters from the floor)."
    },
    "signage_legibility": {
        "title": "Sign Text Not Legible",
        "category": "Signage",
        "issue": "The text on the sign '{text}' blends into its background (color difference: {lrv:.0f}%), making it very hard to read.",
        "suggestion": "Use a sign with dark text on a bright white background, or bright text on a dark background. Make sure the letters are large and simple."
    },
    "signage_abstract": {
        "title": "Confusing Signage",
        "category": "Signage",
        "issue": "The sign '{text}' uses confusing or tricky words. People with memory loss might not understand clever names or abstract ideas.",
        "suggestion": "Change the sign to a simple, direct word (like '{concrete}') and add a clear picture."
    },

    # ── RULE 16: Illusions ──
    "illusion": {
        "title": "Misleading Wall Image",
        "category": "Cognitive",
        "issue": "This picture or wallpaper looks like a real 3D space (like a fake window, bookshelf, or hallway). A person with dementia might try to walk into it or grab things from it, causing extreme frustration.",
        "suggestion": "Remove the 3D picture and replace it with a plain color or simple, flat artwork."
    },

    # ── RULE 17: Spatial Clutter ──
    "clutter": {
        "title": "Cluttered Surface/Area",
        "category": "Cognitive",
        "issue": "This area is covered in too many loose items. A cluttered space overwhelms the brain, making it hard to find important things and creating dangerous trip hazards.",
        "suggestion": "Clear away the clutter. Keep only the most important items visible, and put the rest in labeled drawers or boxes."
    },

    # ── RULE 18: Illumination Transitions ──
    "illumination_transition": {
        "title": "Sudden Lighting Change",
        "category": "Lighting",
        "issue": "One part of the room is much brighter than the other. When walking from a bright area to a dark area, aging eyes take much longer to adjust, creating a few seconds of total blindness where falls often happen.",
        "suggestion": "Try to make the lighting even across the whole room. Add a lamp to the dark side, or dim the lights on the bright side."
    },

    # ── RULE 19: Low Illuminance ──
    "low_illuminance": {
        "title": "Overall Low Lighting",
        "category": "Lighting",
        "issue": "This room is too dim. Aging eyes need up to three times more light to see clearly, and dim lighting makes every other hazard in the room much more dangerous.",
        "suggestion": "Increase the overall brightness of the room by adding brighter bulbs or opening curtains."
    },

    # ── RULE 20: Overstimulating Color ──
    "color_saturation": {
        "title": "Overstimulating Room Color",
        "category": "Cognitive",
        "issue": "There is a large amount of highly stimulating color (like bright red or orange) in this room. While great for small accents, wrapping a room in these colors can cause anxiety and overstimulation.",
        "suggestion": "Use calming, muted colors (like soft blues, greens, or warm neutrals) for large walls and floors, and save the bright colors for important things you want to highlight."
    },

    # ── RULE 21: Blocked Sightlines ──
    "sightline": {
        "title": "Blocked Line of Sight",
        "category": "Navigation",
        "issue": "This large object blocks the view across the room. If a person with dementia can't see the toilet or their bed from where they are sitting, they might forget it exists.",
        "suggestion": "Move this object against a wall or out of the room to open up the view, so important areas are always visible."
    }
}

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def calculate_iou(box1, box2):
    """Calculate Intersection over Union between two [x, y, w, h] bounding boxes."""
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[0] + box1[2], box2[0] + box2[2])
    y_bottom = min(box1[1] + box1[3], box2[1] + box2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = box1[2] * box1[3]
    box2_area = box2[2] * box2[3]
    return intersection_area / float(box1_area + box2_area - intersection_area)

def calculate_ioa(box1, box2):
    """Calculate Intersection over Area of box1. Useful when box1 might be entirely enclosed by box2."""
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[0] + box1[2], box2[0] + box2[2])
    y_bottom = min(box1[1] + box1[3], box2[1] + box2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = box1[2] * box1[3]
    return intersection_area / float(max(box1_area, 1))

def calculate_lrv_from_bbox(img_cv2, img_lab, bbox, padding=20):
    """
    Calculates the Light Reflectance Value (LRV) contrast between an object and its
    immediate background. Uses GrabCut on the local ROI to isolate the foreground object.
    Returns: (lrv_diff, object_lrv, background_lrv, foreground_mask)
    """
    x, y, w, h = [int(v) for v in bbox]
    H, W = img_lab.shape[:2]
    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x+w), min(H, y+h)
    
    px1, py1, px2, py2 = max(0, x-padding), max(0, y-padding), min(W, x+w+padding), min(H, y+h+padding)
    roi_cv2 = img_cv2[py1:py2, px1:px2]
    mask2 = np.zeros(img_cv2.shape[:2], np.uint8)
    
    if roi_cv2.shape[0] < 5 or roi_cv2.shape[1] < 5:
        mask2[y1:y2, x1:x2] = 1
        return 0.0, 0.0, 0.0, mask2

    roi_mask = np.zeros(roi_cv2.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rx, ry = x1 - px1, y1 - py1
    rw, rh = min(w, roi_cv2.shape[1] - rx), min(h, roi_cv2.shape[0] - ry)
    rect = (rx, ry, max(1, rw), max(1, rh))
    try:
        cv2.grabCut(roi_cv2, roi_mask, rect, bgdModel, fgdModel, 2, cv2.GC_INIT_WITH_RECT)
        roi_mask2 = np.where((roi_mask == 2) | (roi_mask == 0), 0, 1).astype('uint8')
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        roi_mask2 = cv2.morphologyEx(roi_mask2, cv2.MORPH_CLOSE, kernel)
    except Exception:
        roi_mask2 = np.zeros(roi_cv2.shape[:2], np.uint8)
        roi_mask2[ry:ry+rh, rx:rx+rw] = 1

    mask2[py1:py2, px1:px2] = roi_mask2

    obj_l = img_lab[:, :, 0][mask2 == 1]

    bg_region_mask = np.zeros(img_cv2.shape[:2], np.uint8)
    bg_region_mask[py1:py2, px1:px2] = 1
    bg_mask_final = (bg_region_mask == 1) & (mask2 == 0)
    bg_l = img_lab[:, :, 0][bg_mask_final]

    if len(obj_l) == 0 or len(bg_l) == 0: 
        return 0.0, 0.0, 0.0, mask2

    o_lrv = float(np.mean(obj_l) / 255.0 * 100.0)
    b_lrv = float(np.mean(bg_l) / 255.0 * 100.0)

    return abs(o_lrv - b_lrv), o_lrv, b_lrv, mask2

def calculate_lrv_against_mask(img_lab, bbox, region_mask, grabcut_mask):
    """
    Calculates LRV contrast between an object (defined by grabcut_mask) and
    a specific region mask (e.g., floor_mask). Used for Floor-as-Background checks.
    """
    obj_l = img_lab[:, :, 0][grabcut_mask == 1]
    
    x, y, w, h = [int(v) for v in bbox]
    H, W = img_lab.shape[:2]
    # Expand search area around the object to find adjacent floor/wall pixels
    pad = max(w, h) // 2
    px1, py1 = max(0, x - pad), max(0, y - pad)
    px2, py2 = min(W, x + w + pad), min(H, y + h + pad)
    
    search_region = np.zeros((H, W), dtype=np.uint8)
    search_region[py1:py2, px1:px2] = 1
    
    # Floor/wall pixels near the object, excluding the object itself
    bg_mask = (search_region == 1) & (region_mask == 1) & (grabcut_mask == 0)
    bg_l = img_lab[:, :, 0][bg_mask]
    
    if len(obj_l) == 0 or len(bg_l) == 0:
        return 0.0, 0.0, 0.0
    
    o_lrv = float(np.mean(obj_l) / 255.0 * 100.0)
    b_lrv = float(np.mean(bg_l) / 255.0 * 100.0)
    return abs(o_lrv - b_lrv), o_lrv, b_lrv

def has_contrasting_edge_lining(img_lab, bbox, grabcut_mask, o_lrv):
    """
    Checks if a piece of furniture has a deliberate high-contrast edge lining.
    It does this by eroding the GrabCut mask to separate the object's "core" from its "border".
    If the average Light Reflectance Value of the border differs significantly from the core,
    it indicates a deliberate contrasting edge lining painted around the perimeter.
    This ignores center-placed hardware (knobs) and pillows.
    """
    x, y, w, h = [int(v) for v in bbox]
    H, W = img_lab.shape[:2]
    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x+w), min(H, y+h)
    
    mask_crop = grabcut_mask[y1:y2, x1:x2]
    
    # Erode the mask by 6 pixels to get the inner core
    kernel = np.ones((6, 6), np.uint8)
    core_mask = cv2.erode(mask_crop, kernel, iterations=1)
    
    # The border is whatever is in the original mask but NOT in the core
    border_mask = mask_crop - core_mask
    
    core_pixels = img_lab[y1:y2, x1:x2, 0][core_mask == 1]
    border_pixels = img_lab[y1:y2, x1:x2, 0][border_mask == 1]
    
    if len(core_pixels) == 0 or len(border_pixels) == 0:
        return False
        
    core_lrv = np.mean(core_pixels) / 255.0 * 100.0
    border_lrv = np.mean(border_pixels) / 255.0 * 100.0
    
    diff = abs(core_lrv - border_lrv)
    
    # Calculate pixel contrast ratio (for large two-tone objects like tables with colored sides)
    obj_l_pixels = img_lab[y1:y2, x1:x2, 0][mask_crop == 1]
    if len(obj_l_pixels) > 0:
        obj_lrvs = (obj_l_pixels / 255.0) * 100.0
        body_lrv = np.mean(obj_lrvs)
        contrast_pixels = np.count_nonzero(np.abs(obj_lrvs - body_lrv) > 30.0)
        contrast_ratio = contrast_pixels / max(1, len(obj_lrvs))
    else:
        contrast_ratio = 0.0
    
    debug_log(f"[EDGE DEBUG] core_lrv={core_lrv:.1f}, border_lrv={border_lrv:.1f}, diff={diff:.1f}, contrast_ratio={contrast_ratio:.4f}")
    
    # 1. Thin edge lining around perimeter (border differs from core)
    # 2. Large two-tone design (colored sides -> >20% of pixels contrast with mean)
    return diff > 10.0 or contrast_ratio > 0.20

def make_suggestion(desc_key, bbox_format, poly_pts, lrv_diff=0.0, o_lrv=0.0, b_lrv=0.0, **fmt_kwargs):
    """
    Creates a Suggestion object using the HAZARD_DESCRIPTIONS dictionary.
    Dynamically formats issue and suggestion text with the provided keyword arguments.
    """
    desc = HAZARD_DESCRIPTIONS[desc_key]
    
    try:
        issue_text = desc["issue"].format(**fmt_kwargs)
    except KeyError:
        issue_text = desc["issue"]
    try:
        suggestion_text = desc["suggestion"].format(**fmt_kwargs)
    except KeyError:
        suggestion_text = desc["suggestion"]
    
    return Suggestion(
        id=f"sug_{uuid.uuid4().hex[:8]}",
        category=desc["category"],
        title=desc["title"],
        lrv_score=lrv_diff,
        object_lrv=o_lrv,
        background_lrv=b_lrv,
        rule_type="CV",
        recommendation=f"Issue: {issue_text} Suggestion: {suggestion_text}",
        location_box=bbox_format,
        polygon=poly_pts
    )

# ═══════════════════════════════════════════════════════════════
# TEXT-BASED SEMANTIC OVERRIDES
# ═══════════════════════════════════════════════════════════════

# Maps Florence-2 text labels to forced CLIP categories when text is unambiguous.
# This prevents CLIP from being confused by complex visual scenes.
TEXT_OVERRIDES = {
    "sharp_furniture": ["table", "desk", "cabinet", "dresser", "counter", "countertop", "shelf"],
    "soft_floor_covering": ["rug", "carpet", "mat", "runner"],
    "seating_sleeping": ["sofa", "couch", "chair", "armchair", "bed", "bench", "stool", "toilet"],
    # Order matters for tiebreaking: categories listed first win when keyword lengths are equal.
    # Put more important/specific categories first.
    "landmark_wayfinding": ["door frame", "doorframe", "skirting", "baseboard", "architrave"],
    # Hardware containing the word 'door' must be matched before 'door' to avoid being misclassified as a door
    "structural_hardware_door_specific": ["door handle", "door knob", "door lock", "door hinge", "sliding door handle", "strike plate"],
    "interior_door": ["door", "doorway"],
    "structural_hardware": ["latch", "hinge", "knob", "handle", "lock", "deadbolt", "keyhole", "lever", "pull", "hook"],
    "stair_step": ["stair", "stairs", "step", "staircase"],
    "hard_floor": ["floor", "tile", "hardwood", "parquet", "linoleum", "laminate", "marble floor", "wooden floor", "polished floor"],
    "mirror_reflective": ["mirror"],
    "light_source": ["lamp", "chandelier", "light fixture", "ceiling light"],
    "curtain_blind": ["curtain", "blind", "drape", "shade"],
    "glass_transparent": ["window", "glass door", "glass table", "sliding door"],
}

def get_text_override(label_lower):
    """Check if Florence's text label unambiguously identifies the object category.
    Uses first-match-wins based strictly on the order of TEXT_OVERRIDES. 
    Because 'interior_door' is listed before 'structural_hardware', a label like 
    'white door with metal hinges' will correctly match 'door' first and ignore 'hinges'.
    """
    for cat, keywords in TEXT_OVERRIDES.items():
        for kw in keywords:
            if kw in label_lower:
                if cat == "structural_hardware_door_specific":
                    return "structural_hardware"
                return cat
    return None

# ═══════════════════════════════════════════════════════════════
# MAIN AUDIT ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.post("/api/audit-image", response_model=AuditResponse)
async def audit_image(file: UploadFile = File(...)):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    image_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large.")
    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise HTTPException(status_code=400, detail="File could not be read as an image.")
    
    # ── Downscale high-resolution images for fast, timeout-safe CPU inference ──
    # Florence-2 native resolution is 768px, CLIP is 224px. Capping to max 1024px
    # preserves all built-environment details while preventing 300s CPU timeouts.
    max_dim = 1024
    if pil_image.width > max_dim or pil_image.height > max_dim:
        pil_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    
    # ── Indoor Validation ──
    is_indoor = cv_models.is_indoor_room(pil_image)
    if not is_indoor:
        return AuditResponse(
            status="error",
            is_valid_indoor=False,
            barriers_found=0,
            suggestions=[]
        )
    
    # ── Prepare OpenCV Matrices ──
    img_cv2 = np.array(pil_image)[:, :, ::-1].copy()
    img_lab = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2LAB)
    img_gray = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2GRAY)
    img_h, img_w = img_cv2.shape[:2]
    
    suggestions = []
    barriers_found = 0
    
    if not cv_models.flo_model:
        return AuditResponse(status="error", is_valid_indoor=True, barriers_found=0, suggestions=[])

    # ═══════════════════════════════════════════════════════════
    # PHASE 0: SEMANTIC SEGMENTATION MASKS (Run Once, Reuse Everywhere)
    # ═══════════════════════════════════════════════════════════
    
    floor_mask = cv_models.get_segmentation_mask(pil_image, "floor")
    wall_mask = cv_models.get_segmentation_mask(pil_image, "wall")
    
    # ═══════════════════════════════════════════════════════════
    # CACHED FLORENCE-2 CALLS (Run Once, Reuse Everywhere)
    # ═══════════════════════════════════════════════════════════
    
    # Call 1: OCR — cached for Rule 11 (Hidden Affordances), Rule 15 (Signage)
    res_ocr = cv_models.run_florence_task(pil_image, "<OCR_WITH_REGION>", "")
    ocr_bboxes = res_ocr.get('<OCR_WITH_REGION>', {}).get('quad_boxes', [])
    ocr_labels = res_ocr.get('<OCR_WITH_REGION>', {}).get('labels', [])
    
    # Call 4: Dense Region Captions — primary object detection
    res_dense = cv_models.run_florence_task(pil_image, "<DENSE_REGION_CAPTION>", "")
    dense_bboxes = res_dense.get('<DENSE_REGION_CAPTION>', {}).get('bboxes', [])
    dense_labels = res_dense.get('<DENSE_REGION_CAPTION>', {}).get('labels', [])
    
    # Call 5: Safety-net Vocab Grounding — ensures critical objects are not missed
    vocab = "floor. rug. mat. carpet. door. door frame. door handle. door knob. hinge. strike plate. door latch. door lock. window. window blind. curtain. sofa. couch. chair. armchair. bed. table. coffee table. dining table. desk. counter. cabinet. dresser. wardrobe. lamp. light fixture. television. mirror. stairs. steps. handrail. toilet. bathtub. shower. sink. power cord. cable. threshold."
    res_vocab = cv_models.run_florence_task(pil_image, "<CAPTION_TO_PHRASE_GROUNDING>", vocab)
    vocab_bboxes = res_vocab.get('<CAPTION_TO_PHRASE_GROUNDING>', {}).get('bboxes', [])
    vocab_labels = res_vocab.get('<CAPTION_TO_PHRASE_GROUNDING>', {}).get('labels', [])
    
    # ═══════════════════════════════════════════════════════════
    # RULE 15a: ABSTRACT SIGNAGE (Process OCR results first)
    # ═══════════════════════════════════════════════════════════
    
    abstract_terms = {
        "facilities": "Toilet", "restroom": "Toilet", "washroom": "Toilet",
        "wc": "Toilet", "cloakroom": "Toilet", "exit": "Way Out",
        "lavatory": "Toilet", "powder room": "Toilet"
    }
    
    # Convert OCR quad boxes to [x, y, w, h] format for reuse
    ocr_rects = []
    for i, pts in enumerate(ocr_bboxes):
        bx1 = int(min(pts[0], pts[2], pts[4], pts[6]))
        bx2 = int(max(pts[0], pts[2], pts[4], pts[6]))
        by1 = int(min(pts[1], pts[3], pts[5], pts[7]))
        by2 = int(max(pts[1], pts[3], pts[5], pts[7]))
        bw, bh = bx2 - bx1, by2 - by1
        if bw <= 0 or bh <= 0: 
            ocr_rects.append(None)
            continue
        ocr_rects.append([bx1, by1, bw, bh])
    
    for i, text in enumerate(ocr_labels):
        if ocr_rects[i] is None: continue
        t_lower = text.lower().strip().replace('</s>', '')
        
        # Abstract signage check
        for abs_term, concrete_term in abstract_terms.items():
            if abs_term in t_lower:
                clean_text = text.replace('</s>', '').strip()
                bx1, by1, bw, bh = ocr_rects[i]
                poly = [[bx1, by1], [bx1+bw, by1], [bx1+bw, by1+bh], [bx1, by1+bh]]
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "signage_abstract", ocr_rects[i], poly,
                    text=clean_text, concrete=concrete_term
                ))
                break
        
        # Rule 15a: Signage Placement (top 25% of image = too high)
        if ocr_rects[i] is not None:
            bx1, by1, bw, bh = ocr_rects[i]
            sign_center_y = by1 + bh / 2
            if sign_center_y < img_h * 0.25:
                clean_text = text.replace('</s>', '').strip()
                poly = [[bx1, by1], [bx1+bw, by1], [bx1+bw, by1+bh], [bx1, by1+bh]]
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "signage_placement", ocr_rects[i], poly,
                    text=clean_text
                ))
        
        # Rule 15b: Signage Legibility (intra-signage contrast)
        if ocr_rects[i] is not None:
            bx1, by1, bw, bh = ocr_rects[i]
            sign_crop_lab = img_lab[by1:by1+bh, bx1:bx1+bw, 0]
            if sign_crop_lab.size > 0:
                _, otsu_mask = cv2.threshold(sign_crop_lab, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                text_l = sign_crop_lab[otsu_mask == 0]
                bg_l = sign_crop_lab[otsu_mask == 255]
                if len(text_l) > 0 and len(bg_l) > 0:
                    text_lrv = float(np.mean(text_l) / 255.0 * 100.0)
                    bg_lrv = float(np.mean(bg_l) / 255.0 * 100.0)
                    sign_contrast = abs(text_lrv - bg_lrv)
                    if sign_contrast < 30.0:
                        clean_text = text.replace('</s>', '').strip()
                        poly = [[bx1, by1], [bx1+bw, by1], [bx1+bw, by1+bh], [bx1, by1+bh]]
                        barriers_found += 1
                        suggestions.append(make_suggestion(
                            "signage_legibility", ocr_rects[i], poly,
                            lrv_diff=sign_contrast, o_lrv=text_lrv, b_lrv=bg_lrv,
                            text=clean_text, lrv=sign_contrast
                        ))
    
    # ═══════════════════════════════════════════════════════════
    # MERGE DETECTIONS & PER-OBJECT PROCESSING (Phases 2-3)
    # ═══════════════════════════════════════════════════════════
    
    all_bboxes = dense_bboxes + vocab_bboxes
    all_labels = dense_labels + vocab_labels
    
    tested_areas = []
    clutter_boxes = []  # Accumulator for Rule 17 (Spatial Clutter)
    curtain_bboxes = []  # Accumulator for curtain/blind detections (used by Rule 5)
    found_wall_surface = False  # Flag for conditional Rule 16 (Illusions)
    
    for i, raw_label in enumerate(all_labels):
        label_core = raw_label.lower().strip()
        x1, y1, x2, y2 = [int(v) for v in all_bboxes[i]]
        w, h = x2 - x1, y2 - y1
        if w <= 0 or h <= 0: continue
        bbox_format = [x1, y1, w, h]
        
        # ── Duplicate Prevention (IoU) ──
        is_duplicate = False
        for t_box in tested_areas:
            if calculate_iou(bbox_format, t_box) > 0.5:
                is_duplicate = True
                break
        if is_duplicate: continue
        
        # ── SKIP MASSIVE BACKGROUND BOXES ──
        # Florence-2 sometimes draws a box around the entire scene (e.g., labeling it "room"). 
        # We must skip this before adding to `tested_areas`, otherwise Rule 21 (Sightlines) will trigger on it.
        obj_area_ratio = (w * h) / (img_w * img_h)
        if obj_area_ratio > 0.85:
            continue
            
        tested_areas.append(bbox_format)
        
        poly_pts = [[x1, y1], [x1+w, y1], [x1+w, y1+h], [x1, y1+h]]
        crop_gray = img_gray[y1:y2, x1:x2]
        
        # ── Map to Dense Caption for Rich Description ──
        best_desc = label_core
        best_iou = 0
        for j, d_box in enumerate(dense_bboxes):
            d_x1, d_y1, d_x2, d_y2 = [int(v) for v in d_box]
            d_format = [d_x1, d_y1, d_x2 - d_x1, d_y2 - d_y1]
            iou = calculate_iou(bbox_format, d_format)
            if iou > best_iou and iou > 0.3:
                best_iou = iou
                best_desc = dense_labels[j].lower()
        display_label = best_desc
        
        # ═══════════════════════════════════════════════════════
        # PHASE 2: PRE-FILTERING
        # ═══════════════════════════════════════════════════════
        
        # Step 1: Text-based pre-filter (zero CPU cost)
        is_living = any(kw in label_core for kw in LIVING_BEING_KEYWORDS)
        is_temporary = any(kw in label_core for kw in TEMPORARY_ITEM_KEYWORDS)
        
        if is_living:
            continue  # SKIP entirely — not part of the built environment
        
        if is_temporary:
            clutter_boxes.append(bbox_format)  # Log for Rule 17
            continue  # SKIP individual evaluation
        
        # ── LRV Contrast Calculation (needed by most rules) ──
        lrv_diff, o_lrv, b_lrv, grabcut_mask = calculate_lrv_from_bbox(img_cv2, img_lab, bbox_format)
        
        # ── Fast Text-Based Semantic Override (Check First to Skip Heavy CLIP Inference) ──
        text_override = get_text_override(label_core) or get_text_override(display_label.lower())
        if text_override:
            semantic_cat = text_override
        else:
            # Smart padding for CLIP crop only when text is ambiguous
            img_isolated = img_cv2.copy()
            if obj_area_ratio >= 0.05:
                img_isolated[grabcut_mask == 0] = [0, 0, 0]
            
            if obj_area_ratio < 0.05:
                pad_x, pad_y = int(w * 0.20), int(h * 0.20)
            else:
                pad_x, pad_y = 0, 0
            
            exp_x1, exp_y1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
            exp_x2, exp_y2 = min(img_w, x2 + pad_x), min(img_h, y2 + pad_y)
            
            crop_cv2 = img_isolated[exp_y1:exp_y2, exp_x1:exp_x2]
            crop_pil = Image.fromarray(cv2.cvtColor(crop_cv2, cv2.COLOR_BGR2RGB))
            semantic_cat = cv_models.classify_object_category(crop_pil)
        
        # Step 2: CLIP-based pre-filter (catches ambiguous labels)
        if semantic_cat == "living_being":
            continue
        if semantic_cat == "temporary_item":
            clutter_boxes.append(bbox_format)
            continue
        
        if CV_DEBUG:
            # Runs CLIP a second time, so only when debugging
            debug_log(f"[OBJ DEBUG] label='{label_core}' | dense='{display_label}' | CLIP='{cv_models.classify_object_category(crop_pil)}' | final='{semantic_cat}' | lrv_diff={lrv_diff:.1f} | area_ratio={obj_area_ratio:.3f}")
        
        # Track curtain/blind detections for Rule 5 window overlap check
        if semantic_cat == "curtain_blind":
            curtain_bboxes.append(bbox_format)
        
        # Track wall surfaces for conditional Rule 16
        if semantic_cat == "wall_surface":
            found_wall_surface = True
        
        # ═══════════════════════════════════════════════════════
        # PHASE 3: PER-OBJECT HAZARD RULES (Tier 1, Rules 1-11)
        # ═══════════════════════════════════════════════════════
        
        # ────────────────────────────────────────────────────
        # [CONTRAST & CAMOUFLAGE]
        # ────────────────────────────────────────────────────
        
        # Rule 1: Camouflage — Standard (LRV < 30 against wall background)
        if semantic_cat in ("operable_hardware", "landmark_wayfinding", "interior_door", "signage_label"):
            if lrv_diff < 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflage_standard", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
        
        # Rule 1: Camouflage — Floor-as-Background (for seating/sleeping)
        if semantic_cat == "seating_sleeping":
            floor_lrv_diff, floor_o_lrv, floor_b_lrv = calculate_lrv_against_mask(
                img_lab, bbox_format, floor_mask, grabcut_mask
            )
            # Furniture with high-contrast edge linings is visually distinct and dementia-friendly
            has_edge_lining = has_contrasting_edge_lining(img_lab, bbox_format, grabcut_mask, floor_o_lrv)
            
            if floor_lrv_diff < 30.0 and floor_b_lrv > 0 and not has_edge_lining:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflage_floor_bg", bbox_format, poly_pts,
                    lrv_diff=floor_lrv_diff, o_lrv=floor_o_lrv, b_lrv=floor_b_lrv,
                    lrv=floor_lrv_diff
                ))
        
        # Rule 1: Camouflage — Exit-Seeking Inversion (restricted exits MUST be camouflaged)
        if semantic_cat == "restricted_exit":
            if lrv_diff > 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflage_exit_seeking", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
        
        # Rule 1: Camouflage — Structural Inversion (structural hardware should blend in)
        if semantic_cat == "structural_hardware":
            if lrv_diff > 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflage_structural", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
        
        # Rule 2: Visual Confusion — Floor-level high contrast
        if semantic_cat == "soft_floor_covering":
            if lrv_diff > 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "visual_confusion_floor", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
        
        # Rule 2: Exception — Stair nosings (LRV < 30 = invisible stairs = HAZARD)
        if semantic_cat == "stair_step":
            if lrv_diff < 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "visual_confusion_stairs", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
        
        # Rule 3: Camouflaged Trip Hazards (grey cord on grey carpet)
        if semantic_cat == "floor_obstacle":
            floor_lrv_diff, floor_o_lrv, floor_b_lrv = calculate_lrv_against_mask(
                img_lab, bbox_format, floor_mask, grabcut_mask
            )
            if floor_lrv_diff < 30.0:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflaged_trip", bbox_format, poly_pts,
                    lrv_diff=floor_lrv_diff, o_lrv=floor_o_lrv, b_lrv=floor_b_lrv,
                    lrv=floor_lrv_diff
                ))
        
        # ────────────────────────────────────────────────────
        # [LIGHTING & REFLECTION]
        # ────────────────────────────────────────────────────
        
        # Rule 4: Specular Glare
        if semantic_cat == "hard_floor":
            l_channel = img_lab[y1:y2, x1:x2, 0]
            # Use a very high lightness threshold (245) so white matte floors aren't flagged
            _, bright_mask = cv2.threshold(l_channel, 245, 255, cv2.THRESH_BINARY)
            glare_ratio = np.count_nonzero(bright_mask) / max(1, w * h)
            if glare_ratio > 0.05:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "specular_glare", bbox_format, poly_pts,
                    lrv_diff=glare_ratio * 100,
                    score=glare_ratio * 100
                ))
        
        # Rule 5: Direct Glare (unshielded light sources)
        if semantic_cat in ("light_source", "glass_transparent"):
            # Check if this window is covered by a curtain/blind
            has_curtain = False
            if semantic_cat == "glass_transparent":
                debug_log(f"[GLARE DEBUG] Evaluating glass_transparent at {bbox_format}")
                for c_bbox in curtain_bboxes:
                    ioa = calculate_ioa(bbox_format, c_bbox)
                    debug_log(f"[GLARE DEBUG] Comparing with curtain at {c_bbox} -> ioa={ioa:.3f}")
                    if ioa > 0.30:
                        has_curtain = True
                        break
                
                # FALLBACK: If Florence-2 detected a curtain *anywhere* in the room, 
                # we assume the windows are covered. Florence-2 often generates 
                # disjoint bounding boxes for windows and curtains.
                if len(curtain_bboxes) > 0 and not has_curtain:
                    debug_log("[GLARE DEBUG] Fallback triggered: A curtain exists in the room, assuming window is treated.")
                    has_curtain = True
            
            if not has_curtain:
                l_channel = img_lab[y1:y2, x1:x2, 0]
                _, max_bright_mask = cv2.threshold(l_channel, 250, 255, cv2.THRESH_BINARY)
                max_bright_ratio = np.count_nonzero(max_bright_mask) / max(1, w * h)
                bright_std = float(np.std(l_channel))
                
                debug_log(f"[GLARE DEBUG] has_curtain={has_curtain}, max_bright_ratio={max_bright_ratio:.3f}, bright_std={bright_std:.1f}")
                
                if max_bright_ratio > 0.05 and bright_std > 15.0:
                    barriers_found += 1
                    glare_type = "direct_glare_bulb" if semantic_cat == "light_source" else "direct_glare_window"
                    suggestions.append(make_suggestion(
                        glare_type, bbox_format, poly_pts,
                    ))
        
        # ────────────────────────────────────────────────────
        # [COGNITIVE & PATTERN]
        # ────────────────────────────────────────────────────
        
        # Rule 6: Busy Patterns (Visual Noise)
        if semantic_cat in ("soft_floor_covering", "curtain_blind", "wall_surface", "seating_sleeping"):
            crop_blur = cv2.GaussianBlur(crop_gray, (5, 5), 0)
            edges = cv2.Canny(crop_blur, 50, 150)
            edge_density = np.count_nonzero(edges) / max(1, w * h)
            if edge_density > 0.10:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "busy_pattern", bbox_format, poly_pts,
                    lrv_diff=edge_density * 100,
                    score=edge_density * 100
                ))
        
        # Rule 8: Transparency (Invisible Glass Barriers)
        if semantic_cat == "glass_transparent":
            try:
                from skimage.feature import graycomatrix, graycoprops
                glcm_crop = cv2.resize(crop_gray, (64, 64))
                glcm_crop_q = (glcm_crop / 32).astype(np.uint8)
                glcm = graycomatrix(glcm_crop_q, distances=[1], angles=[0], levels=8, symmetric=True, normed=True)
                contrast = graycoprops(glcm, 'contrast')[0, 0]
                entropy = -np.sum(glcm * np.log2(glcm + 1e-10))
                
                if entropy > 2.0 and contrast > 1.5:
                    barriers_found += 1
                    suggestions.append(make_suggestion(
                        "transparency", bbox_format, poly_pts,
                    ))
            except ImportError:
                pass
        
        # Rule 9: Reflections & Ghosting (Mirrors)
        # Added strict size constraint (< 7% of image) so distant passageways aren't falsely flagged as mirrors
        if semantic_cat == "mirror_reflective" and obj_area_ratio < 0.07:
            barriers_found += 1
            suggestions.append(make_suggestion(
                "ghosting", bbox_format, poly_pts,
            ))
        
        # ────────────────────────────────────────────────────
        # [PHYSICAL SAFETY]
        # ────────────────────────────────────────────────────
        
        # Rule 7: Sharp Physical Edges
        if semantic_cat == "sharp_furniture":
            crop_blur = cv2.GaussianBlur(crop_gray, (5, 5), 0)
            corners = cv2.cornerHarris(np.float32(crop_blur), 2, 3, 0.04)
            corner_count = np.count_nonzero(corners > 0.05 * corners.max()) if corners.max() > 0 else 0
            if corner_count > 8:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "sharp_edges", bbox_format, poly_pts,
                ))
        
        # Rule 10: Protruding/Hanging Hazards
        if semantic_cat == "protruding_object":
            bottom_edge_ratio = (y1 + h) / img_h
            if bottom_edge_ratio < 0.60:  # Bottom edge above 60% of image = suspended
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "protruding", bbox_format, poly_pts,
                ))
        
        # ────────────────────────────────────────────────────
        # [AFFORDANCES]
        # ────────────────────────────────────────────────────
        
        # Rule 11: Hidden Affordances (doors/cabinets without labels)
        if semantic_cat in ("interior_door", "storage_cabinet"):
            has_signage = False
            for k, ocr_rect in enumerate(ocr_rects):
                if ocr_rect is None: continue
                if calculate_iou(bbox_format, ocr_rect) > 0.1:
                    has_signage = True
                    break
            if not has_signage:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "hidden_affordance", bbox_format, poly_pts,
                ))
        
        # ── Universal Camouflage Check (for remaining furniture/objects) ──
        if semantic_cat in ("sharp_furniture", "storage_cabinet", "other"):
            # Furniture with high-contrast edge linings is visually distinct and dementia-friendly
            has_edge_lining = has_contrasting_edge_lining(img_lab, bbox_format, grabcut_mask, o_lrv)
            
            if lrv_diff < 30.0 and not has_edge_lining:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "camouflage_standard", bbox_format, poly_pts,
                    lrv_diff=lrv_diff, o_lrv=o_lrv, b_lrv=b_lrv,
                    lrv=lrv_diff
                ))
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 4: SURFACE/ZONE HAZARD RULES (Tier 2, Rules 12-16)
    # ═══════════════════════════════════════════════════════════
    
    full_bbox = [0, 0, img_w, img_h]
    full_poly = [[0, 0], [img_w, 0], [img_w, img_h], [0, img_h]]
    
    # Calculate a specific bounding box for the floor to make UI highlights more accurate
    floor_bbox = full_bbox
    floor_poly = full_poly
    if np.any(floor_mask):
        floor_points = cv2.findNonZero(np.uint8(floor_mask))
        if floor_points is not None:
            fx, fy, fw, fh = cv2.boundingRect(floor_points)
            floor_bbox = [fx, fy, fw, fh]
            floor_poly = [[fx, fy], [fx+fw, fy], [fx+fw, fy+fh], [fx, fy+fh]]
    
    # Rule 12: Structural Boundary Loss (Wall-to-Floor Camouflage)
    if np.any(floor_mask) and np.any(wall_mask):
        # We dilate both masks by 20 pixels to create a 40-pixel "transition zone" where the wall meets the floor
        kernel_zone = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
        boundary_zone = (cv2.dilate(floor_mask, kernel_zone, iterations=1) == 1) & (cv2.dilate(wall_mask, kernel_zone, iterations=1) == 1)
        
        if np.any(boundary_zone):
            zone_points = cv2.findNonZero(np.uint8(boundary_zone))
            if zone_points is not None:
                zx, zy, zw, zh = cv2.boundingRect(zone_points)
                
                # Scan the transition zone in vertical columns. 
                # If there is a baseboard or a contrast between the wall and floor, 
                # the LRV inside this vertical column will have a high variance (light wall vs dark baseboard).
                col_contrasts = []
                for x in range(zx, zx + zw, 10):  # Sample every 10th column for speed
                    col_mask = boundary_zone[:, x]
                    if not np.any(col_mask): 
                        continue
                        
                    col_l = img_lab[:, x, 0][col_mask]
                    if len(col_l) < 5: 
                        continue
                        
                    # Absolute max and min to guarantee we catch even a 1-pixel thin baseboard
                    p_max = float(np.max(col_l)) / 255.0 * 100.0
                    p_min = float(np.min(col_l)) / 255.0 * 100.0
                    col_contrasts.append(p_max - p_min)
                
                if len(col_contrasts) > 0:
                    # Use median to ignore random floor clutter (like a black shoe) that might spike the contrast locally
                    median_contrast = np.median(col_contrasts)
                    
                    debug_log(f"[Rule 12 DEBUG] Median vertical contrast in transition zone = {median_contrast:.1f} (using absolute min/max)")
                    
                    if median_contrast < 30.0:
                        barriers_found += 1
                        suggestions.append(make_suggestion(
                            "boundary_loss", floor_bbox, floor_poly,
                            lrv_diff=median_contrast, o_lrv=0, b_lrv=0,
                            lrv=median_contrast
                        ))
    
    # Rule 13: Striped/Grid Shadows (Gait-Freezing)
    if np.any(floor_mask):
        floor_gray = img_gray.copy()
        floor_gray[floor_mask == 0] = 128  # Neutral out non-floor pixels
        
        # Apply Gabor filters at multiple orientations to detect parallel bands
        gabor_energies = []
        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            gabor_kernel = cv2.getGaborKernel((45, 45), 8.0, theta, 30.0, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(floor_gray, cv2.CV_32F, gabor_kernel)
            floor_energy = np.mean(np.abs(filtered[floor_mask == 1])) if np.any(floor_mask) else 0
            gabor_energies.append(floor_energy)
        
        max_gabor_energy = max(gabor_energies)
        min_gabor_energy = max(min(gabor_energies), 1.0)  # Avoid division by zero
        
        # Directionality ratio: real blind shadows are strongly directional (high ratio),
        # floor glare is omnidirectional (ratio ≈ 1.0)
        directionality_ratio = max_gabor_energy / min_gabor_energy
        
        # Calculate Canny edge density
        floor_blur = cv2.GaussianBlur(floor_gray, (5, 5), 0)
        floor_edges = cv2.Canny(floor_blur, 50, 150)
        floor_area = np.count_nonzero(floor_mask)
        edge_density = np.count_nonzero(floor_edges[floor_mask == 1]) / max(1, floor_area)
        
        # Calculate floor brightness standard deviation
        floor_l_values = img_lab[:, :, 0][floor_mask == 1]
        floor_l_std = float(np.std(floor_l_values)) if len(floor_l_values) > 0 else 0
        
        debug_log(f"[Rule 13 DEBUG] Gabor energy: {max_gabor_energy:.1f}, Directionality: {directionality_ratio:.2f}, Floor L std: {floor_l_std:.1f}")
        
        # All THREE conditions must be met:
        # 1. High Gabor energy (strong repeating pattern detected)
        # 2. High L-channel std dev (>30.0) = extreme bright/dark alternation (not just carpet texture)
        # 3. High directionality (>1.5) = pattern is concentrated in one direction (striped), not omnidirectional (glare)
        if max_gabor_energy > 100.0 and floor_l_std > 30.0 and directionality_ratio > 1.5:
            barriers_found += 1
            suggestions.append(make_suggestion(
                "striped_shadows", floor_bbox, floor_poly
            ))
    
    # Rule 14: Shadows & Dark Zones (on floor)
    if np.any(floor_mask):
        floor_l = img_lab[:, :, 0][floor_mask == 1]
        if len(floor_l) > 0:
            _, shadow_thresh = cv2.threshold(img_lab[:, :, 0], 40, 255, cv2.THRESH_BINARY_INV)
            shadow_on_floor = shadow_thresh[floor_mask == 1]
            shadow_ratio = np.count_nonzero(shadow_on_floor) / max(1, len(floor_l))
            if shadow_ratio > 0.10:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "deep_shadows", floor_bbox, floor_poly,
                    score=shadow_ratio * 100
                ))
    
    # Rule 16: Misleading Illusions (Trompe-l'œil) — Conditional on wall_surface detection
    if found_wall_surface and cv_models.flo_model:
        try:
            vqa_result = cv_models.run_florence_task(
                pil_image, "<VQA>",
                "Does this room contain a realistic painting or mural of a doorway, window, or hallway on the wall? Answer yes or no."
            )
            vqa_text = str(vqa_result.get('<VQA>', '')).lower()
            if 'yes' in vqa_text:
                barriers_found += 1
                suggestions.append(make_suggestion(
                    "illusion", full_bbox, full_poly,
                ))
        except Exception:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # PHASE 5: GLOBAL ROOM HAZARD RULES (Tier 3, Rules 17-21)
    # ═══════════════════════════════════════════════════════════
    
    # Rule 17: Spatial Clutter (Cognitive Overload)
    if clutter_boxes:
        total_clutter_area = sum(b[2] * b[3] for b in clutter_boxes)
        clutter_ratio = total_clutter_area / max(1, img_w * img_h)
        if clutter_ratio > 0.15:
            # Bounding box enclosing all clutter items
            all_x1 = min(b[0] for b in clutter_boxes)
            all_y1 = min(b[1] for b in clutter_boxes)
            all_x2 = max(b[0] + b[2] for b in clutter_boxes)
            all_y2 = max(b[1] + b[3] for b in clutter_boxes)
            clutter_bbox = [all_x1, all_y1, all_x2 - all_x1, all_y2 - all_y1]
            clutter_poly = [[all_x1, all_y1], [all_x2, all_y1], [all_x2, all_y2], [all_x1, all_y2]]
            barriers_found += 1
            suggestions.append(make_suggestion(
                "clutter", clutter_bbox, clutter_poly,
                score=clutter_ratio * 100
            ))
    
    # Rule 18: Illumination Transitions
    left_half_l = img_lab[:, :img_w//2, 0]
    right_half_l = img_lab[:, img_w//2:, 0]
    left_avg = float(np.mean(left_half_l)) if left_half_l.size > 0 else 1.0
    right_avg = float(np.mean(right_half_l)) if right_half_l.size > 0 else 1.0
    
    if min(left_avg, right_avg) > 0:
        transition_ratio = max(left_avg, right_avg) / max(1.0, min(left_avg, right_avg))
        if transition_ratio > 2.0:
            barriers_found += 1
            suggestions.append(make_suggestion(
                "illumination_transition", full_bbox, full_poly,
                score=transition_ratio
            ))
    
    # Rule 19: Overall Low Illuminance
    if np.any(floor_mask):
        functional_l = img_lab[:, :, 0][floor_mask == 1]
    else:
        functional_l = img_lab[:, :, 0].flatten()
    
    avg_illuminance = float(np.mean(functional_l)) if len(functional_l) > 0 else 128.0
    if avg_illuminance < 80.0:
        barriers_found += 1
        suggestions.append(make_suggestion(
            "low_illuminance", full_bbox, full_poly,
            score=avg_illuminance
        ))
    
    # Rule 20: Overstimulating Color Saturation
    img_hsv = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2HSV)
    h_channel = img_hsv[:, :, 0]  # OpenCV H is 0-180
    s_channel = img_hsv[:, :, 1]  # OpenCV S is 0-255
    
    # High saturation + red/orange/yellow hues (H < 30 or H > 150 in OpenCV scale)
    high_sat_mask = s_channel > 180
    arousal_hue_mask = (h_channel < 30) | (h_channel > 150)
    overstimulating_mask = high_sat_mask & arousal_hue_mask
    
    overstim_ratio = np.count_nonzero(overstimulating_mask) / max(1, img_w * img_h)
    if overstim_ratio > 0.20:
        barriers_found += 1
        suggestions.append(make_suggestion(
            "color_saturation", full_bbox, full_poly,
            score=overstim_ratio * 100
        ))
    
    # Rule 21: Sightline Obstructions
    for t_box in tested_areas:
        box_area = t_box[2] * t_box[3]
        area_ratio = box_area / max(1, img_w * img_h)
        
        if area_ratio > 0.15:
            # Check if the object is in the central vertical third
            box_center_y = t_box[1] + t_box[3] / 2
            if img_h * 0.33 < box_center_y < img_h * 0.66:
                horizontal_coverage = t_box[2] / img_w
                if horizontal_coverage > 0.40:
                    poly = [[t_box[0], t_box[1]], [t_box[0]+t_box[2], t_box[1]], 
                            [t_box[0]+t_box[2], t_box[1]+t_box[3]], [t_box[0], t_box[1]+t_box[3]]]
                    barriers_found += 1
                    suggestions.append(make_suggestion(
                        "sightline", t_box, poly,
                    ))
    
    # ═══════════════════════════════════════════════════════════
    # ENCODE RESPONSE
    # ═══════════════════════════════════════════════════════════
    
    _, buffer = cv2.imencode('.jpg', img_cv2)
    b64_string = base64.b64encode(buffer).decode('utf-8')
    data_uri = f"data:image/jpeg;base64,{b64_string}"
    
    return AuditResponse(
        status="success",
        is_valid_indoor=True,
        original_annotated_url=data_uri,
        transformed_after_url=None,
        barriers_found=barriers_found,
        suggestions=suggestions
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
