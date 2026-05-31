import os
import time
import requests

_CLOUD_URL = 'https://api.ollama.com'

# Keys tried in order; first healthy one wins
_API_KEYS = [
    'fcdb4338f8a04a568fb439d4c678cc0e.BCeAlsstWb0wiLUTEtk6KdJP',  # new account – default
    '16b49325e25648409d92bd99b3a8aec8.DFI16wlQ_sq7uuDPI9YYVjuW',  # r.chand9972
    '36775c93f411447c8102e4b0acb2c2f5.JXjgA9XHo_LHH_EBSXInZlho',  # r.bethireddy
]


class OllamaRateLimitError(Exception):
    pass


def _post(api_key, payload):
    return requests.post(
        f"{_CLOUD_URL}/api/chat",
        json=payload,
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=60,
    )


def ollama_chat(prompt, model='gpt-oss:120b-cloud', system=None):
    env_key = os.getenv('OLLAMA_API_KEY')
    keys = ([env_key] if env_key else []) + _API_KEYS
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    payload = {
        'model': model,
        'messages': messages,
        'stream': False,
    }

    last_exc = None
    for api_key in keys:
        for attempt in range(3):
            resp = _post(api_key, payload)
            if resp.status_code == 429:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                last_exc = OllamaRateLimitError('rate_limit')
                break
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                last_exc = e
                break
            return resp.json().get('message', {}).get('content', '')

    raise OllamaRateLimitError(
        'All API keys are currently exhausted. Please try again later.'
    )
