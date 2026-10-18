"""
Local LLM client for MARK XL.

Supports two backends — selected via  "llm_provider"  in config/api_keys.json:

  "llm_provider": "ollama"   (default)
        Uses Ollama's native /api/chat endpoint.
        Download: https://ollama.com
        Default port: 11434

  "llm_provider": "openai"
        Uses any OpenAI-compatible server: LM Studio, Jan, LocalAI,
        llama.cpp server, vLLM, etc.
        LM Studio download: https://lmstudio.ai   (default port: 1234)
        Set  "llm_url": "http://localhost:1234"  in config.
        Note: tool-calling support depends on the model; use a model that
        supports function/tool calls (e.g. Qwen2.5, Llama-3.1, Mistral).
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Generator

import requests

# Matches a sentence boundary: [.!?] followed by whitespace, or a blank line.
# Avoids splitting on decimals (3.5) because those have no space after the dot.
_SENT_END = re.compile(r'(?<=[.!?])\s+|(?<=\n)\s*\n')

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR    = get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

_DEFAULTS = {
    "llm_url":      "http://localhost:11434",
    "llm_model":    "llama3.2",
    "llm_provider": "ollama",   # "ollama" | "openai"
}


def get_llm_provider() -> str:
    """Returns 'ollama' or 'openai' (covers LM Studio, LocalAI, Jan, etc.)."""
    raw = _load_config().get("llm_provider", "ollama").strip().lower()
    return "openai" if raw in ("openai", "lmstudio", "localai", "jan", "llamacpp") else "ollama"


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ensure_ollama_running(timeout: int = 15) -> bool:
    """
    For Ollama: ping /api/tags; auto-launch 'ollama serve' if not running.
    For OpenAI-compatible providers: just ping /v1/models (server must be started manually).
    Returns True if the LLM server is reachable.
    """
    url, _   = get_llm_settings()
    provider = get_llm_provider()

    if provider == "openai":
        # OpenAI-compatible servers (LM Studio, LocalAI, etc.) must be started
        # by the user — we just check if they're reachable.
        health = f"{url}/v1/models"
        try:
            ok = requests.get(health, timeout=5).status_code == 200
            if ok:
                print(f"[LLM] OpenAI-compatible server reachable at {url}")
            else:
                print(f"[LLM] Server at {url} returned non-200.  Is it running?")
            return ok
        except Exception as e:
            print(
                f"[LLM] Cannot reach OpenAI-compatible server at {url}.\n"
                "      Make sure LM Studio / LocalAI / Jan is running and the server is started."
            )
            return False

    # ── Ollama ──────────────────────────────────────────────────────────────
    health = f"{url}/api/tags"

    def _is_up() -> bool:
        try:
            return requests.get(health, timeout=3).status_code == 200
        except Exception:
            return False

    if _is_up():
        return True

    print("[LLM] Ollama not running — launching 'ollama serve'…")
    try:
        kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(["ollama", "serve"], **kwargs)
    except FileNotFoundError:
        print("[LLM] 'ollama' command not found. Install Ollama from https://ollama.com")
        return False
    except Exception as e:
        print(f"[LLM] Could not launch Ollama: {e}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.0)
        if _is_up():
            print("[LLM] Ollama started successfully.")
            return True

    print("[LLM] Ollama did not respond within the timeout.")
    return False


def warmup_model(system_prompt: str | None = None) -> bool:
    """
    Pre-load the model AND prime Ollama's KV prefix cache.

    Why the system_prompt matters
    ─────────────────────────────
    Ollama caches the KV attention state of the prompt prefix across requests.
    If warmup includes the same system prompt that real requests will use, Ollama
    evaluates those tokens ONCE at startup.  Every subsequent request only needs
    to evaluate the small delta (user message ± time context) instead of the full
    300-500 token system prompt → drops first-token latency from ~17 s to <1 s.

    Pass the *static* part of the system prompt (the JARVIS protocol text, without
    timestamps or per-minute context) so the prefix stays valid across calls.
    """
    url, model = get_llm_settings()
    provider   = get_llm_provider()
    print(f"[LLM] Warming up '{model}' ({provider})…")

    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": "hi"})

    if provider == "openai":
        # OpenAI-compatible: just fire a minimal request to ensure the model is loaded.
        # No keep_alive or KV-cache priming available — server manages this internally.
        payload = {
            "model":      model,
            "messages":   messages,
            "stream":     False,
            "max_tokens": 1,
        }
        try:
            resp = requests.post(f"{url}/v1/chat/completions", json=payload, timeout=180)
            resp.raise_for_status()
            print(f"[LLM] '{model}' ready (OpenAI-compatible server).")
            return True
        except Exception as e:
            print(f"[LLM] Warmup failed (non-fatal): {e}")
            return False

    # ── Ollama ──────────────────────────────────────────────────────────────
    payload = {
        "model":      model,
        "messages":   messages,
        "stream":     False,
        "keep_alive": -1,
        # num_gpu:99 → push ALL transformer layers to GPU (Ollama caps at available)
        # This is safe even without a GPU — Ollama silently ignores if n_gpu_layers=0
        "options":    {"num_predict": 1, "num_gpu": 99},
    }
    try:
        resp = requests.post(f"{url}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        print(f"[LLM] '{model}' loaded and KV cache primed.")
        return True
    except Exception as e:
        print(f"[LLM] Warmup failed (non-fatal): {e}")
        return False


def check_model_available(log: Callable | None = None) -> bool:
    """
    Returns True if the configured model is already pulled in Ollama.
    Logs an actionable warning (to console + optional UI callback) if not.
    Always returns True for non-Ollama providers (cannot inspect their model list).
    """
    if get_llm_provider() != "ollama":
        return True

    url, model = get_llm_settings()
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        resp.raise_for_status()
        pulled = [m.get("name", "") for m in resp.json().get("models", [])]
        model_base = model.split(":")[0]
        found = any(
            m == model or m == model_base or m.startswith(model_base + ":")
            for m in pulled
        )
        if not found:
            available = ", ".join(pulled) if pulled else "none"
            warn = (
                f"WRN: Model '{model}' is not pulled in Ollama.\n"
                f"     Available: {available}\n"
                f"     Fix: ollama pull {model}"
            )
            print(warn)
            if log:
                log(f"WRN: '{model}' not found — run: ollama pull {model}")
        return found
    except Exception:
        return True   # Ollama might still be starting up; non-blocking


def get_llm_settings() -> tuple[str, str]:
    """Returns (base_url, model_name)."""
    cfg   = _load_config()
    url   = cfg.get("llm_url",   _DEFAULTS["llm_url"]).rstrip("/")
    model = cfg.get("llm_model", _DEFAULTS["llm_model"])
    return url, model


def call_llm(
    messages: list,
    tools:    list | None = None,
    timeout:  int = 120,
) -> dict:
    """
    Non-streaming chat request.  Routes to Ollama or OpenAI-compatible backend.

    Returns:
        {"content": str, "tool_calls": list}
    """
    url, model = get_llm_settings()
    provider   = get_llm_provider()

    if provider == "openai":
        endpoint = f"{url}/v1/chat/completions"
        payload: dict = {
            "model":      model,
            "messages":   messages,
            "stream":     False,
            "max_tokens": 150,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = "auto"
        try:
            resp = requests.post(endpoint, json=payload, timeout=timeout)
            resp.raise_for_status()
            choice = resp.json().get("choices", [{}])[0]
            msg    = choice.get("message", {})
            # OpenAI tool_calls format → normalise to Ollama-style
            raw_tc  = msg.get("tool_calls") or []
            tc_list = [
                {
                    "id":       t.get("id", ""),
                    "function": {
                        "name":      t["function"]["name"],
                        "arguments": (
                            json.loads(t["function"]["arguments"])
                            if isinstance(t["function"].get("arguments"), str)
                            else t["function"].get("arguments", {})
                        ),
                    },
                }
                for t in raw_tc
            ]
            return {
                "content":    (msg.get("content") or "").strip(),
                "tool_calls": tc_list,
            }
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible LLM call failed: {e}")

    # ── Ollama ──────────────────────────────────────────────────────────────
    endpoint = f"{url}/api/chat"
    payload = {
        "model":      model,
        "messages":   messages,
        "stream":     False,
        "keep_alive": -1,
        "options":    {"num_predict": 150, "num_gpu": 99},
    }
    if tools:
        payload["tools"] = tools

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        msg  = data.get("message", {})
        return {
            "content":    (msg.get("content") or "").strip(),
            "tool_calls": msg.get("tool_calls") or [],
        }
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] ConnectionError — trying to restart Ollama… ({e})")
        if ensure_ollama_running():
            try:
                resp = requests.post(endpoint, json=payload, timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                msg  = data.get("message", {})
                return {
                    "content":    (msg.get("content") or "").strip(),
                    "tool_calls": msg.get("tool_calls") or [],
                }
            except Exception:
                pass
        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out after 120 s.")
    except requests.exceptions.HTTPError as e:
        print(f"[LLM] HTTPError: {e.response.status_code} — {e.response.text[:200]}")
        raise RuntimeError(f"Ollama HTTP error: {e.response.status_code}")
    except Exception as e:
        print(f"[LLM] Unexpected error: {type(e).__name__}: {e}")
        raise RuntimeError(f"LLM call failed: {e}")


def call_llm_text(
    prompt:  str,
    system:  str | None = None,
    model:   str | None = None,
    timeout: int = 120,
) -> str:
    """
    Simple text-only generation (no tools).
    Used by planner, executor, error_handler, code_helper, dev_agent.
    """
    url, default_model = get_llm_settings()
    endpoint = f"{url}/api/chat"
    m        = model or default_model

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": m, "messages": messages, "stream": False, "keep_alive": -1, "options": {"num_predict": 600}}

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        resp.raise_for_status()
        return (resp.json().get("message", {}).get("content") or "").strip()
    except requests.exceptions.ConnectionError:
        if ensure_ollama_running():
            try:
                resp = requests.post(endpoint, json=payload, timeout=timeout)
                resp.raise_for_status()
                return (resp.json().get("message", {}).get("content") or "").strip()
            except Exception:
                pass
        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except Exception as e:
        raise RuntimeError(f"LLM text call failed: {e}")


def _stream_openai(
    messages: list,
    tools:    list | None,
    timeout:  int,
) -> Generator[dict, None, None]:
    """
    Streaming backend for OpenAI-compatible servers (LM Studio, LocalAI, Jan…).

    Parses Server-Sent Events (SSE) and accumulates streaming tool-call fragments
    so the output format is identical to the Ollama backend.
    """
    url, model = get_llm_settings()
    endpoint   = f"{url}/v1/chat/completions"

    payload: dict = {
        "model":      model,
        "messages":   messages,
        "stream":     True,
        "max_tokens": 150,
    }
    if tools:
        payload["tools"]       = tools
        payload["tool_choice"] = "auto"

    try:
        with requests.post(endpoint, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            full_content = ""
            buf          = ""
            # tool_call fragments: index → {"id", "function": {"name", "arguments"}}
            tc_fragments: dict[int, dict] = {}

            for raw in resp.iter_lines():
                if not raw:
                    continue
                # SSE lines look like: b"data: {...}" or b"data: [DONE]"
                line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                choice = chunk.get("choices", [{}])[0]
                delta  = choice.get("delta", {})
                text   = delta.get("content") or ""

                full_content += text
                buf          += text

                # Accumulate sentence boundaries for streaming TTS
                while True:
                    m = _SENT_END.search(buf)
                    if not m:
                        break
                    sentence = buf[: m.start() + 1].strip()
                    buf      = buf[m.end():]
                    if sentence:
                        yield {"type": "sentence", "text": sentence}

                # Accumulate streaming tool-call fragments
                for tc in (delta.get("tool_calls") or []):
                    idx = tc.get("index", 0)
                    if idx not in tc_fragments:
                        tc_fragments[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                    frag = tc_fragments[idx]
                    frag["id"] = frag["id"] or tc.get("id", "")
                    fn = tc.get("function", {})
                    frag["function"]["name"]      += fn.get("name") or ""
                    frag["function"]["arguments"] += fn.get("arguments") or ""

                finish = choice.get("finish_reason")
                if finish in ("stop", "tool_calls", "length"):
                    break

            # Flush any trailing content
            if buf.strip():
                yield {"type": "sentence", "text": buf.strip()}

            # Parse accumulated tool-call argument strings → dicts
            tool_calls: list = []
            for idx in sorted(tc_fragments):
                frag = tc_fragments[idx]
                args = frag["function"]["arguments"]
                try:
                    args = json.loads(args)
                except Exception:
                    pass   # leave as raw string; _execute_tool handles it
                tool_calls.append({
                    "id":       frag["id"],
                    "function": {"name": frag["function"]["name"], "arguments": args},
                })

            yield {
                "type":       "done",
                "content":    full_content.strip(),
                "tool_calls": tool_calls,
            }

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach OpenAI-compatible server at {url}.\n"
            "Make sure LM Studio / LocalAI / Jan is running and the server is started."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("OpenAI-compatible stream timed out.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"OpenAI-compatible HTTP error: {e.response.status_code}")
    except Exception as e:
        raise RuntimeError(f"OpenAI-compatible stream failed: {e}")


def call_llm_stream(
    messages: list,
    tools:    list | None = None,
    timeout:  int = 120,
) -> Generator[dict, None, None]:
    """
    Streaming chat request.  Routes to Ollama or OpenAI-compatible backend.

    Yields:
        {"type": "sentence", "text": str}   — each complete sentence as it arrives
        {"type": "done", "content": str, "tool_calls": list}  — when stream ends

    Sentences are split on [.!?] + whitespace so TTS can start immediately.
    Tool calls always appear in the final "done" event.
    """
    provider = get_llm_provider()
    if provider == "openai":
        yield from _stream_openai(messages, tools, timeout)
        return

    url, model = get_llm_settings()
    endpoint   = f"{url}/api/chat"

    payload: dict = {
        "model":      model,
        "messages":   messages,
        "stream":     True,
        "keep_alive": -1,
        # 150 tokens ≈ 100 words ≈ 3-4 sentences — enough for any voice reply.
        # num_gpu:99 pushes all layers to GPU; num_thread removed (Ollama auto-tunes).
        "options":    {"num_predict": 150, "num_gpu": 99},
    }
    if tools:
        payload["tools"] = tools

    def _do_stream() -> Generator[dict, None, None]:
        with requests.post(endpoint, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            full_content = ""
            tool_calls:  list = []
            buf          = ""

            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg   = chunk.get("message", {})
                delta = msg.get("content") or ""

                full_content += delta
                buf          += delta

                # Yield complete sentences as they accumulate
                while True:
                    m = _SENT_END.search(buf)
                    if not m:
                        break
                    sentence = buf[: m.start() + 1].strip()
                    buf      = buf[m.end() :]
                    if sentence:
                        yield {"type": "sentence", "text": sentence}

                tc = msg.get("tool_calls")
                if tc:
                    tool_calls.extend(tc)

                if chunk.get("done"):
                    if buf.strip():
                        yield {"type": "sentence", "text": buf.strip()}

                    yield {
                        "type":       "done",
                        "content":    full_content.strip(),
                        "tool_calls": tool_calls,
                    }
                    return

    try:
        yield from _do_stream()
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] Stream ConnectionError — trying to restart Ollama… ({e})")
        if ensure_ollama_running():
            yield from _do_stream()
            return
        raise RuntimeError(
            f"Cannot connect to Ollama at {url}. "
            "Make sure Ollama is installed and run: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama stream timed out.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e.response.status_code}")
    except Exception as e:
        print(f"[LLM] Stream error: {type(e).__name__}: {e}")
        raise RuntimeError(f"LLM stream failed: {e}")


# ── Unified Multi-Provider Dispatcher ───────────────────────────────────────

def _format_tools_for_openai(raw_tools: list) -> list:
    """Transform ActionRegistry declarations into OpenAI/Ollama function format."""
    def _lower_types(schema):
        if not isinstance(schema, dict):
            return schema
        s = dict(schema)
        if "type" in s and isinstance(s["type"], str):
            s["type"] = s["type"].lower()
        if "properties" in s and isinstance(s["properties"], dict):
            s["properties"] = {k: _lower_types(v) for k, v in s["properties"].items()}
        if "items" in s and isinstance(s["items"], dict):
            s["items"] = _lower_types(s["items"])
        return s

    formatted = []
    for t in raw_tools:
        if isinstance(t, dict):
            if "function" in t:
                f = dict(t["function"])
                if "parameters" in f:
                    f["parameters"] = _lower_types(f["parameters"])
                formatted.append({"type": "function", "function": f})
            else:
                params = t.get("parameters", {"type": "object", "properties": {}})
                formatted.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "parameters": _lower_types(params),
                    }
                })
    return formatted


def call_unified(
    prompt_or_messages,
    system: str | None = None,
    tools: list | None = None,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 60,
) -> dict:
    """
    Unified multi-provider client for Ultron.
    Supports:
      - 'gemini': Google GenAI API
      - 'ollama': Local or remote Ollama server
      - 'gpt': OpenAI API
      - 'nvidia_nim': NVIDIA NIM API
      - 'opencode_zen': OpenCode Zen API
      - 'claude': Anthropic API
      - 'deepseek': DeepSeek API
      - 'groq': Groq Cloud API
      - 'openrouter': OpenRouter / Custom OpenAI-compatible API

    Returns:
      {"content": str, "tool_calls": list}
    """
    from memory import config_manager

    p = (provider or config_manager.get_ai_provider() or "gemini").lower()
    m = model or config_manager.get_ai_model()
    key = config_manager.get_provider_key(p)
    base_url = config_manager.get_provider_url(p)

    # Standardize messages
    if isinstance(prompt_or_messages, str):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt_or_messages})
    else:
        messages = list(prompt_or_messages)
        if system and not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {"role": "system", "content": system})

    # 1. Gemini
    if p == "gemini":
        gemini_key = key or config_manager.get_gemini_key() or ""
        if not gemini_key:
            raise ValueError("No Gemini API key configured.")

        prompt_parts = []
        sys_msg = None
        for msg in messages:
            if msg.get("role") == "system":
                sys_msg = msg.get("content", "")
            elif msg.get("content"):
                prompt_parts.append(msg.get("content", ""))

        payload = {
            "contents": [{"parts": [{"text": "\n\n".join(prompt_parts)}]}]
        }
        if sys_msg:
            payload["systemInstruction"] = {"parts": [{"text": sys_msg}]}

        models_to_try = [m] if m else ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
        last_err = None
        for mod in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
            try:
                resp = requests.post(url, json=payload, timeout=min(timeout, 20))
                if resp.status_code == 200:
                    cand = resp.json().get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [{}])
                    text_out = "".join(p.get("text", "") for p in parts)
                    return {"content": text_out.strip(), "tool_calls": []}
                else:
                    last_err = resp.text
            except Exception as e:
                last_err = str(e)
                continue
        if last_err:
            print(f"[LLM] Gemini call failed: {last_err}")
            raise RuntimeError(f"Gemini API error: {last_err}")

    # 2. Claude (Anthropic)
    if p == "claude":
        try:
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            url = (base_url or "https://api.anthropic.com/v1").rstrip("/") + "/messages"
            sys_msg = next((msg["content"] for msg in messages if msg.get("role") == "system"), "")
            user_msgs = [msg for msg in messages if msg.get("role") != "system"]
            payload = {
                "model": m or "claude-3-7-sonnet-20250219",
                "max_tokens": 2048,
                "messages": user_msgs,
            }
            if sys_msg:
                payload["system"] = sys_msg
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            return {"content": text.strip(), "tool_calls": []}
        except Exception as e:
            print(f"[LLM] Claude call failed: {e}")
            raise

    # 3. Ollama (Native)
    if p == "ollama":
        url = base_url or "http://localhost:11434"
        endpoint = f"{url.rstrip('/')}/api/chat"
        payload = {
            "model": m or "gemma4:31b-cloud",
            "messages": messages,
            "stream": False,
            "keep_alive": -1,
        }
        if tools:
            payload["tools"] = _format_tools_for_openai(tools)
        try:
            resp = requests.post(endpoint, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            raw_tc = msg.get("tool_calls") or []
            tc_list = []
            for tc in raw_tc:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
                tc_list.append({
                    "id": tc.get("id", ""),
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": args,
                    }
                })
            return {
                "content": (msg.get("content") or "").strip(),
                "tool_calls": tc_list,
            }
        except Exception as e:
            print(f"[LLM] Ollama call failed: {e}")
            raise

    # 4. OpenAI & Compatible Providers (GPT, Nvidia NIM, OpenCode Zen, DeepSeek, Groq, OpenRouter)
    default_urls = {
        "gpt": "https://api.openai.com/v1",
        "nvidia_nim": "https://integrate.api.nvidia.com/v1",
        "opencode_zen": "https://api.opencode.zen/v1",
        "deepseek": "https://api.deepseek.com",
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
    }
    target_base = (base_url or default_urls.get(p, "https://api.openai.com/v1")).rstrip("/")
    if target_base.endswith("/chat/completions"):
        endpoint = target_base
    elif target_base.endswith("/v1"):
        endpoint = f"{target_base}/chat/completions"
    else:
        # Check if deepseek or others without /v1
        endpoint = f"{target_base}/v1/chat/completions" if p not in ("deepseek",) else f"{target_base}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if p == "openrouter":
        headers["HTTP-Referer"] = "https://ultron.ai"
        headers["X-Title"] = "Ultron AI"

    payload = {
        "model": m,
        "messages": messages,
        "temperature": 0.7,
    }
    if tools:
        payload["tools"] = _format_tools_for_openai(tools)
        payload["tool_choice"] = "auto"

    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        res_json = resp.json()
        choice = res_json.get("choices", [{}])[0]
        msg = choice.get("message", {})
        raw_tc = msg.get("tool_calls") or []
        tc_list = []
        for t in raw_tc:
            fn = t.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            tc_list.append({
                "id": t.get("id", ""),
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": args,
                }
            })
        return {
            "content": (msg.get("content") or "").strip(),
            "tool_calls": tc_list,
        }
    except Exception as e:
        print(f"[LLM] {p} call failed at {endpoint}: {e}")
        raise


def call_unified_text(
    prompt: str,
    system: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 60,
) -> str:
    """Returns just the text completion from the active (or specified) AI provider."""
    res = call_unified(prompt, system=system, provider=provider, model=model, timeout=timeout)
    return res.get("content", "").strip()
