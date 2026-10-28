# Sandbox harness: isolated HOME, time limit, peak RSS sampling, disk size, METRIC parsing, one JSON line per attempt.
# Original harness script, copied unmodified apart from this header. Comments inside may be in Portuguese.
"""Suite de testes de instalacao/uso em sandbox descartavel (CPU). Cada teste roda com HOME isolado, timeout e medicao de tempo, RSS de pico e disco.
Saida: out/sandbox/results.jsonl (1 linha por teste) + logs por teste. Linhas 'METRIC k=v' impressas pelo teste viram metricas estruturadas.
uso: python sandbox_suite.py [ids...]"""
import json
import os
import re
import subprocess
import sys
import time

import psutil

ROOT = "/workspace/sb"
OUT = "/workspace/eco/out/sandbox"
os.makedirs(OUT, exist_ok=True)
os.makedirs(ROOT + "/t", exist_ok=True)
os.makedirs(ROOT + "/h", exist_ok=True)
RES = OUT + "/results.jsonl"

SAMPLE_LOG = r"""python - <<'PY'
import random
random.seed(1)
lines=[]
for i in range(3000):
    lines.append(f"2026-10-26 12:{i%60:02d}:{i%60:02d} INFO worker-{i%8} request id={random.randint(1,10**6)} path=/api/v1/items status=200 took={random.randint(1,90)}ms")
lines.insert(1700,"2026-10-26 12:28:20 FATAL worker-3 database connection pool exhausted: could not obtain connection after 30s (host=db-prod-2)")
open('sample.log','w').write("\n".join(lines))
PY"""

T = {}


def t(id_, name, script, timeout=900, tier="T1"):
    T[id_] = dict(name=name, script=script, timeout=timeout, tier=tier)


t("playwright", "Playwright", """pip install -q playwright && playwright install --with-deps chromium >/dev/null 2>&1
python - <<'PY'
import time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); ts=[]
    for i in range(5):
        t0=time.time(); pg.goto("https://example.com"); pg.title(); ts.append(time.time()-t0)
    print("METRIC goto_ms_median=%d"%(sorted(ts)[2]*1000)); b.close()
PY""", 900, "T2")
t("crawl4ai", "Crawl4AI", """pip install -q crawl4ai && crawl4ai-setup >/dev/null 2>&1
python - <<'PY'
import asyncio,time
from crawl4ai import AsyncWebCrawler
async def main():
    async with AsyncWebCrawler() as c:
        for u in ("https://example.com","https://docs.python.org/3/library/json.html"):
            t0=time.time(); r=await c.arun(url=u); dt=time.time()-t0
            print("METRIC %s_s=%.2f md_chars=%d"%(u.split('/')[2].replace('.','_'),dt,len(r.markdown or "")))
asyncio.run(main())
PY""", 1200, "T2")
t("obscura", "Obscura", """curl -sLO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz && tar xzf obscura-x86_64-linux.tar.gz && chmod +x obscura
python - <<'PY'
import subprocess,time
ts=[]
for i in range(5):
    t0=time.time(); o=subprocess.run(["./obscura","fetch","https://example.com","--eval","document.title"],capture_output=True,text=True,timeout=60); ts.append(time.time()-t0)
print("OUT",o.stdout.strip()[:80],o.stderr.strip()[:120])
print("METRIC fetch_ms_median=%d"%(sorted(ts)[2]*1000))
PY""", 600, "T2")
t("camoufox_detect", "Camofox browser", """pip install -q camoufox playwright >/dev/null 2>&1; python -m camoufox fetch >/dev/null 2>&1; python -m playwright install --with-deps chromium >/dev/null 2>&1
python - <<'PY'
import re
from camoufox.sync_api import Camoufox
with Camoufox(headless=True) as b:
    p=b.new_page(); p.goto("https://bot.sannysoft.com/",timeout=60000); p.wait_for_timeout(4000)
    t=p.inner_text("body")
print("METRIC detector_page_chars=%d failed_mentions=%d"%(len(t),len(re.findall(r'(?i)failed',t))))
print(t[:300].replace("\\n"," | "))
PY
python - <<'PY'
from playwright.sync_api import sync_playwright
import re
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto("https://bot.sannysoft.com/",timeout=60000); pg.wait_for_timeout(4000); t=pg.inner_text("body")
print("METRIC baseline_playwright_failed_mentions=%d"%len(re.findall(r'(?i)failed',t)))
PY""", 1500, "T2")
t("headroom", "Headroom", SAMPLE_LOG + """
pip install -q headroom-ai >/dev/null 2>&1; pip show headroom-ai | head -2
python - <<'PY'
import time,inspect
import headroom
print("API:",[n for n in dir(headroom) if not n.startswith('_')][:25])
txt=open('sample.log').read()
try:
    from headroom import compress
    t0=time.time(); r=compress([{"role":"user","content":txt}]); dt=time.time()-t0
    print("RESULT type",type(r).__name__, str(r)[:300])
    print("METRIC compress_s=%.2f"%dt)
except Exception as e: print("ERR",repr(e)[:300])
PY""", 1200, "T2")
t("mcptoon", "mcptoon", """pip install -q mcptoon >/dev/null 2>&1; mcptoon status 2>&1 | head -8; mcptoon bench 2>&1 | tail -8""", 600, "T2")
t("concord", "Concord MCP", """npm install -g @concord-ai/concord-mcp >/dev/null 2>&1; concord --help 2>&1 | head -8; npm ls -g --depth=0 2>/dev/null | head""", 600)
t("trail_graft", "Graft", """git clone -q --depth 1 https://github.com/pallets/flask.git repo && cd repo && npm install -g @trailhq/trail-code >/dev/null 2>&1; (time timeout 300 trail init --yes </dev/null) 2>&1 | tail -12; du -sh graft .trail 2>/dev/null; ls .trail | head; true""", 900, "T2")
t("codebase_memory", "codebase-memory-mcp", """git clone -q --depth 1 https://github.com/pallets/flask.git repo
URL=$(curl -s https://api.github.com/repos/DeusData/codebase-memory-mcp/releases/latest | python -c "import sys,json;a=json.load(sys.stdin)['assets'];print([x['browser_download_url'] for x in a if 'linux' in x['name'].lower() and 'amd64' in x['name'].lower() or ('linux' in x['name'].lower() and 'x86' in x['name'].lower())][0])")
curl -sLo cbm.tgz "$URL"; mkdir -p cbm && tar xzf cbm.tgz -C cbm 2>/dev/null || cp cbm.tgz cbm/bin; ls cbm | head; B=$(find cbm -type f -perm -u+x | head -1); echo BIN $B; $B --help 2>&1 | head -15; (time $B cli index_repository '{"repo_path":"'$PWD'/repo"}') 2>&1 | tail -8""", 900, "T2")
t("hyperframes", "HyperFrames", """git clone -q --depth 1 https://github.com/heygen-com/hyperframes.git hf && cd hf && ls | head -30 && cat package.json | head -30 && (time bun install >inst.log 2>&1) 2>&1 | tail -4; tail -2 inst.log; npx -y hyperframes --help 2>&1 | head -15""", 1500)
t("litpage", "Litpage", """git clone -q --depth 1 https://github.com/litmers-dev/litpage.git lp && cd lp && (time pnpm install >inst.log 2>&1) 2>&1 | tail -3; tail -2 inst.log; (time pnpm build >build.log 2>&1) 2>&1 | tail -3; tail -2 build.log; (PORT=4010 timeout 90 pnpm start >start.log 2>&1 &); sleep 35; tail -3 start.log; curl -s -o /dev/null -w 'METRIC http_code=%{http_code}\\n' http://127.0.0.1:4010/ ; ps -eo rss,cmd | grep -i -E 'node' | sort -rn | head -2""", 900, "T2")
t("open_webui", "Open WebUI", """pip install -q open-webui >/dev/null 2>&1; (DATA_DIR=$PWD/data timeout 240 open-webui serve --port 4020 >serve.log 2>&1 &); for i in $(seq 1 40); do sleep 5; c=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4020/health); [ "$c" = 200 ] && { echo "METRIC ready_s=$((i*5))"; break; }; done; ps -eo rss,cmd | grep -i open-webui | sort -rn | head -2; du -sh $(python -c "import open_webui,os;print(os.path.dirname(open_webui.__file__))")""", 1200, "T2")
t("llamacpp", "llama.cpp", """git clone -q --depth 1 https://github.com/ggml-org/llama.cpp.git lc && cd lc && cmake -B build -DGGML_NATIVE=ON >/dev/null 2>&1 && (time cmake --build build -j16 --target llama-bench llama-cli >/dev/null 2>&1) 2>&1 | tail -3
python -c "from huggingface_hub import hf_hub_download as h; h('Qwen/Qwen2.5-0.5B-Instruct-GGUF','qwen2.5-0.5b-instruct-q4_k_m.gguf',local_dir='.')" 2>&1 | tail -1; ls *.gguf; ./build/bin/llama-bench -m qwen2.5-0.5b-instruct-q4_k_m.gguf -p 128 -n 64 -t 16 2>&1 | tail -6""", 1500, "T2")
t("bitnet", "BitNet (bitnet.cpp)", """git clone -q --recursive https://github.com/microsoft/BitNet.git bn && cd bn && pip install -q -r requirements.txt >/dev/null 2>&1; python -c "from huggingface_hub import snapshot_download as d; d('microsoft/BitNet-b1.58-2B-4T-gguf',local_dir='models/BitNet-b1.58-2B-4T')" 2>&1 | tail -1; (time python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s >build.log 2>&1) 2>&1 | tail -3; tail -3 build.log; python run_inference.py -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf -p "Explique o que e um indice de banco de dados." -n 64 -t 16 2>&1 | tail -6""", 2400, "T2")
t("faster_whisper_cpu", "faster-whisper", """python3 -m venv vw && . vw/bin/activate && pip install -q faster-whisper "av>=15" >/dev/null 2>&1; curl -sLo jfk.wav https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav
python - <<'PY'
import time
from faster_whisper import WhisperModel
for sz in ("tiny","base","small"):
    m=WhisperModel(sz,device="cpu",compute_type="int8",cpu_threads=16)
    t0=time.time(); segs,info=m.transcribe("jfk.wav",language="en"); txt=" ".join(s.text for s in segs); dt=time.time()-t0
    print("METRIC %s_rtf=%.3f"%(sz,dt/info.duration)); print(sz,txt[:90])
PY""", 1200, "T2")
t("mediamtx", "MediaMTX", """curl -sL https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz -o m.tgz 2>/dev/null; URL=$(curl -s https://api.github.com/repos/bluenviron/mediamtx/releases/latest | python -c "import sys,json;a=json.load(sys.stdin)['assets'];print([x['browser_download_url'] for x in a if x['name'].endswith('linux_amd64.tar.gz')][0])"); curl -sL $URL -o m.tgz && tar xzf m.tgz; (./mediamtx >mtx.log 2>&1 &); sleep 2
ffmpeg -loglevel error -re -f lavfi -i testsrc2=size=1280x720:rate=15 -t 20 -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://127.0.0.1:8554/cam1 &
sleep 4; python - <<'PY'
import subprocess,time
t0=time.time(); o=subprocess.run(["ffprobe","-v","error","-rtsp_transport","tcp","-show_entries","stream=codec_name,width,height,avg_frame_rate","-of","csv=p=0","rtsp://127.0.0.1:8554/cam1"],capture_output=True,text=True,timeout=30)
print("METRIC probe_ms=%d"%((time.time()-t0)*1000), o.stdout.strip())
PY
ps -eo rss,cmd | grep mediamtx | head -1; pkill mediamtx""", 300, "T2")
t("onvif_zeep", "onvif-zeep", """pip install -q onvif-zeep >/dev/null 2>&1; python -c "import onvif;print('onvif ok',onvif.__file__)" """, 300)
t("gepa", "GEPA", """pip install -q gepa >/dev/null 2>&1; python -c "import gepa;print('gepa',getattr(gepa,'__version__','?'));print([n for n in dir(gepa) if not n.startswith('_')][:20])" """, 400)
t("taipy", "Taipy", """python3 -m venv vt && . vt/bin/activate && pip install -q taipy 2>&1 | tail -2; python -c "import taipy.gui" 2>&1 | tail -1; cat > app.py <<'PY'
from taipy.gui import Gui
Gui("# Ola Taipy").run(port=4030, run_browser=False, use_reloader=False)
PY
(timeout 120 python app.py >app.log 2>&1 &); sleep 45; tail -4 app.log; ss -ltn | grep 4030 || true; curl -s -o /dev/null -w 'METRIC http_code=%{http_code}\\n' http://127.0.0.1:4030/""", 900, "T2")
t("nautilus", "NautilusTrader", """pip install -q nautilus_trader >/dev/null 2>&1; python -c "import nautilus_trader;print('nautilus',nautilus_trader.__version__)" """, 900)
t("autohedge", "AutoHedge", """pip install -q autohedge >/dev/null 2>&1; python -c "import autohedge;print('autohedge ok')" 2>&1 | tail -2""", 600)
t("vibe_trading", "Vibe-Trading", """git clone -q --depth 1 https://github.com/HKUDS/Vibe-Trading.git vt && cd vt && ls | head -20; (time pip install -q -e . >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("drawdb", "drawDB", """git clone -q --depth 1 https://github.com/drawdb-io/drawdb.git d && cd d && (time npm install >/dev/null 2>&1) 2>&1 | tail -3; (time npm run build >/dev/null 2>&1) 2>&1 | tail -3; du -sh dist""", 1200)
t("gods_eye", "Gods Eye View", """git clone -q --depth 1 https://github.com/bilawalsidhu/gods-eye-view.git g && cd g && ls | head; (time npm install >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("obliteratus", "OBLITERATUS", """git clone -q --depth 1 https://github.com/elder-plinius/OBLITERATUS.git ob && cd ob && ls | head -20; pip install -q -e . >/dev/null 2>&1; python -c "import obliteratus;print('obliteratus ok')" 2>&1 | tail -2""", 900)
t("whatsmeow", "whatsmeow", """git clone -q --depth 1 https://github.com/tulir/whatsmeow.git w && cd w && (time go build ./... ) 2>&1 | tail -4""", 900)
t("mautrix_wa", "mautrix-whatsapp", """git clone -q --depth 1 https://github.com/mautrix/whatsapp.git m && cd m && (time go build ./cmd/... ) 2>&1 | tail -4""", 900)
t("wa_akg", "WA-AKG", """git clone -q --depth 1 https://github.com/mrifqidaffaaditya/WA-AKG.git a && cd a && ls | head; (time npm install >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("open_llm_vtuber", "Open-LLM-VTuber", """git clone -q --depth 1 https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git v && cd v && ls | head -20; pip install -q uv >/dev/null 2>&1; (time timeout 900 uv sync >sync.log 2>&1) 2>&1 | tail -3; tail -3 sync.log; du -sh .venv 2>/dev/null""", 1500)
t("open_gen_ai", "Open Generative AI", """git clone -q --depth 1 https://github.com/Anil-matcha/Open-Generative-AI.git o && cd o && ls | head -20; (time npm install >/dev/null 2>&1) 2>&1 | tail -3""", 1200)
t("opencut", "OpenCut", """git clone -q --depth 1 https://github.com/OpenCut-app/OpenCut.git oc && cd oc && ls | head; (time timeout 900 npm install >/dev/null 2>&1) 2>&1 | tail -3""", 1200)
t("openmontage", "OpenMontage", """git clone -q --depth 1 https://github.com/calesthio/OpenMontage.git om && cd om && ls | head -20; du -sh .""", 400)
t("comfyui_cpu", "ComfyUI", """git clone -q --depth 1 https://github.com/comfyanonymous/ComfyUI.git c && cd c && (time pip install -q -r requirements.txt >/dev/null 2>&1) 2>&1 | tail -3; (timeout 90 python main.py --cpu --listen 127.0.0.1 --port 4040 >run.log 2>&1 &); sleep 45; curl -s -o /dev/null -w 'METRIC http_code=%{http_code}\\n' http://127.0.0.1:4040/; tail -3 run.log""", 1500, "T2")
t("sglang", "SGLang", """(time pip install -q sglang >/dev/null 2>&1) 2>&1 | tail -3; python -c "import sglang;print('sglang',sglang.__version__)" 2>&1 | tail -2""", 1500)
t("otel", "OpenTelemetry (python)", """pip install -q opentelemetry-sdk >/dev/null 2>&1
python - <<'PY'
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
class N(SpanExporter):
    def export(self,s): return SpanExportResult.SUCCESS
trace.set_tracer_provider(TracerProvider()); trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(N()))
tr=trace.get_tracer("x"); t0=time.time()
for i in range(100000):
    with tr.start_as_current_span("s"): pass
print("METRIC spans_per_s=%d"%(100000/(time.time()-t0)))
PY""", 400, "T2")
t("agent_reach", "Agent Reach", """git clone -q --depth 1 https://github.com/Panniantong/Agent-Reach.git ar && cd ar && ls | head -20; (time pip install -q -e . >/dev/null 2>&1) 2>&1 | tail -3; agent-reach --help 2>&1 | head -10""", 900)
t("gumroad", "Gumroad", """git clone -q --depth 1 https://github.com/antiwork/gumroad.git gr && cd gr && ls | head -20; du -sh .; echo "NOTE: Rails+Postgres+Redis+Elasticsearch; instalacao completa fora do escopo do smoke" """, 300)
t("ever_gauzy", "Ever Gauzy", """git clone -q --depth 1 https://github.com/ever-co/ever-gauzy.git eg && cd eg && ls | head -20; du -sh .; echo "NOTE: monorepo Nx pesado (Postgres/Redis); so clone medido" """, 400)
t("ghost", "Ghost", """npm install -g ghost-cli >/dev/null 2>&1; mkdir g && cd g && (time timeout 600 ghost install local --no-prompt --no-start --db sqlite3 >install.log 2>&1) 2>&1 | tail -3; tail -5 install.log; du -sh . """, 1200, "T2")
t("paymenter", "Paymenter", """git clone -q --depth 1 https://github.com/Paymenter/Paymenter.git p && cd p && ls | head; du -sh .; echo "NOTE: PHP/Laravel+MySQL; so clone medido" """, 300)
t("getfy", "Getfy", """git clone -q --depth 1 https://github.com/getfy-opensource/getfy.git gf && cd gf && ls | head; du -sh .""", 300)
t("xiryn", "Xiryn", """git clone -q --depth 1 https://github.com/SouravBeraAkaSpeed/xiryn.git x 2>&1 | tail -1; cd x 2>/dev/null && ls | head; du -sh .""", 400)
t("geo_sleuth", "geo-sleuth", """git clone -q --depth 1 https://github.com/Oldcircle/geo-sleuth.git gs && cd gs && ls | head -20; cat README.md | head -40""", 300)
t("litellm_none", "FreeLLMAPI", """git clone -q --depth 1 https://github.com/tashfeenahmed/freellmapi.git f && cd f && ls | head; (time npm install >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("docker_android", "docker-android", """git clone -q --depth 1 https://github.com/budtmo/docker-android.git da && cd da && ls | head; du -sh .; echo "NOTE: exige Docker+KVM; nao testavel em instancia Vast" """, 300)
t("anyps5", "AnyPS5", """git clone -q --depth 1 https://github.com/boykopovar/anyps5.git ap && cd ap && ls | head; du -sh .; echo "NOTE: C++ especifico de console; so clone" """, 300)
t("agopengps", "AgOpenGPS", """echo "NOTE: C#/Windows + hardware GPS RTK; nao testavel em Linux/sem hardware" """, 60)
t("xtool", "xtool", """git clone -q --depth 1 https://github.com/xtool-org/xtool.git xt && cd xt && ls | head; du -sh .; echo "NOTE: Swift + conta Apple; so clone" """, 300)
t("fincept", "Fincept Terminal", """git clone -q --depth 1 https://github.com/Fincept-Corporation/FinceptTerminal.git ft && cd ft && ls | head; du -sh .; echo "NOTE: app Qt/C++ desktop; so clone" """, 400)
t("yt_automation", "youtube-automation-agent", """git clone -q --depth 1 https://github.com/darkzOGx/youtube-automation-agent.git ya && cd ya && ls | head; (time npm install >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("baocut", "BaoCut", """git clone -q --depth 1 https://github.com/JimLiu/baocut.git bc && cd bc && ls | head -20; du -sh .; echo "NOTE: app Tauri/Rust+Node; so clone (licenca source-available)" """, 400)
t("pixelrag", "PixelRAG", """git clone -q --depth 1 https://github.com/navneet-singh2907/pixelrag-langchain.git pr && cd pr && ls | head; (time pip install -q -e . >/dev/null 2>&1) 2>&1 | tail -3""", 900)
t("kev", "Kev (modelos de decisao)", """git clone -q --depth 1 https://github.com/aleskxyz/kev-onnx.git k && cd k && ls | head; du -sh .; cat README.md | head -30""", 300)
t("pix_brcode", "pix_brcode", """git clone -q --depth 1 https://github.com/igorgbr/pix_brcode.git pb && cd pb && ls | head; du -sh .; echo "NOTE: Elixir; Pix BR Code e CRC16+TLV (comparar com o gerador do Mercado Pago)" """, 300)
t("frigate", "Frigate", """git clone -q --depth 1 https://github.com/blakeblackshear/frigate.git fr && cd fr && ls | head; du -sh .; echo "NOTE: exige Docker; so clone" """, 400)


t("openvoice_cpu", "OpenVoice", """pip install -q uv >/dev/null 2>&1; uv venv --python 3.10 ov >/dev/null 2>&1; . ov/bin/activate
git clone -q --depth 1 https://github.com/myshell-ai/OpenVoice.git OV && cd OV
uv pip install -q "setuptools<81" wheel -e . 2>&1 | tail -2
uv pip install -q "git+https://github.com/myshell-ai/MeloTTS.git" soundfile 2>&1 | tail -3
uv pip install -q faster-whisper whisper-timestamped wavmark 2>&1 | tail -1; uv pip install -q --reinstall "setuptools<81" 2>&1 | tail -1; python -c "import pkg_resources; print('pkg_resources ok')"
python -m unidic download >/dev/null 2>&1
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("myshell-ai/OpenVoiceV2", local_dir="ckpt")
print("ckpt ok")
PY
cat > ov_test.py <<'PY'
import time, os, torch, soundfile as sf
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
from melo.api import TTS
dev="cpu"
conv=ToneColorConverter("ckpt/converter/config.json", device=dev); conv.load_ckpt("ckpt/converter/checkpoint.pth")
t0=time.time(); tts=TTS(language="EN", device=dev); sid=tts.hps.data.spk2id["EN-US"]; load=time.time()-t0
text="Hello, this is a test of voice cloning on a small CPU server."
os.makedirs("o",exist_ok=True)
t=time.time(); tts.tts_to_file(text, sid, "o/base.wav", speed=1.0); t_tts=time.time()-t
d=sf.info("o/base.wav").duration
print("METRIC melo_tts_s=%.2f melo_audio_s=%.2f melo_rtf=%.3f load_s=%.1f"%(t_tts,d,t_tts/d,load))
# referencia: o proprio audio gerado (voz sintetica; clonagem com amostra autorizada fica p/ teste manual)
src_se=torch.load("ckpt/base_speakers/ses/en-us.pth",map_location=dev)
t=time.time(); tgt,_=se_extractor.get_se("o/base.wav",conv,vad=False); t_se=time.time()-t
rs=[]
for i in range(3):
    t=time.time(); conv.convert(audio_src_path="o/base.wav",src_se=src_se,tgt_se=tgt,output_path="o/conv.wav",message="@x"); rs.append(time.time()-t)
print("METRIC se_extract_s=%.2f convert_s_median=%.2f convert_rtf=%.3f"%(t_se,sorted(rs)[1],sorted(rs)[1]/d))
PY
python ov_test.py 2>&1 | tail -8""", 2400, "T2")

SKILLS = {"Taste Skill": "leonxlnx/taste-skill", "Impeccable": "pbakaus/impeccable", "UI/UX Pro Max": "nextlevelbuilder/ui-ux-pro-max-skill", "Diagram Design": "cathrynlavery/diagram-design",
          "Awesome Design MD": "VoltAgent/awesome-design-md", "Design.md": "google-labs-code/design.md", "Design DNA": "zanwei/design-dna", "SwiftUI Pro": "twostraws/swiftui-agent-skill",
          "motionmaxxing": "tejashmakwana/motionmaxxing", "animate (cth9191)": "cth9191/animate", "Claude Ads": "AgriciDaniel/claude-ads", "lemo-opuscar": "lemomo-ai/lemo-opuscar",
          "brag": "latent-spaces/brag", "REA (Reverse Engineer Anything)": "alextnetto/res", "get-brolls": "engenheirodevideo/get-brolls", "universal-modder": "rehan-remade/universal-modder",
          "ReelMimic": "edenfunf/reelmimic", "Bugframe": "vBug-dev/bugframe.github.io"}
for i, (n, slug) in enumerate(SKILLS.items()):
    t("skill_%02d" % i, n, f"""git clone -q --depth 1 https://github.com/{slug}.git s && cd s
python - <<'PY'
import os,re,glob,json
files=[f for f in glob.glob('**/*',recursive=True) if os.path.isfile(f) and '.git/' not in f]
md=[f for f in files if f.lower().endswith(('.md','.mdx'))]
skills=[f for f in files if os.path.basename(f).upper()=='SKILL.MD']
chars=sum(os.path.getsize(f) for f in md)
sk=sum(os.path.getsize(f) for f in skills)
print("METRIC files=%d md_files=%d skill_md=%d md_kchars=%d skill_tokens_est=%d"%(len(files),len(md),len(skills),chars//1000,sk//4))
print("SKILLS",[os.path.dirname(f) or '.' for f in skills][:8])
PY""", 300)

BASE = """set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq build-essential cmake git curl unzip ffmpeg golang-go cargo python3-pip python3-venv libssl-dev pkg-config >/dev/null 2>&1
(curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 && apt-get install -y -qq nodejs >/dev/null 2>&1) || true
ln -sf $(which python3) /usr/local/bin/python; ln -sf $(which pip3) /usr/local/bin/pip
pip install -q --upgrade pip psutil 'setuptools<81' wheel 'huggingface_hub[cli]' >/dev/null 2>&1 || pip install -q --break-system-packages --upgrade psutil 'setuptools<81' wheel 'huggingface_hub[cli]' >/dev/null 2>&1 || true
npm install -g pnpm bun >/dev/null 2>&1 || true
which hf huggingface-cli | head -2
node --version; go version; python3 --version; nproc; free -g | head -2; df -h /workspace | tail -1
"""


def run_test(id_, spec, retry=False):
    d = f"{ROOT}/t/{id_}"
    h = f"{ROOT}/h/{id_}"
    for p in (d, h):
        os.makedirs(p, exist_ok=True)
    env = {"PATH": os.environ["PATH"], "HOME": h, "TMPDIR": d, "LANG": "C.UTF-8", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "CI": "1",
           "PIP_BREAK_SYSTEM_PACKAGES": "1", "npm_config_cache": h + "/.npm", "GOPATH": h + "/go", "CARGO_HOME": h + "/.cargo", "XDG_CACHE_HOME": h + "/.cache"}
    log = open(f"{OUT}/{id_}.log", "w")
    t0 = time.time()
    p = subprocess.Popen(["bash", "-lc", spec["script"]], cwd=d, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
    peak = 0
    status = "ok"
    while p.poll() is None:
        try:
            rss = 0
            for c in [psutil.Process(p.pid)] + psutil.Process(p.pid).children(recursive=True):
                try:
                    rss += c.memory_info().rss
                except Exception:  # noqa: BLE001
                    pass
            peak = max(peak, rss)
        except Exception:  # noqa: BLE001
            pass
        if time.time() - t0 > spec["timeout"]:
            status = "timeout"
            try:
                os.killpg(os.getpgid(p.pid), 9)
            except Exception:  # noqa: BLE001
                pass
            break
        time.sleep(0.5)
    dt = time.time() - t0
    log.close()
    txt = open(f"{OUT}/{id_}.log", errors="replace").read()
    metrics = {}
    for m in re.finditer(r"METRIC ([^\n]+)", txt):
        for kv in m.group(1).split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                try:
                    metrics[k] = float(v)
                except ValueError:
                    metrics[k] = v
    du = subprocess.run(["du", "-sm", d, h], capture_output=True, text=True).stdout.split()
    disk = sum(int(x) for x in du[::2]) if du else None
    rc = p.returncode
    if status == "ok" and rc not in (0, None):
        status = "exit_%s" % rc
    low = txt.lower()
    note = ""
    if "note:" in low:
        note = re.search(r"NOTE: ([^\n]+)", txt).group(1) if re.search(r"NOTE: ([^\n]+)", txt) else ""
    rec = {"id": id_, "attempt": 2 if retry else 1, "name": spec["name"], "tier": spec["tier"], "status": status, "wall_s": round(dt, 1), "peak_rss_mb": round(peak / 2**20), "disk_mb": disk,
           "metrics": metrics, "note": note, "tail": txt[-700:], "t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    open(RES, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(id_, status, round(dt), "s", rec["peak_rss_mb"], "MB", metrics, flush=True)


if __name__ == "__main__":
    if not os.path.exists(OUT + "/base.done"):
        subprocess.run(["bash", "-lc", BASE], check=False)
        open(OUT + "/base.done", "w").write("1")
    ids = sys.argv[1:] or list(T)
    for i in ids:
        try:
            run_test(i, T[i])
        except Exception as e:  # noqa: BLE001
            open(RES, "a").write(json.dumps({"id": i, "name": T[i]["name"], "status": "runner_error", "err": repr(e)[:300]}) + "\n")
    # 2a passada: repete uma vez os que falharam (rede/timeout transitorio); resultado vai como id#retry
    failed = [json.loads(line) for line in open(RES)] if os.path.exists(RES) else []
    redo = [r["id"] for r in failed if r.get("status") not in ("ok",) and "#" not in r["id"] and r["id"] in T and "NOTE:" not in (r.get("tail") or "")]
    for i in redo:
        spec = dict(T[i])
        spec["timeout"] = int(spec["timeout"] * 1.5)
        try:
            run_test(i, spec, retry=True)
        except Exception as e:  # noqa: BLE001
            open(RES, "a").write(json.dumps({"id": i + "#retry", "status": "runner_error", "err": repr(e)[:300]}) + chr(10))
    print("SUITE_DONE", flush=True)
