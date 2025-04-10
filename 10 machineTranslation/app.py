import os
import gc
import warnings
import torch
from flask import Flask, request, render_template, jsonify
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
from typing import Callable, Union, Dict, List, Any
from functools import lru_cache
from waitress import serve
from flask_compress import Compress

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings("ignore", category=UserWarning)

app = Flask(__name__)
Compress(app)

# Type alias for the translator function
TranslatorType = Callable[[Union[str, List[str]]], List[Dict[str, str]]]

# Global variables
translator: TranslatorType = None
model_loaded = False

# Create a compatible dummy translator that doesn't rely on closure scope
def create_dummy_translator(error_msg):
    def dummy_translator(text, **kwargs):
        if isinstance(text, list):
            return [{'translation_text': f"Service unavailable: {error_msg}"} for _ in text]
        return [{'translation_text': f"Service unavailable: {error_msg}"}]
    return dummy_translator

def initialize_translator() -> TranslatorType:
    try:
        # Try the simplest approach with the Helsinki model directly
        print("Loading translation model directly...")
        return pipeline("translation_en_to_de", model="Helsinki-NLP/opus-mt-en-de")
    
    except Exception as e:
        error_msg = str(e)
        print(f"Critical error initializing translator: {error_msg}")
        return create_dummy_translator(error_msg)

# Alternative to before_first_request for newer Flask versions
def get_translator():
    global translator, model_loaded
    if not model_loaded:
        print("Loading translator model...")
        translator = initialize_translator()
        model_loaded = True
        print("Model loaded successfully")
    return translator

# Simple caching for frequently translated content
@lru_cache(maxsize=1000)
def cached_translate(text: str) -> str:
    trans = get_translator()
    try:
        result = trans(text, max_length=400)[0]['translation_text']
        return result.replace('&quot;', '"')
    except Exception as e:
        print(f"Translation error in cached_translate: {str(e)}")
        return f"Translation error: {str(e)}"

# Batch processing function
def batch_translate(texts: List[str]) -> List[str]:
    trans = get_translator()
    try:
        results = trans(texts, max_length=400, batch_size=16)
        return [r['translation_text'].replace('&quot;', '"') for r in results]
    except Exception as e:
        print(f"Translation error in batch_translate: {str(e)}")
        return [f"Translation error: {str(e)}"] * len(texts)

def clear_gpu_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

@app.route("/", methods=["GET", "POST"])
def translate():
    if request.method == "POST":
        original = request.form.get("text", "")
        if original.strip():
            try:
                result = cached_translate(original)
                return render_template("index.html", 
                                   translation=result,
                                   original=original)
            except Exception as e:
                print(f"Translation route error: {str(e)}")
                return render_template("index.html", 
                                   translation=f"Translation error occurred: {str(e)}",
                                   original=original)
    
    return render_template("index.html")

@app.route("/api/translate", methods=["POST"])
def api_translate():
    try:
        data = request.get_json()
        if not data or "texts" not in data:
            return jsonify({"error": "Invalid request format"}), 400
            
        texts = data["texts"]
        if not isinstance(texts, list) or len(texts) > 100:
            return jsonify({"error": "Texts must be a list with max 100 items"}), 400
            
        results = batch_translate(texts)
        return jsonify({"translations": results})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "model_loaded": model_loaded})

@app.route("/admin/clear-memory", methods=["POST"])
def admin_clear_memory():
    # Add authentication here in real application
    auth_token = request.headers.get("Authorization")
    if not auth_token or auth_token != os.environ.get("ADMIN_TOKEN", "default_secret_token"):
        return jsonify({"error": "Unauthorized"}), 401
        
    clear_gpu_memory()
    return jsonify({"status": "memory cleared"})

if __name__ == "__main__":
    if not os.path.exists("templates"):
        os.makedirs("templates")
    
    # Development mode
    if os.environ.get("FLASK_ENV") == "development":
        app.run(host="0.0.0.0", port=5330, debug=True)
    # Production mode
    else:
        # Use a production WSGI server
        print("Running in production mode")
        serve(app, host="0.0.0.0", port=5330, threads=4)