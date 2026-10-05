import os

import httpx
import streamlit as st


def api(method, path, **kwargs):
    base_url = os.getenv("BANKING_API_URL", "http://localhost:8000").rstrip("/")
    try:
        response = httpx.request(method, base_url + path, timeout=60, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", "Request failed")
        except ValueError:
            detail = "Request failed"
        st.error(str(detail))
    except httpx.RequestError:
        st.error(
            "Banking API unavailable. Start `PYTHONPATH=src:. uvicorn app.main:app --reload` and run migrations."
        )
    return None
