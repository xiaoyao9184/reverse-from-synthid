import os
import sys
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

APP_DIR = Path(__file__).resolve().parent
REPO_DIR = Path(
    os.environ.get("APP_PATH", APP_DIR.parent / "reverse-SynthID")
).resolve()

# fix sys.path for import
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
os.chdir(REPO_DIR)
if str(REPO_DIR) not in sys.path:
    sys.path.append(str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "src" / "extraction"))

import cv2
import numpy as np

from synthid_bypass import SynthIDBypass, SpectralCodebook
from synthid_bypass_v4 import SynthIDBypassV4, SpectralCodebookV4
from robust_extractor import RobustSynthIDExtractor

CODEBOOK_PATH = REPO_DIR / "artifacts" / "spectral_codebook_v3.npz"
DETECTOR_CODEBOOK_PATH = REPO_DIR / "artifacts" / "codebook" / "robust_codebook.pkl"
V4_CODEBOOK_PATH = REPO_DIR / "artifacts" / "spectral_codebook_v4.npz"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def normalize_rgb_image(image):
    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        return image

    img_bgr = cv2.imread(str(image))
    if img_bgr is None:
        raise ValueError(f"Could not load: {image}")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def json_safe(value):
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def result_summary(result):
    data = json_safe(result)
    data.pop("cleaned_image", None)
    return data


def find_exact_v4_profile(h: int, w: int, v4_codebook: SpectralCodebookV4,
                           tolerance: float = 0.003):
    """Find a V4 codebook profile that (h, w) is a clean scaled and/or
    90-degree-rotated version of, based on a strict aspect-ratio match.

    Real Gemini downloads that don't exactly match one of the codebook's 14
    captured resolutions are typically a clean integer up-scale of one of
    them (e.g. exactly 2.000x in both dimensions after accounting for a
    90-degree rotation) — some delivery paths export at a higher resolution
    than the one the reference set was built from. An unrelated image that
    merely has a similar aspect ratio by coincidence will not hit this tight
    a tolerance (empirically: genuine matches land at ~0.00% deviation,
    coincidental ones at 1.5%+), so this is deliberately strict rather than
    "closest available profile" — a loose match is worse than no match, since
    resizing to fit a wrong profile is what produces false positives.

    Returns (target_h, target_w, needs_rotation) for the tightest match
    within tolerance, or None if nothing matches closely enough to trust.
    """
    img_ar = h / w
    seen_resolutions = set()
    best = None
    for (_, ph, pw) in v4_codebook.profiles:
        if (ph, pw) in seen_resolutions:
            continue
        seen_resolutions.add((ph, pw))
        profile_ar = ph / pw
        # Rotating the image 90 degrees swaps its H/W, so its aspect ratio
        # becomes 1/img_ar; the resize target is always the profile's own
        # (ph, pw) either way, only the orientation to compare against differs.
        for rotate, candidate_ar in [(False, profile_ar), (True, pw / ph)]:
            diff = abs(img_ar - candidate_ar) / candidate_ar
            if best is None or diff < best[0]:
                best = (diff, ph, pw, rotate)
    if best is not None and best[0] <= tolerance:
        return best[1], best[2], best[3]
    return None

def detect_watermark(path: str, detector: RobustSynthIDExtractor,
                      v4_codebook: SpectralCodebookV4):
    """Check for a SynthID watermark, combining the V3 detector (works at
    any resolution but loses some signal to its fixed 512x512 stretch) with
    the V4 detector (native-resolution, much more sensitive, but only valid
    at an exact profile match) when a trustworthy V4 match exists. Returns
    the more confident of the two.
    """
    img = normalize_rgb_image(path)
    h, w = img.shape[:2]

    candidates = [detector.detect_array(img)]

    match = find_exact_v4_profile(h, w, v4_codebook)
    if match is not None:
        target_h, target_w, rotate = match
        oriented = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE) if rotate else img
        resized = cv2.resize(oriented, (target_w, target_h), interpolation=cv2.INTER_AREA)
        for model in v4_codebook.models:
            candidates.append(
                detector.detect_from_v4_codebook(resized, v4_codebook, model=model))

    return max(candidates, key=lambda r: r.confidence)

def remove_watermark_v1(path: str,
                        bypass: SynthIDBypass,
                        mode: str = "balanced",
                        verify: bool = True):
    img = normalize_rgb_image(path)
    return bypass.bypass(img, mode=mode, verify=verify)


def remove_watermark_v2(path: str,
                        bypass: SynthIDBypass,
                        strength: str = "aggressive",
                        iterations: int = 2,
                        verify: bool = True):
    img = normalize_rgb_image(path)
    return bypass.bypass_v2(
        img,
        strength=strength,
        iterations=int(iterations),
        verify=verify,
    )


def remove_watermark_v3(path: str,
                        bypass: SynthIDBypass,
                        codebook: SpectralCodebook,
                        strength: str = "moderate",
                        passes: int = 0,
                        verify: bool = True):
    img = normalize_rgb_image(path)
    return bypass.bypass_v3(
        img,
        codebook,
        strength=strength,
        passes=int(passes),
        verify=verify,
    )


def remove_watermark_v4(path: str,
                        bypass4: SynthIDBypassV4,
                        codebook4: SpectralCodebookV4,
                        strength: str = "final",
                        model: str = "Auto",
                        verify: bool = True):
    img = normalize_rgb_image(path)
    model = None if model == "Auto" else model
    if strength in bypass4.FINAL_PRESETS:
        return bypass4.bypass_v4_final(
            img, codebook4, strength=strength, model=model)
    if strength in bypass4.REGEN_PRESETS:
        return bypass4.bypass_v4_regen(
            img, codebook4, strength=strength, model=model)
    if strength in bypass4.UNIVERSAL_PRESETS:
        return bypass4.bypass_v4_universal(
            img, codebook4, strength=strength, model=model)
    return bypass4.bypass_v4(
        img, codebook4, strength=strength, model=model, verify=verify)

@lru_cache(maxsize=1)
def load_codebook():
    detector = RobustSynthIDExtractor(codebook_path=str(DETECTOR_CODEBOOK_PATH))

    bypass = SynthIDBypass(extractor=detector)
    codebook = SpectralCodebook()
    codebook.load(str(CODEBOOK_PATH))

    v4_bypass = SynthIDBypassV4(extractor=detector)
    v4_codebook = SpectralCodebookV4()
    v4_codebook.load(str(V4_CODEBOOK_PATH))

    return SimpleNamespace(
        detector=detector,
        bypass=bypass,
        codebook=codebook,
        v4_bypass=v4_bypass,
        v4_codebook=v4_codebook,
    )

codebook = load_codebook()

import gradio as gr
from telemetry_counter import patch_button_click

patch_button_click()

V1_MODES = ["light", "balanced", "aggressive", "maximum"]
V2_STRENGTHS = ["moderate", "aggressive", "maximum"]
V3_STRENGTHS = ["gentle", "moderate", "aggressive", "maximum"]
V4_STRENGTHS = (
    list(codebook.v4_bypass.FINAL_PRESETS)
    + list(codebook.v4_bypass.REGEN_PRESETS)
    + list(codebook.v4_bypass.UNIVERSAL_PRESETS)
    + list(codebook.v4_bypass.STRENGTH_PRESETS)
)
V4_MODELS = ["Auto"] + codebook.v4_codebook.models

with gr.Blocks() as demo:
    gr.Markdown(
    """
    # ⚓ Reverse SynthId watermark for detect and remov

    Find the original project [here](https://github.com/aloshdenny/reverse-SynthID).
    Or this project [here](https://github.com/xiaoyao9184/reverse-from-synthid).
    """)

    with gr.Row():
        with gr.Column(scale=1):
            input_img = gr.Image(label="Input Image", type="numpy")
        with gr.Column(scale=1):
            with gr.Tabs():
                with gr.TabItem("Detect"):
                    detecting_btn = gr.Button("Detect")
                with gr.TabItem("Remove V1"):
                    removing_v1_mode = gr.Radio(
                        choices=V1_MODES,
                        value="balanced",
                        label="V1 mode",
                    )
                    removing_v1_verify = gr.Checkbox(value=True, label="V1 verify")
                    removing_v1_btn = gr.Button("Remove V1")
                with gr.TabItem("Remove V2"):
                    removing_v2_strength = gr.Radio(
                        choices=V2_STRENGTHS,
                        value="aggressive",
                        label="V2 strength",
                    )
                    removing_v2_iterations = gr.Slider(
                        minimum=1,
                        maximum=6,
                        value=2,
                        step=1,
                        label="V2 iterations",
                    )
                    removing_v2_verify = gr.Checkbox(value=True, label="V2 verify")
                    removing_v2_btn = gr.Button("Remove")
                with gr.TabItem("Remove V3"):
                    removing_v3_strength = gr.Radio(
                        choices=V3_STRENGTHS,
                        value="moderate",
                        label="V3 strength",
                    )
                    removing_v3_passes = gr.Slider(
                        minimum=0,
                        maximum=6,
                        value=0,
                        step=1,
                        label="V3 passes",
                    )
                    removing_v3_verify = gr.Checkbox(value=True, label="V3 verify")
                    removing_v3_btn = gr.Button("Remove V3")
                with gr.TabItem("Remove V4"):
                    removing_v4_strength = gr.Dropdown(
                        choices=V4_STRENGTHS,
                        value="final",
                        label="V4 preset",
                    )
                    removing_v4_model = gr.Dropdown(
                        choices=V4_MODELS,
                        value="Auto",
                        label="V4 model",
                    )
                    removing_v4_verify = gr.Checkbox(value=True, label="V4 verify")
                    removing_v4_btn = gr.Button("Remove V4")
            output_json = gr.JSON(label="Output result", max_height=None)
        with gr.Column(scale=1):
            output_img = gr.Image(label="Output image", type="numpy")

    def detecting_watermark(img: np.ndarray):
        det = detect_watermark(img, codebook.detector, codebook.v4_codebook)
        return [gr.update(value=json_safe(det))]
    detecting_btn.click(
        fn=detecting_watermark,
        inputs=[input_img],
        outputs=[output_json],
        api_name="detecting_watermark",
    )
    # gr.api(detecting_watermark, api_name="detecting_watermark")

    def format_remove_result(result):
        return [
            gr.update(value=result_summary(result)),
            gr.update(value=result.cleaned_image),
        ]

    def handle_remove_v1(
        img: np.ndarray, mode: str, verify: bool
    ):
        result = remove_watermark_v1(
            img,
            codebook.bypass,
            mode=mode,
            verify=verify,
        )
        return format_remove_result(result)

    def handle_remove_v2(
        img: np.ndarray, strength: str, iterations: int, verify: bool
    ):
        result = remove_watermark_v2(
            img,
            codebook.bypass,
            strength=strength,
            iterations=iterations,
            verify=verify,
        )
        return format_remove_result(result)

    def handle_remove_v3(
        img: np.ndarray, strength: str, passes: int, verify: bool
    ):
        result = remove_watermark_v3(
            img,
            codebook.bypass,
            codebook.codebook,
            strength=strength,
            passes=passes,
            verify=verify,
        )
        return format_remove_result(result)

    def handle_remove_v4(
        img: np.ndarray, strength: str, model: str, verify: bool
    ):
        result = remove_watermark_v4(
            img,
            codebook.v4_bypass,
            codebook.v4_codebook,
            strength=strength,
            model=model,
            verify=verify,
        )
        return format_remove_result(result)

    removing_v1_btn.click(
        fn=handle_remove_v1,
        inputs=[
            input_img,
            removing_v1_mode,
            removing_v1_verify,
        ],
        outputs=[output_json, output_img],
        api_name="removing_watermark_v1",
    )
    removing_v2_btn.click(
        fn=handle_remove_v2,
        inputs=[
            input_img,
            removing_v2_strength,
            removing_v2_iterations,
            removing_v2_verify,
        ],
        outputs=[output_json, output_img],
        api_name="removing_watermark_v2",
    )
    removing_v3_btn.click(
        fn=handle_remove_v3,
        inputs=[
            input_img,
            removing_v3_strength,
            removing_v3_passes,
            removing_v3_verify,
        ],
        outputs=[output_json, output_img],
        api_name="removing_watermark_v3",
    )
    removing_v4_btn.click(
        fn=handle_remove_v4,
        inputs=[
            input_img,
            removing_v4_strength,
            removing_v4_model,
            removing_v4_verify,
        ],
        outputs=[output_json, output_img],
        api_name="removing_watermark_v4",
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
