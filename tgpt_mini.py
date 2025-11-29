#!/usr/bin/env python3
"""
tgpt-mini: Compact Free AI Chatbot CLI
Single-file implementation with FREE providers only (No API Key Required)
Version: 1.2.0 | License: MIT
"""

import argparse
import json
import os
import sys
import subprocess
import signal
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

try:
    import requests
except ImportError:
    print("Error: requests library required. Install: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Kiểm tra Python version
if sys.version_info < (3, 7):
    print("Error: Python 3.7+ required", file=sys.stderr)
    sys.exit(1)

VERSION = "1.2.0"

# ============================================================================
# SYSTEM PROMPTS - Các prompt mạnh mẽ, ngắn gọn cho từng use case
# ============================================================================

# Prompt tạo image prompt - mạnh mẽ, tạo prompt dài chi tiết (200+ chars)
IMAGE_PROMPT_SYSTEM = """Transform idea into LONG detailed English image prompt (200-400 chars minimum).

MUST include: detailed subject description, specific environment/background, lighting type, mood/atmosphere, art style, AND quality tags (8K, highly detailed, masterpiece).

Example output format:
"A young woman with long flowing hair sitting at wooden desk by rain-streaked window, orange cat sleeping on cushion beside her, warm cozy room with bookshelves and plants, soft golden lamp light, peaceful relaxed atmosphere, lofi aesthetic digital art style, highly detailed, 8K, masterpiece"

Output ONLY the prompt. No explanations. Single paragraph."""

# Prompt cho code generation
CODE_PROMPT_SYSTEM = """You are an expert programmer. Generate clean, efficient code.

RULES:
- Output ONLY the code, no explanations unless asked
- Include comments for complex logic
- Follow best practices and conventions
- Handle edge cases"""

# Prompt cho text enhancement/rewrite
TEXT_ENHANCE_SYSTEM = """You are a content writer. Enhance and improve text while keeping the original meaning.

RULES:
- Output ONLY the enhanced text
- Maintain the original language
- Improve clarity, flow, and impact
- Keep the same tone"""

# Prompt cho translation
TRANSLATE_SYSTEM = """You are a translator. Translate text accurately and naturally.

RULES:
- Output ONLY the translated text
- Maintain meaning and tone
- Use natural expressions in target language
- Keep formatting if any"""

# =============================================================================
# LOFI/CHILL FRAME-CONTEXT - Load từ YAML file hoặc fallback to hardcoded
# =============================================================================

# Fallback system prompt nếu không đọc được YAML
_LOFI_SYSTEM_PROMPT_FALLBACK = """You are an image prompt generator. Transform Vietnamese idea into English lofi 2.5D image prompt.

CRITICAL: Output ONLY the final prompt text. NO introductions like "Here's...", NO explanations, NO markdown.

FORMAT (single paragraph, 100-200 words):
"A warm 2.5D cartoon illustration... [character description]... In the foreground... Behind... 2.5D layered composition. Lofi chill aesthetic. [colors]. [mood]."

STRUCTURE:
1. Style opener: "A warm/cozy 2.5D cartoon illustration featuring [character]"
2. Character: action, clothing, expression
3. Foreground: "In the foreground" + surface + 3 props
4. Background: "Behind" mid-ground + "distant background" blurred + lighting
5. Close: "2.5D layered composition. Lofi chill aesthetic. Color palette. Mood."

RULES:
- Peaceful activities only (reading, coffee, relaxing)
- 1-2 characters, 3-5 props
- Warm colors: golden, orange, pastel
- Must include depth keywords: "foreground", "behind", "distant background", "softly blurred"

START OUTPUT DIRECTLY WITH: "A warm" or "A cozy" """

# Cache cho lofi config
_LOFI_CONFIG_CACHE = None

def _get_lofi_yaml_path() -> str:
    """Get path to lofi_frame_context.yaml file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "lofi_frame_context.yaml")

def load_lofi_config() -> dict:
    """
    Load lofi frame-context config từ YAML file.
    Sử dụng cache để tránh đọc file nhiều lần.
    
    Returns:
        dict: Config với keys: system_prompt, reference, examples, etc.
    """
    global _LOFI_CONFIG_CACHE
    
    if _LOFI_CONFIG_CACHE is not None:
        return _LOFI_CONFIG_CACHE
    
    if not YAML_AVAILABLE:
        _LOFI_CONFIG_CACHE = {"system_prompt": _LOFI_SYSTEM_PROMPT_FALLBACK}
        return _LOFI_CONFIG_CACHE
    
    yaml_path = _get_lofi_yaml_path()
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            _LOFI_CONFIG_CACHE = config
            return config
    except FileNotFoundError:
        print(f"Warning: lofi_frame_context.yaml not found at {yaml_path}, using fallback", file=sys.stderr)
        _LOFI_CONFIG_CACHE = {"system_prompt": _LOFI_SYSTEM_PROMPT_FALLBACK}
        return _LOFI_CONFIG_CACHE
    except Exception as e:
        print(f"Warning: Error loading lofi_frame_context.yaml: {e}, using fallback", file=sys.stderr)
        _LOFI_CONFIG_CACHE = {"system_prompt": _LOFI_SYSTEM_PROMPT_FALLBACK}
        return _LOFI_CONFIG_CACHE

def get_lofi_system_prompt() -> str:
    """
    Get system prompt cho lofi/chill image generation.
    Đọc từ YAML file hoặc sử dụng fallback.
    
    Returns:
        str: System prompt tối ưu cho lofi 2.5D style
    """
    config = load_lofi_config()
    return config.get("system_prompt", _LOFI_SYSTEM_PROMPT_FALLBACK)

def get_lofi_reference() -> dict:
    """
    Get reference data (props, actions, lighting, colors) từ YAML.
    
    Returns:
        dict: Reference data với keys: props, actions, expressions, lighting, colors
    """
    config = load_lofi_config()
    return config.get("reference", {})

def get_lofi_examples() -> list:
    """
    Get ví dụ từ YAML file.
    
    Returns:
        list: List các examples với input/output
    """
    config = load_lofi_config()
    return config.get("examples", [])

# Legacy: giữ biến LOFI_SYSTEM_PROMPT cho backward compatibility
# Sử dụng lazy loading - chỉ đọc khi cần
class _LazyLofiPrompt:
    """Lazy loader cho LOFI_SYSTEM_PROMPT để tránh đọc file khi import."""
    _value = None
    
    def __str__(self):
        if self._value is None:
            self._value = get_lofi_system_prompt()
        return self._value
    
    def __repr__(self):
        return str(self)

LOFI_SYSTEM_PROMPT = _LazyLofiPrompt()

# Style keywords để detect lofi/chill
LOFI_STYLE_KEYWORDS = [
    "lofi", "lo-fi", "lo fi", "chill", "cozy", "ấm cúng", "thư giãn",
    "pusheen", "snoopy", "cute cat", "mèo cute", "cartoon cat",
    "picnic", "campfire", "lửa trại", "đọc sách", "reading",
    "2.5d", "2.5 d", "chiều sâu", "độ sâu", "layered"
]

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Params:
    """Request parameters"""
    provider: str = "phind"
    model: str = ""
    url: str = ""
    temperature: float = 0.7
    top_p: float = 1.0
    preprompt: str = ""
    thread_id: str = ""
    system_prompt: str = ""
    prev_messages: List[Dict] = field(default_factory=list)

@dataclass
class Options:
    """Runtime options"""
    quiet: bool = False
    auto_exec: bool = False
    log_file: str = ""
    verbose: bool = False
    whole_text: bool = False

# ============================================================================
# UTILITIES
# ============================================================================

class C:
    """Colors"""
    R, G, Y, B, C, M, W = "\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[96m", "\033[95m", "\033[0m"
    BOLD = "\033[1m"

def error(msg: str): print(f"{C.R}Error: {msg}{C.W}", file=sys.stderr)
def info(msg: str): print(f"{C.B}{msg}{C.W}")
def success(msg: str): print(f"{C.G}{msg}{C.W}")

def log(text: str, role: str, path: str):
    """Log to file"""
    if path:
        try:
            with open(path, "a") as f: f.write(f"\n[{role}]\n{text}\n")
        except: pass

def clean_response(text: str) -> str:
    """
    Loại bỏ các ký tự spinner, text Loading và control characters khỏi response.
    
    Args:
        text: Response text từ provider
        
    Returns:
        Text đã được clean, chỉ chứa nội dung thực tế
    """
    if not text:
        return text
    
    # Loại bỏ các ký tự spinner Unicode (Braille patterns U+2800-U+28FF)
    # Các ký tự spinner thường gặp: ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷
    spinner_pattern = re.compile(r'[\u2800-\u28FF]')
    text = spinner_pattern.sub('', text)
    
    # Loại bỏ các dòng chỉ chứa "Loading" (case-insensitive) hoặc spinner + "Loading"
    # Không loại bỏ các dòng có nội dung thực tế chứa từ "loading"
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        # Chỉ loại bỏ nếu dòng chỉ chứa "Loading" (có thể kèm spinner đã bị loại bỏ ở trên)
        # Pattern: chỉ "Loading" hoặc "Loading" với whitespace
        if line_stripped and not re.match(r'^\s*loading\s*$', line_stripped, re.IGNORECASE):
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Loại bỏ các ký tự control characters không cần thiết (giữ lại \n, \t)
    # Loại bỏ các ký tự như \r, \b, và các ký tự control khác
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # Loại bỏ các khoảng trắng thừa ở đầu/cuối mỗi dòng
    lines = text.split('\n')
    cleaned_lines = [line.rstrip() for line in lines]
    text = '\n'.join(cleaned_lines)
    
    # Loại bỏ các dòng trống liên tiếp (chỉ giữ lại 1 dòng trống)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def exec_cmd(cmd: str, shell: str = "bash") -> str:
    """Execute shell command"""
    try:
        result = subprocess.run(cmd, shell=True, executable=shell, 
                              capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired: return "Timeout"
    except Exception as e: return f"Error: {e}"

def get_shell() -> Tuple[str, str]:
    """Get shell and OS info"""
    shell = os.environ.get("SHELL", "bash").split("/")[-1]
    os_name = "Windows" if sys.platform == "win32" else ("macOS" if sys.platform == "darwin" else "Linux")
    if sys.platform == "win32": shell = "powershell"
    return shell, os_name

def read_stdin() -> str:
    """Read piped input"""
    return sys.stdin.read() if not sys.stdin.isatty() else ""

def load_proxy() -> Optional[Dict]:
    """Load proxy config"""
    proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    if proxy: return {"http": proxy, "https": proxy}
    
    for path in ["./proxy.txt", os.path.expanduser("~/.config/tgpt/proxy.txt")]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    p = f.read().strip()
                    if p: return {"http": p, "https": p}
            except: pass
    return None

# ============================================================================
# FREE PROVIDERS (No API Key Required)
# ============================================================================

class Provider:
    """Base provider class"""
    def __init__(self): self.proxies = load_proxy()
    
    def request(self, url: str, headers: Dict, payload: Dict, stream: bool = True, timeout: int = 30):
        """Make HTTP request"""
        try:
            response = requests.post(url, headers=headers, json=payload, 
                                   proxies=self.proxies, timeout=timeout, stream=stream)
            # Update VQD for DuckDuckGo if present
            if "duckduckgo.com" in url:
                vqd = response.headers.get("x-vqd-4")
                if vqd and hasattr(self, 'vqd'):
                    self.vqd = vqd
            return response
        except requests.exceptions.Timeout:
            error("Request timeout - server không phản hồi")
            return None
        except requests.exceptions.ConnectionError:
            error("Connection error - không thể kết nối đến server")
            return None
        except Exception as e:
            error(f"Request failed: {e}")
            return None
    
    def stream(self, response, opts: Options) -> str:
        """Stream response"""
        text = ""
        if not response:
            return ""
            
        try:
            if response.status_code != 200:
                error_msg = response.text[:200] if hasattr(response, 'text') else "Unknown error"
                error(f"HTTP {response.status_code}: {error_msg}")
                return ""
            
            if opts.whole_text:
                # Get whole response at once
                text = response.text
                if not opts.quiet:
                    print(text)
                # Clean response trước khi trả về
                return clean_response(text)
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    chunk = self.parse(line)
                    if chunk:
                        text += chunk
                        if not opts.quiet: 
                            print(chunk, end="", flush=True)
            if not opts.quiet and text: 
                print()
        except requests.exceptions.ChunkedEncodingError:
            # Một số provider có thể gửi response không đúng format
            if text and not opts.quiet:
                print()
            # Clean response trước khi trả về
            return clean_response(text)
        except Exception as e:
            error(f"Stream error: {e}")
        # Clean response trước khi trả về để loại bỏ ký tự thừa
        return clean_response(text)
    
    def parse(self, line: str) -> str:
        """Parse response line - override in subclass"""
        return ""

class Phind(Provider):
    """Phind - Free, no limits"""
    def create(self, text: str, params: Params):
        # Build message history - Phind LUÔN thêm system prompt vào đầu (theo Go code)
        # Ngay cả khi system_prompt là empty string, vẫn cần thêm vào
        msgs = [{"role": "system", "content": params.system_prompt or ""}]
        
        # Thêm prev_messages nếu có
        if params.prev_messages:
            msgs.extend(params.prev_messages)
        
        # Cuối cùng thêm user input
        msgs.append({"role": "user", "content": text})
        
        payload = {
            "additional_extension_context": "",
            "allow_magic_buttons": True,
            "is_vscode_extension": True,
            "requested_model": params.model or "Phind-70B",
            "user_input": text,
            "message_history": msgs
        }
        
        return self.request(
            "https://https.extension.phind.com/agent/",
            {
                "Content-Type": "application/json",
                "User-Agent": "",
                "Accept": "*/*",
                "Accept-Encoding": "Identity"
            },
            payload
        )
    
    def parse(self, line: str) -> str:
        # Parse theo format của Go code: tìm "data: " và parse JSON
        if not line or len(line) <= 1:
            return ""
        
        # Tìm "data: " trong line
        if "data: " in line:
            try:
                parts = line.split("data: ", 1)
                if len(parts) > 1:
                    obj_str = parts[1].strip()
                    # Bỏ qua nếu là [DONE]
                    if obj_str == "[DONE]":
                        return ""
                    data = json.loads(obj_str)
                    # Parse theo CommonResponse structure
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        return content if content else ""
            except (json.JSONDecodeError, ValueError, KeyError, IndexError):
                pass
        return ""

class DuckDuckGo(Provider):
    """DuckDuckGo AI - Free, privacy-focused"""
    def __init__(self):
        super().__init__()
        self.vqd = ""
        self.status_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
            "Accept": "text/event-stream",
            "Accept-Language": "en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://duckduckgo.com/",
            "Origin": "https://duckduckgo.com",
            "Connection": "keep-alive",
            "Cookie": "dcm=1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-store",
            "x-vqd-accept": "1"
        }
        self._get_vqd()
    
    def _get_vqd(self) -> str:
        """Get VQD token"""
        try:
            r = requests.get("https://duckduckgo.com/duckchat/v1/status", 
                           headers=self.status_headers, proxies=self.proxies, timeout=10)
            self.vqd = r.headers.get("x-vqd-4", "")
            return self.vqd
        except Exception as e:
            error(f"DuckDuckGo VQD error: {e}")
            return ""
    
    def create(self, text: str, params: Params):
        if not self.vqd:
            self._get_vqd()
        
        # Build messages with system prompt if available
        msgs = []
        if params.system_prompt:
            msgs.append({"role": "system", "content": params.system_prompt})
        msgs.extend(params.prev_messages)
        msgs.append({"role": "user", "content": text})
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
            "Accept": "text/event-stream",
            "Accept-Language": "en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Referer": "https://duckduckgo.com/",
            "Origin": "https://duckduckgo.com",
            "Connection": "keep-alive",
            "Cookie": "dcm=1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "x-vqd-4": self.vqd,
            "x-vqd-hash-1": "abcdefg"
        }
        
        payload = {
            "model": params.model or "o3-mini",
            "messages": msgs
        }
        
        resp = self.request(
            "https://duckduckgo.com/duckchat/v1/chat",
            headers,
            payload
        )
        
        # Update VQD from response
        if resp:
            new_vqd = resp.headers.get("x-vqd-4")
            if new_vqd:
                self.vqd = new_vqd
        
        return resp
    
    def parse(self, line: str) -> str:
        if line.startswith("data: "):
            try:
                json_str = line[6:]
                if json_str.startswith("{"):
                    data = json.loads(json_str)
                    message = data.get("message", "")
                    if isinstance(message, str):
                        return message.replace("\\n", "\n")
            except: pass
        return ""

class Pollinations(Provider):
    """Pollinations - Free text & image (có thể không ổn định)"""
    def create(self, text: str, params: Params):
        # Build messages với system prompt
        msgs = []
        if params.system_prompt:
            msgs.append({"role": "system", "content": params.system_prompt})
        msgs.extend(params.prev_messages)
        msgs.append({"role": "user", "content": text})
        
        payload = {
            "model": params.model or "openai",
            "referrer": "tgpt",
            "stream": True,
            "messages": msgs,
            "temperature": str(params.temperature) if params.temperature else "1",
            "top_p": str(params.top_p) if params.top_p else "1"
        }
        
        # Try with shorter timeout
        resp = self.request(
            "https://text.pollinations.ai/openai",
            {"Content-Type": "application/json"},
            payload,
            timeout=20
        )
        
        return resp
    
    def parse(self, line: str) -> str:
        if line.startswith("data: "):
            json_str = line[6:]
            if json_str == "[DONE]":
                return ""
            try:
                data = json.loads(json_str)
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("delta", {}).get("content", "") or ""
            except: pass
        return ""
    
    def image(self, prompt: str, width: int = 1024, height: int = 1024, out: str = "", 
              negative: str = "", count: int = 1, ratio: str = "1:1") -> str:
        """Generate image"""
        import urllib.parse
        
        # Parse ratio (e.g., "16:9" -> calculate width/height)
        if ":" in ratio:
            try:
                w_ratio, h_ratio = map(int, ratio.split(":"))
                if h_ratio > 0:
                    height = int(width * h_ratio / w_ratio)
            except:
                pass
        
        # Build URL with parameters
        params = {"width": width, "height": height}
        if negative:
            params["negative"] = negative
        
        query_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?{query_str}"
        
        info(f"Image URL: {url}")
        
        if out:
            try:
                r = requests.get(url, proxies=self.proxies, timeout=60)
                r.raise_for_status()
                with open(out, "wb") as f: 
                    f.write(r.content)
                success(f"Saved: {out}")
            except Exception as e:
                error(f"Save failed: {e}")
        return url

class Ollama(Provider):
    """Ollama - Local/Self-hosted (Free)"""
    def create(self, text: str, params: Params):
        # Build messages với system prompt
        msgs = []
        if params.system_prompt:
            msgs.append({"role": "system", "content": params.system_prompt})
        msgs.extend(params.prev_messages)
        msgs.append({"role": "user", "content": text})
        
        url = params.url or "http://localhost:11434/v1/chat/completions"
        return self.request(
            url,
            {"Content-Type": "application/json"},
            {"model": params.model or "mistral", "messages": msgs, "stream": True}
        )
    
    def parse(self, line: str) -> str:
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                return data.get("choices", [{}])[0].get("delta", {}).get("content", "")
            except: pass
        return ""

class Isou(Provider):
    """Isou - Free AI với search capabilities"""
    def create(self, text: str, params: Params):
        import urllib.parse
        
        model = params.model or "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        
        payload = {
            "stream": True,
            "model": model,
            "provider": "siliconflow",
            "mode": "deep",
            "language": "all",
            "categories": ["science"],
            "engine": "SEARXNG",
            "locally": False,
            "reload": False
        }
        
        query = urllib.parse.quote(text)
        url = f"https://isou.chat/api/search?q={query}"
        
        return self.request(
            url,
            {
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://isou.chat/search",
                "Origin": "https://isou.chat",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"
            },
            payload
        )
    
    def parse(self, line: str) -> str:
        if "data:" in line:
            try:
                parts = line.split("data:", 1)
                if len(parts) > 1:
                    obj = json.loads(parts[1])
                    data_str = obj.get("data", "")
                    if data_str:
                        inner = json.loads(data_str)
                        # Ưu tiên content, sau đó reasoningContent, cuối cùng context
                        if inner.get("content"):
                            return inner["content"]
                        if inner.get("reasoningContent"):
                            return inner["reasoningContent"]
                        if inner.get("context"):
                            ctx = inner["context"]
                            return f"{ctx.get('id', '')}. Name: {ctx.get('name', '')}, Source: {ctx.get('url', '')}\n"
            except: pass
        return ""

class KoboldAI(Provider):
    """KoboldAI - Free hosted model trên HuggingFace"""
    def create(self, text: str, params: Params):
        payload = {
            "prompt": text,
            "temperature": str(params.temperature) if params.temperature else "0.5",
            "top_p": str(params.top_p) if params.top_p else "0.5",
            "max_length": "300"
        }
        
        return self.request(
            "https://koboldai-koboldcpp-tiefighter.hf.space/api/extra/generate/stream",
            {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            payload
        )
    
    def parse(self, line: str) -> str:
        if "data:" in line:
            try:
                parts = line.split("data: ", 1)
                if len(parts) > 1:
                    data = json.loads(parts[1])
                    return data.get("token", "")
            except: pass
        return ""

class Sky(Provider):
    """Sky - Free AI provider"""
    def create(self, text: str, params: Params):
        # Build messages - Sky chỉ thêm system prompt nếu có giá trị (theo Go code)
        msgs = []
        if params.system_prompt and len(params.system_prompt) > 0:
            msgs.append({"role": "system", "content": params.system_prompt})
        
        # Thêm prev_messages nếu có
        if params.prev_messages:
            msgs.extend(params.prev_messages)
        
        # Cuối cùng thêm user input
        msgs.append({"role": "user", "content": text})
        
        return self.request(
            "https://api.sky.foresko.com/v1/create-chat-completion",
            {
                "Content-Type": "application/json",
                "accept-charset": "UTF-8",
                "accept-encoding": "gzip",
                "connection": "Keep-Alive",
                "user-agent": "ktor-client"
            },
            {"messages": msgs}
        )
    
    def parse(self, line: str) -> str:
        # Parse theo format của Go code: tìm "data: " và parse JSON
        if not line or len(line) <= 1:
            return ""
        
        # Tìm "data: " trong line
        if "data: " in line:
            try:
                parts = line.split("data: ", 1)
                if len(parts) > 1:
                    obj_str = parts[1].strip()
                    # Bỏ qua nếu là [DONE]
                    if obj_str == "[DONE]":
                        return ""
                    data = json.loads(obj_str)
                    # Parse theo CommonResponse structure
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        return content if content else ""
            except (json.JSONDecodeError, ValueError, KeyError, IndexError):
                pass
        return ""

# Provider registry - Chỉ giữ lại các provider đã test và hoạt động tốt
PROVIDERS = {
    "phind": Phind,           # ✅ Hoạt động tốt - Default
    "sky": Sky,               # ✅ Hoạt động tốt
    "koboldai": KoboldAI,     # ✅ Hoạt động (chậm hơn)
    "kobold": KoboldAI,       # Alias của koboldai
    # Các provider không hoạt động đã được loại bỏ:
    # "duckduckgo": DuckDuckGo,  # ❌ Không hoạt động
    # "ddg": DuckDuckGo,         # ❌ Không hoạt động
    # "pollinations": Pollinations,  # ❌ Không hoạt động
    # "pol": Pollinations,       # ❌ Không hoạt động
    # "ollama": Ollama,          # ❌ Cần cài đặt local
    # "isou": Isou,              # ❌ Không hoạt động
}

# ============================================================================
# CORE ENGINE
# ============================================================================

class TGPT:
    """Main TGPT engine"""
    
    def __init__(self):
        self.history = []
    
    def get_provider(self, name: str) -> Provider:
        """Get provider instance"""
        return PROVIDERS.get(name.lower(), Phind)()
    
    def chat(self, text: str, params: Params, opts: Options) -> Tuple[str, List[Dict]]:
        """Get AI response"""
        provider = self.get_provider(params.provider)
        
        # Add system prompt if provided
        if params.system_prompt:
            system_msg = {"role": "system", "content": params.system_prompt}
            if not params.prev_messages or params.prev_messages[0].get("role") != "system":
                params.prev_messages.insert(0, system_msg)
        
        response = provider.create(text, params)
        
        if not response:
            return "", []
        
        # Stream response
        full_text = provider.stream(response, opts)
        
        if not full_text:
            return "", []
        
        # Clean response để loại bỏ ký tự thừa (double-check)
        full_text = clean_response(full_text)
        
        # Build conversation objects
        objs = [
            {"role": "user", "content": text},
            {"role": "assistant", "content": full_text}
        ]
        
        return full_text, objs
    
    def interactive(self, params: Params, opts: Options, initial: str = ""):
        """Interactive chat mode"""
        print(f"{C.BOLD}Interactive mode. Type 'exit' to quit.{C.W}\n")
        params.thread_id = str(uuid.uuid4())
        
        def handle(inp: str):
            if inp.strip().lower() == "exit":
                print(f"{C.BOLD}Bye!{C.W}")
                sys.exit(0)
            if not inp.strip(): return
            
            log(inp, "USER", opts.log_file)
            
            # Preprompt only on first message
            if not params.prev_messages and params.preprompt:
                inp = params.preprompt + inp
            
            text, objs = self.chat(inp, params, opts)
            params.prev_messages.extend(objs)
            self.history.append(inp)
            log(text, "ASSISTANT", opts.log_file)
        
        if initial:
            print(f"{C.C}You:{C.W} {initial}")
            handle(initial)
        
        while True:
            try:
                inp = input(f"\n{C.C}You:{C.W} ")
                handle(inp)
            except (KeyboardInterrupt, EOFError):
                print(f"\n{C.BOLD}Bye!{C.W}")
                break
    
    def shell_mode(self, params: Params, opts: Options, initial: str = "", aliases: bool = False):
        """Interactive shell assistant"""
        print(f"{C.BOLD}Shell mode. Type 'exit' to quit.{C.W}\n")
        
        shell, os_name = get_shell()
        params.thread_id = str(uuid.uuid4())
        params.system_prompt = (
            f"You are a {shell} terminal assistant on {os_name}. "
            f"Generate commands wrapped in <cmd>command</cmd> tags. "
            f"Only output commands when user needs shell execution. "
            f"Example: User: 'list files' → <cmd>ls -la</cmd>"
        )
        if aliases:
            params.system_prompt += " Support shell aliases and functions."
        
        def handle(inp: str):
            if inp.strip().lower() == "exit":
                print(f"{C.BOLD}Bye!{C.W}")
                sys.exit(0)
            if not inp.strip(): return
            
            log(inp, "USER", opts.log_file)
            
            if not params.prev_messages and params.preprompt:
                inp = params.preprompt + inp
            
            text, objs = self.chat(inp, params, opts)
            
            # Extract command
            match = re.search(r'<cmd>(.*?)</cmd>', text, re.DOTALL)
            if match:
                cmd = match.group(1).strip()
                
                if not opts.auto_exec:
                    confirm = input(f"\n{C.Y}Run: {cmd} ? [y/n]:{C.W} ")
                    if confirm.lower() not in ['y', '']: 
                        params.prev_messages.extend(objs)
                        return
                
                print()
                output = exec_cmd(cmd, shell)
                if output: print(output)
                
                # Add to context
                objs.append({"role": "user", "content": f"Executed: {cmd}"})
                if output: objs.append({"role": "assistant", "content": f"Output:\n{output}"})
            
            params.prev_messages.extend(objs)
            log(text, "ASSISTANT", opts.log_file)
        
        if initial:
            print(f"{C.C}You:{C.W} {initial}")
            handle(initial)
        
        while True:
            try:
                inp = input(f"\n{C.C}You:{C.W} ")
                handle(inp)
            except (KeyboardInterrupt, EOFError):
                print(f"\n{C.BOLD}Bye!{C.W}")
                break
    
    def code(self, prompt: str, params: Params, opts: Options) -> str:
        """Generate code"""
        enhanced = f"Write code for: {prompt}\nProvide only the code without explanation."
        text, _ = self.chat(enhanced, params, opts)
        # Clean response để loại bỏ ký tự thừa
        return clean_response(text)
    
    def shell_cmd(self, prompt: str, params: Params, opts: Options) -> str:
        """Generate shell command"""
        shell, os_name = get_shell()
        enhanced = f"Generate {shell} command for {os_name}: {prompt}\nOnly the command, no explanation."
        text, _ = self.chat(enhanced, params, opts)
        
        # Clean response để loại bỏ ký tự thừa trước
        text = clean_response(text)
        
        # Clean markdown code blocks
        text = re.sub(r'^```[\w]*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```$', '', text)
        # Remove markdown inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text.strip()
    
    def image(self, prompt: str, width: int, height: int, out: str, params: Params, 
              negative: str = "", count: int = 1, ratio: str = "1:1"):
        """Generate image - Không được hỗ trợ với các provider free hiện tại"""
        error("Image generation không được hỗ trợ với các provider free hiện tại")
        error("Các provider hỗ trợ image (pollinations) hiện không hoạt động")
    
    def _is_lofi_style(self, idea: str, style: str = "") -> bool:
        """
        Kiểm tra xem idea/style có thuộc lofi/chill hay không.
        
        Args:
            idea: Ý tưởng gốc
            style: Style được chỉ định
            
        Returns:
            True nếu là lofi/chill style
        """
        combined = f"{idea} {style}".lower()
        return any(kw in combined for kw in LOFI_STYLE_KEYWORDS)
    
    def image_prompt(self, idea: str, style: str = "", mood: str = "", lighting: str = "") -> str:
        """
        Tạo prompt hình ảnh chi tiết từ ý tưởng đơn giản.
        Tự động detect lofi/chill style và sử dụng frame-context tối ưu.
        
        Args:
            idea: Ý tưởng gốc (tiếng Việt hoặc English)
            style: Style mong muốn (optional) - "lofi", "chill", etc. sẽ trigger lofi frame-context
            mood: Mood/atmosphere (optional)
            lighting: Lighting (optional)
            
        Returns:
            Prompt tiếng Anh chi tiết (100-200 words cho lofi, 200-400 chars cho generic)
        """
        # Detect lofi/chill style
        is_lofi = self._is_lofi_style(idea, style)
        
        # Chọn system prompt phù hợp
        if is_lofi:
            # Đọc từ YAML file (có cache)
            system_prompt = get_lofi_system_prompt()
            # Không cần thêm context cho lofi vì đã có trong system prompt
            user_input = idea
        else:
            system_prompt = IMAGE_PROMPT_SYSTEM
            # Build context cho generic style
            ctx = []
            if style: ctx.append(style)
            if mood: ctx.append(mood)
            if lighting: ctx.append(lighting)
            user_input = f"{idea} ({', '.join(ctx)})" if ctx else idea
        
        params = Params(
            provider="phind",
            system_prompt=system_prompt
        )
        opts = Options(quiet=True)
        
        text, _ = self.chat(user_input, params, opts)
        return clean_response(text)
    
    def image_prompt_lofi(self, idea: str, mood: str = "", lighting: str = "") -> str:
        """
        Tạo prompt hình ảnh lofi/chill 2.5D chi tiết.
        Sử dụng frame-context từ lofi_frame_context.yaml.
        
        Args:
            idea: Ý tưởng gốc (tiếng Việt hoặc English)
            mood: Mood bổ sung (optional): "cozy", "peaceful", "warm"
            lighting: Lighting bổ sung (optional): "golden sunlight", "campfire", "twilight"
            
        Returns:
            Prompt tiếng Anh chi tiết 2.5D lofi style (100-200 words)
            
        Example:
            >>> tgpt.image_prompt_lofi("Pusheen ngồi đọc sách picnic mùa thu, núi xa")
            # Returns detailed 2.5D layered lofi prompt
        """
        # Thêm context nếu có
        ctx = []
        if mood: ctx.append(f"mood: {mood}")
        if lighting: ctx.append(f"lighting: {lighting}")
        
        user_input = f"{idea} ({', '.join(ctx)})" if ctx else idea
        
        # Đọc system prompt từ YAML file (có cache)
        lofi_prompt = get_lofi_system_prompt()
        
        params = Params(
            provider="phind",
            system_prompt=lofi_prompt
        )
        opts = Options(quiet=True)
        
        text, _ = self.chat(user_input, params, opts)
        return clean_response(text)
    
    def get_lofi_props(self, category: str = "") -> dict:
        """
        Lấy reference props từ lofi_frame_context.yaml.
        
        Args:
            category: Category cụ thể ("reading", "comfort", "seasonal") hoặc empty để lấy tất cả
            
        Returns:
            dict: Props reference data
        """
        ref = get_lofi_reference()
        props = ref.get("props", {})
        if category and category in props:
            return {category: props[category]}
        return props
    
    def get_lofi_lighting(self, time_of_day: str = "") -> dict:
        """
        Lấy lighting reference từ lofi_frame_context.yaml.
        
        Args:
            time_of_day: Thời điểm ("morning", "afternoon", "evening", "night_indoor", "night_outdoor")
            
        Returns:
            dict hoặc str: Lighting reference data
        """
        ref = get_lofi_reference()
        lighting = ref.get("lighting", {})
        if time_of_day and time_of_day in lighting:
            return {time_of_day: lighting[time_of_day]}
        return lighting
    
    def enhance_text(self, text: str, system: str = "") -> str:
        """
        Enhance/improve text với AI.
        
        Args:
            text: Text cần enhance
            system: Custom system prompt (optional)
            
        Returns:
            Text đã được enhance
        """
        params = Params(
            provider="phind",
            system_prompt=system or TEXT_ENHANCE_SYSTEM
        )
        opts = Options(quiet=True)
        
        result, _ = self.chat(text, params, opts)
        return clean_response(result)
    
    def translate(self, text: str, target_lang: str = "English") -> str:
        """
        Dịch text sang ngôn ngữ khác.
        
        Args:
            text: Text cần dịch
            target_lang: Ngôn ngữ đích (default: English)
            
        Returns:
            Text đã dịch
        """
        params = Params(
            provider="phind",
            system_prompt=TRANSLATE_SYSTEM
        )
        opts = Options(quiet=True)
        
        prompt = f"Translate to {target_lang}: {text}"
        result, _ = self.chat(prompt, params, opts)
        return clean_response(result)
    
    def whole_text(self, prompt: str, params: Params, opts: Options) -> str:
        """Get whole text response without streaming"""
        old_quiet = opts.quiet
        opts.quiet = True
        text, _ = self.chat(prompt, params, opts)
        opts.quiet = old_quiet
        # Clean response để loại bỏ ký tự thừa
        return clean_response(text)
    
# ============================================================================
# CLI
# ============================================================================

def setup_args():
    """Setup argument parser"""
    p = argparse.ArgumentParser(
        description="tgpt-mini: Free AI Chatbots in terminal",
        epilog="""
Examples:
  %(prog)s "What is Python?"                  # Simple query (Phind - default)
  %(prog)s -i                                  # Interactive mode
  %(prog)s -m                                  # Multiline interactive mode
  %(prog)s -s "list large files"              # Shell command
  %(prog)s -c "binary search in Python"       # Code generation
  %(prog)s --whole "long explanation"          # Whole text response
  %(prog)s --provider sky -i                  # Sky interactive
  %(prog)s --provider koboldai "Hello"        # KoboldAI
  cat file.txt | %(prog)s "summarize"         # Piped input

Free Providers (No API Key Required) - Đã test và hoạt động:
  phind        - Fast, no limits (default) ✅
  sky          - Free AI provider ✅
  koboldai    - Free hosted model (kobold) ✅
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Main
    p.add_argument("prompt", nargs="?", help="Input prompt")
    p.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    p.add_argument("-m", "--multiline", action="store_true", help="Multiline interactive mode")
    p.add_argument("-is", "--interactive-shell", action="store_true", help="Interactive shell mode")
    p.add_argument("-ia", "--interactive-alias", action="store_true", help="Interactive shell with aliases")
    p.add_argument("-s", "--shell", action="store_true", help="Generate shell command")
    p.add_argument("-c", "--code", action="store_true", help="Generate code")
    p.add_argument("--img", "--image", action="store_true", help="Generate image")
    p.add_argument("--whole", action="store_true", help="Get whole text response")
    
    # Provider
    p.add_argument("-p", "--provider", default="", help="Provider: phind|sky|koboldai (default: phind)")
    p.add_argument("--model", default="", help="Model name")
    p.add_argument("-u", "--url", default="", help="Custom API URL")
    p.add_argument("-t", "--temperature", type=float, default=0.7, help="Temperature (0.0-2.0)")
    p.add_argument("--top-p", type=float, default=1.0, help="Top-p sampling (0.0-1.0)")
    p.add_argument("--preprompt", default="", help="System preprompt")
    
    # Image
    p.add_argument("--width", type=int, default=1024, help="Image width")
    p.add_argument("--height", type=int, default=1024, help="Image height")
    p.add_argument("--img-negative", default="", help="Negative prompt for image")
    p.add_argument("--img-count", type=int, default=1, help="Number of images to generate")
    p.add_argument("--img-ratio", default="1:1", help="Image aspect ratio (e.g., 16:9)")
    p.add_argument("-o", "--out", default="", help="Output file path")
    
    # Options
    p.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (no streaming)")
    p.add_argument("-y", "--yes", action="store_true", help="Auto-execute commands")
    p.add_argument("-l", "--log", default="", help="Log file path")
    p.add_argument("--vb", "--verbose", action="store_true", dest="verbose", help="Verbose output")
    
    # Info
    p.add_argument("-v", "--version", action="version", version=f"%(prog)s {VERSION}")
    
    return p.parse_args()

def main():
    """Main entry"""
    signal.signal(signal.SIGINT, lambda s, f: (print(f"\n{C.BOLD}Interrupted{C.W}"), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    
    args = setup_args()
    piped = read_stdin()
    
    # Setup params
    provider = args.provider or os.environ.get("AI_PROVIDER", "phind")
    if args.img:
        # Image generation không được hỗ trợ với các provider hiện tại
        error("Image generation không được hỗ trợ với các provider free hiện tại")
        sys.exit(1)
    
    params = Params(
        provider=provider,
        model=args.model,
        url=args.url,
        temperature=args.temperature,
        top_p=getattr(args, 'top_p', 1.0),
        preprompt=args.preprompt
    )
    
    opts = Options(
        quiet=args.quiet,
        auto_exec=args.yes,
        log_file=args.log,
        verbose=getattr(args, 'verbose', False),
        whole_text=getattr(args, 'whole', False)
    )
    
    # Get prompt
    prompt = args.prompt or ""
    if piped and prompt:
        prompt = f"{prompt}\n\nContext:\n{piped}"
    elif piped:
        prompt = piped
    
    # Execute
    tgpt = TGPT()
    
    try:
        if args.interactive:
            tgpt.interactive(params, opts, prompt)
        
        elif args.interactive_shell:
            tgpt.shell_mode(params, opts, prompt, False)
        
        elif args.interactive_alias:
            tgpt.shell_mode(params, opts, prompt, True)
        
        elif args.img:
            if not prompt:
                error("Image prompt required")
                sys.exit(1)
            tgpt.image(prompt, args.width, args.height, args.out, params,
                      getattr(args, 'img_negative', ''), 
                      getattr(args, 'img_count', 1),
                      getattr(args, 'img_ratio', '1:1'))
        
        elif args.shell:
            if not prompt:
                error("Prompt required")
                sys.exit(1)
            cmd = tgpt.shell_cmd(prompt, params, opts)
            print(f"\n{C.C}{cmd}{C.W}")
            
            if args.yes:
                print()
                output = exec_cmd(cmd)
                if output: print(output)
            else:
                confirm = input(f"\n{C.Y}Execute? [y/n]:{C.W} ")
                if confirm.lower() == 'y':
                    print()
                    output = exec_cmd(cmd)
                    if output: print(output)
        
        elif args.code:
            if not prompt:
                error("Prompt required")
                sys.exit(1)
            code = tgpt.code(prompt, params, opts)
            if not args.quiet: print()
            print(code)
        
        elif args.multiline:
            print(f"{C.BOLD}Multiline mode. Press Ctrl+D to submit, Ctrl+C to exit.{C.W}\n")
            params.thread_id = str(uuid.uuid4())
            
            def read_multiline() -> str:
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass
                return "\n".join(lines)
            
            if prompt:
                print(f"{C.C}You:{C.W} {prompt}")
                text, objs = tgpt.chat(prompt, params, opts)
                params.prev_messages.extend(objs)
            
            while True:
                try:
                    print(f"\n{C.C}You (Ctrl+D to submit):{C.W}")
                    inp = read_multiline()
                    if inp.strip().lower() == "exit":
                        print(f"{C.BOLD}Bye!{C.W}")
                        break
                    if not inp.strip(): continue
                    
                    log(inp, "USER", opts.log_file)
                    text, objs = tgpt.chat(inp, params, opts)
                    params.prev_messages.extend(objs)
                    log(text, "ASSISTANT", opts.log_file)
                except (KeyboardInterrupt, EOFError):
                    print(f"\n{C.BOLD}Bye!{C.W}")
                    break
        
        elif args.whole:
            if not prompt:
                error("Prompt required")
                sys.exit(1)
            text = tgpt.whole_text(prompt, params, opts)
            print(text)
        
        elif prompt:
            if params.preprompt:
                prompt = params.preprompt + prompt
            
            text, _ = tgpt.chat(prompt, params, opts)
            
            if args.log:
                log(prompt, "USER", args.log)
                log(text, "ASSISTANT", args.log)
        
        else:
            error("No prompt. Use -h for help")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print(f"\n{C.BOLD}Interrupted{C.W}")
    except Exception as e:
        error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
