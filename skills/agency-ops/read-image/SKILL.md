---
name: read-image
description: Read screenshots, dec pages, and carrier documents via OpenRouter vision models (Qwen). Handles image capture, downscaling, base64 encoding, and API calls.
tags: [vision, ocr, openrouter, qwen, image, screenshot, dec-page, carrier-doc]
---

# Read Image — OpenRouter Vision Utility

Send images (screenshots, dec pages, PDFs, carrier docs) to OpenRouter vision models and get text descriptions back. Used when you can't read an image directly.

## Quick Usage

```python
from read_image import read_image

# From a file path
text = read_image("/tmp/screenshot.png", "Extract the premium amount and coverage limits from this dec page")

# From a Playwright screenshot
page.screenshot(path="/tmp/logic_portal.png")
text = read_image("/tmp/logic_portal.png", "What validation errors are shown on this form?")
```

## Python Function

```python
import os, base64, json, urllib.request

def read_image(image_path, question, model="qwen/qwen3.5-9b"):
    """
    Send an image to OpenRouter vision model and return the text description.
    
    Args:
        image_path: Path to image file (PNG, JPG, WebP)
        question: What you want to know about the image
        model: "qwen/qwen3.5-9b" (fast) or "qwen/qwen3.5-35b-a3b" (better for messy scans)
    
    Returns:
        str: Model's text description of the image
    """
    from PIL import Image
    import io
    
    # Downscale to <=1568px on long side (saves tokens, avoids size limits)
    img = Image.open(image_path)
    max_dim = 1568
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Convert to base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    # Send to OpenRouter
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        # Try credentials file
        cred_path = os.path.expanduser("~/.config/libertas/credentials.env")
        if os.path.exists(cred_path):
            with open(cred_path) as f:
                for line in f:
                    if line.startswith("OPENROUTER_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        break
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in env or credentials.env")
    
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }]
    }
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )
    
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]
```

## Capture Patterns

### Playwright Browser Screenshot
```python
# Full page
page.screenshot(path="/tmp/page.png")

# Specific element
element = page.query_selector('#form-frame')
element.screenshot(path="/tmp/form.png")

# A specific frame's content
for f in page.frames:
    if 'uwp2hob' in f.url:
        # Frame screenshots need the parent page to clip
        page.screenshot(path="/tmp/form_frame.png", clip=f.evaluate(
            "() => { const r = document.querySelector('#targetFrame').getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height} }"
        ))
        break
```

### From an Existing File (dec page, PDF page, etc.)
```python
# PDF → image first (if needed)
# pdftoppm -png -r 200 document.pdf /tmp/page
# Then: read_image("/tmp/page-1.png", "Extract coverages")
```

## Model Selection

| Model | Use Case | Speed | Quality |
|-------|----------|-------|---------|
| `qwen/qwen3.5-9b` | Clean screenshots, typed text, form fields | Fast | Good |
| `qwen/qwen3.5-35b-a3b` | Messy scans, handwritten notes, low-quality faxes | Slower | Better |

**Rule**: Try 9b first. If the result is unclear or garbled, retry with 35b-a3b.

## Pitfalls

- **Image format**: MUST send as base64 `data:image/png;base64,...` URL in the content array. NOT as a plain text path.
- **Downscale first**: Images >1568px on the long side waste tokens and may hit size limits. Always resize before sending.
- **API key location**: `OPENROUTER_API_KEY` in env or `~/.config/libertas/credentials.env`. Never hardcode.
- **Timeout**: Large images or complex questions may need >30s. Set timeout to 60s.
- **Retry on failure**: If 9b returns garbage, retry with 35b-a3b. If both fail, the image may be unreadable.
- **No data retention**: OpenRouter is set to zero-data-retention. Client data stays private.
