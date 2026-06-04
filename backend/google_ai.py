# -*- coding: utf-8 -*-
"""
google_ai.py — Integração unificada Google AI para Aura Decore
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Clientes:
  • GeminiText   — texto/captions/roteiros (gemini-2.0-flash / 2.5-pro)  ✅ free tier
  • GeminiImage  — geração de imagem (imagen / gemini-2.5-flash-image)   ⚠️ requer billing
  • GeminiVeo    — geração de vídeo (veo-3)                              ⚠️ requer billing

Chave: GOOGLE_AI_KEY no .env (já configurada).
Para imagem/vídeo: ativar billing em https://aistudio.google.com/apikey
(cota free_tier = 0 para esses modelos premium).

CLI:
  python google_ai.py status
  python google_ai.py text   "escreva um slogan japandi"
  python google_ai.py image  "vaso ceramica minimalista" saida.png
  python google_ai.py video  "vela acesa, camera lenta" saida.mp4
"""
import os, sys, json, time, base64, pathlib
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ENV = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV, override=True)

GOOGLE_AI_KEY = os.getenv("GOOGLE_AI_KEY", "")
BASE = "https://generativelanguage.googleapis.com/v1beta"

# Modelos
MODEL_TEXT_FAST = "gemini-2.0-flash"
MODEL_TEXT_PRO  = "gemini-2.5-pro"
MODEL_IMAGE     = "gemini-2.5-flash-image"          # "nano banana"
MODEL_IMAGEN    = "imagen-4.0-fast-generate-001"    # Imagen 4 fast (paid, ~US$0.02)
MODEL_VEO       = "veo-3.0-fast-generate-001"       # Veo 3 fast (paid)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GeminiText:
    """Texto — funciona no free tier."""

    @staticmethod
    def generate(prompt: str, pro: bool = False, temperature: float = 0.8,
                 max_tokens: int = 1024) -> dict:
        model = MODEL_TEXT_PRO if pro else MODEL_TEXT_FAST
        try:
            r = httpx.post(
                f"{BASE}/models/{model}:generateContent?key={GOOGLE_AI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": temperature,
                                           "maxOutputTokens": max_tokens}},
                timeout=30
            )
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return {"ok": True, "text": text, "model": model}
            return {"ok": False, "error": f"{r.status_code}: {r.text[:200]}", "model": model}
        except Exception as e:
            return {"ok": False, "error": str(e), "model": model}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GeminiImage:
    """Imagem — requer billing ativado (free_tier = 0)."""

    @staticmethod
    def generate(prompt: str, out_path: str = "", aspect: str = "1:1") -> dict:
        # Tenta gemini-2.5-flash-image primeiro, depois Imagen 3
        for model in (MODEL_IMAGE, MODEL_IMAGEN):
            try:
                if model == MODEL_IMAGE:
                    body = {"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
                    r = httpx.post(f"{BASE}/models/{model}:generateContent?key={GOOGLE_AI_KEY}",
                                   json=body, timeout=60)
                    if r.status_code == 200:
                        parts = r.json()["candidates"][0]["content"]["parts"]
                        img = next((p for p in parts if "inlineData" in p), None)
                        if img:
                            data = base64.b64decode(img["inlineData"]["data"])
                            if out_path:
                                pathlib.Path(out_path).write_bytes(data)
                            return {"ok": True, "model": model, "path": out_path,
                                    "size_kb": len(data) // 1024}
                else:  # Imagen 3 predict endpoint
                    body = {"instances": [{"prompt": prompt}],
                            "parameters": {"sampleCount": 1, "aspectRatio": aspect}}
                    r = httpx.post(f"{BASE}/models/{model}:predict?key={GOOGLE_AI_KEY}",
                                   json=body, timeout=60)
                    if r.status_code == 200:
                        preds = r.json().get("predictions", [])
                        if preds and "bytesBase64Encoded" in preds[0]:
                            data = base64.b64decode(preds[0]["bytesBase64Encoded"])
                            if out_path:
                                pathlib.Path(out_path).write_bytes(data)
                            return {"ok": True, "model": model, "path": out_path,
                                    "size_kb": len(data) // 1024}

                # Erro — detecta billing
                if r.status_code == 429:
                    return {"ok": False, "model": model, "billing_required": True,
                            "error": "Cota free_tier=0. Ative billing: aistudio.google.com/apikey"}
            except Exception as e:
                last_err = str(e)
                continue
        return {"ok": False, "error": "Nenhum modelo de imagem disponível (billing necessário)",
                "billing_required": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class GeminiVeo:
    """Vídeo Veo 3 — operação long-running, requer billing."""

    @staticmethod
    def generate(prompt: str, out_path: str = "", image_path: str = "") -> dict:
        try:
            instance = {"prompt": prompt}
            if image_path and pathlib.Path(image_path).exists():
                img_b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode()
                instance["image"] = {"bytesBase64Encoded": img_b64, "mimeType": "image/png"}

            # Inicia operação long-running
            r = httpx.post(
                f"{BASE}/models/{MODEL_VEO}:predictLongRunning?key={GOOGLE_AI_KEY}",
                json={"instances": [instance],
                      "parameters": {"aspectRatio": "9:16", "durationSeconds": 8}},
                timeout=30
            )
            if r.status_code == 429:
                return {"ok": False, "billing_required": True,
                        "error": "Veo requer billing. Ative: aistudio.google.com/apikey"}
            if r.status_code != 200:
                return {"ok": False, "error": f"{r.status_code}: {r.text[:200]}"}

            op_name = r.json().get("name", "")
            print(f"   Veo operação iniciada: {op_name}")

            # Poll (Veo demora ~1-3 min)
            for i in range(40):
                time.sleep(10)
                pr = httpx.get(f"{BASE}/{op_name}?key={GOOGLE_AI_KEY}", timeout=20)
                op = pr.json()
                if op.get("done"):
                    resp = op.get("response", {})
                    videos = resp.get("generateVideoResponse", {}).get("generatedSamples", [])
                    if videos:
                        uri = videos[0].get("video", {}).get("uri", "")
                        if uri and out_path:
                            vr = httpx.get(f"{uri}&key={GOOGLE_AI_KEY}", timeout=120)
                            pathlib.Path(out_path).write_bytes(vr.content)
                            return {"ok": True, "path": out_path,
                                    "size_kb": len(vr.content) // 1024}
                        return {"ok": True, "uri": uri}
                    return {"ok": False, "error": f"Sem vídeo: {op}"}
                print(f"   Veo processando... ({(i+1)*10}s)")
            return {"ok": False, "error": "Timeout Veo (>400s)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def status():
    print("=" * 56)
    print("  GOOGLE AI — Status de Integração — Aura Decore")
    print("=" * 56)
    print(f"\n  GOOGLE_AI_KEY: {'configurada ✅' if GOOGLE_AI_KEY else 'AUSENTE ❌'}")

    # Texto
    print("\n  [1/3] Gemini Texto...")
    t = GeminiText.generate("Responda apenas: OK", max_tokens=10)
    print(f"     {'✅ ' + MODEL_TEXT_FAST if t['ok'] else '❌ ' + t.get('error','')[:80]}")

    # Imagem
    print("\n  [2/3] Gemini Imagem...")
    img_r = httpx.post(
        f"{BASE}/models/{MODEL_IMAGE}:generateContent?key={GOOGLE_AI_KEY}",
        json={"contents": [{"parts": [{"text": "x"}]}],
              "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}, timeout=20)
    if img_r.status_code == 200:
        print(f"     ✅ {MODEL_IMAGE} (billing ativo)")
    elif img_r.status_code == 429:
        print(f"     ⚠️  {MODEL_IMAGE} existe mas free_tier=0 → ative billing")
    else:
        print(f"     ❌ {img_r.status_code}")

    # Vídeo
    print("\n  [3/3] Veo Vídeo...")
    v_r = httpx.post(
        f"{BASE}/models/{MODEL_VEO}:predictLongRunning?key={GOOGLE_AI_KEY}",
        json={"instances": [{"prompt": "x"}]}, timeout=20)
    if v_r.status_code == 200:
        print(f"     ✅ {MODEL_VEO} (billing ativo)")
    elif v_r.status_code == 429:
        print(f"     ⚠️  {MODEL_VEO} existe mas free_tier=0 → ative billing")
    else:
        print(f"     ❌ {v_r.status_code}: {v_r.text[:100]}")

    print("\n" + "=" * 56)
    print("  Para imagem+vídeo: aistudio.google.com/apikey → ativar billing")
    print("  Custo: imagem ~US$0.04 | Veo ~US$0.35/seg")
    print("=" * 56)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        status()
    elif sys.argv[1] == "status":
        status()
    elif sys.argv[1] == "text":
        r = GeminiText.generate(sys.argv[2] if len(sys.argv) > 2 else "Olá")
        print(r.get("text") if r["ok"] else r.get("error"))
    elif sys.argv[1] == "image":
        out = sys.argv[3] if len(sys.argv) > 3 else "gemini_image.png"
        r = GeminiImage.generate(sys.argv[2], out)
        print(json.dumps(r, ensure_ascii=False))
    elif sys.argv[1] == "video":
        out = sys.argv[3] if len(sys.argv) > 3 else "gemini_video.mp4"
        r = GeminiVeo.generate(sys.argv[2], out)
        print(json.dumps(r, ensure_ascii=False))
