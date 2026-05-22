#!/usr/bin/env python3
"""Read an image via OpenRouter vision models (Qwen). 

Usage:
    python3 read_image.py <image_path> <question> [--model qwen/qwen3.5-9b]
    
Or import as a module:
    from read_image import read_image
    text = read_image("/tmp/screenshot.png", "What does this show?")
"""
import os, base64, json, urllib.request, sys

def read_image(image_path, question, model="qwen/qwen3.5-9b"):
    """Send an image to OpenRouter vision and return text description."""
    try:
        from PIL import Image
        import io
    except ImportError:
        raise ImportError("Pillow required: pip install Pillow")
    
    # Downscale to <=1568px on long side
    img = Image.open(image_path)
    max_dim = 1568
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    
    # Get API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 read_image.py <image_path> <question> [--model MODEL]")
        sys.exit(1)
    
    img_path = sys.argv[1]
    question = sys.argv[2]
    model = "qwen/qwen3.5-9b"
    
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]
    
    result = read_image(img_path, question, model)
    print(result)
