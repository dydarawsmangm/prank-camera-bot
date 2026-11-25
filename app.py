import os
import time
import threading
import requests
from flask import Flask, request, jsonify, render_template_string

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID", "").strip()
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

app = Flask(__name__)
offset = 0

PAGE = r"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>مقلب الكاميرا 😂</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;
background:linear-gradient(145deg,#111827,#312e81);font-family:Arial,sans-serif;color:#fff;padding:20px}
main{width:min(100%,480px);background:#ffffff12;border:1px solid #ffffff25;border-radius:24px;
padding:26px;text-align:center;box-shadow:0 20px 60px #0005}
h1{font-size:28px;margin:4px 0 12px}p{color:#e5e7eb;line-height:1.7}
button{border:0;border-radius:12px;padding:13px 18px;font-size:16px;font-weight:bold;
cursor:pointer;margin:7px;background:#a5b4fc;color:#111827}
button:disabled{opacity:.5;cursor:not-allowed}video,img{width:100%;border-radius:14px;margin-top:12px;background:#000}
#status{min-height:28px;color:#fde68a}.notice{font-size:13px;color:#cbd5e1;border-top:1px solid #ffffff25;padding-top:14px}
.hidden{display:none}
</style></head>
<body><main>
<div style="font-size:48px">😂📸</div>
<h1>مقلب الكاميرا!</h1>
<p>إذا حابب تشارك بالمقلب، اضغط «تشغيل الكاميرا». سيطلب المتصفح إذنك أولاً.<br>
لن تُلتقط أو تُرسل أي صورة إلا إذا ضغطت بنفسك على «التقاط وإرسال الصورة».</p>
<button id="start">تشغيل الكاميرا الأمامية</button>
<video id="video" class="hidden" autoplay playsinline></video>
<div id="controls" class="hidden">
<button id="capture">التقاط وإرسال الصورة</button>
<button id="stop">إيقاف الكاميرا</button>
</div>
<canvas id="canvas" class="hidden"></canvas>
<p id="status" role="status"></p>
<div class="notice">تنبيه: عند اختيار «التقاط وإرسال الصورة» ستُرسل الصورة إلى صاحب البوت عبر تيليجرام. يمكنك رفض إذن الكاميرا أو إغلاق الصفحة في أي وقت.</div>
</main>
<script>
const start=document.getElementById('start'), video=document.getElementById('video'),
controls=document.getElementById('controls'), statusEl=document.getElementById('status'),
canvas=document.getElementById('canvas');
let stream=null;
start.onclick=async()=>{
 try{
  stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
  video.srcObject=stream; video.classList.remove('hidden'); controls.classList.remove('hidden');
  start.disabled=true; statusEl.textContent='الكاميرا تعمل. الصورة لن تُرسل إلا عند ضغطك على زر الإرسال.';
 }catch(e){statusEl.textContent='لم يتم تشغيل الكاميرا. يمكنك السماح بالإذن أو إغلاق الصفحة.';}
};
document.getElementById('stop').onclick=()=>{
 if(stream) stream.getTracks().forEach(t=>t.stop());
 stream=null; video.srcObject=null; video.classList.add('hidden'); controls.classList.add('hidden');
 start.disabled=false; statusEl.textContent='تم إيقاف الكاميرا.';
};
document.getElementById('capture').onclick=async()=>{
 if(!stream) return;
 const w=video.videoWidth,h=video.videoHeight;
 if(!w||!h){statusEl.textContent='انتظر لحظة حتى تظهر الصورة.';return;}
 canvas.width=w;canvas.height=h;canvas.getContext('2d').drawImage(video,0,0,w,h);
 const data=canvas.toDataURL('image/jpeg',0.85);
 if(!confirm('هل توافق على إرسال هذه الصورة إلى صاحب البوت عبر تيليجرام؟')) return;
 statusEl.textContent='جارٍ إرسال الصورة...';
 try{
  const r=await fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:data})});
  const result=await r.json();
  statusEl.textContent=result.ok?'وصلت الصورة إلى صاحب البوت. المقلب نجح 😂':'تعذر الإرسال: '+(result.error||'خطأ غير معروف');
 }catch(e){statusEl.textContent='تعذر الاتصال بالخادم. لم نتمكن من تأكيد الإرسال.';}
};
window.addEventListener('beforeunload',()=>{if(stream)stream.getTracks().forEach(t=>t.stop());});
</script></body></html>"""

def send_message(chat_id, text):
    if not API:
        return
    try:
        requests.post(API + "/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)
    except requests.RequestException:
        pass

def telegram_polling():
    global offset
    while True:
        if not API:
            time.sleep(5)
            continue
        try:
            resp = requests.get(API + "/getUpdates",
                                params={"timeout": 25, "offset": offset},
                                timeout=35)
            data = resp.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "").strip()
                    if not chat_id:
                        continue
                    if text.startswith("/start") or text.startswith("/help"):
                        send_message(chat_id,
                            "أهلاً! 😂 أنا بوت المقالب.\\n"
                            "/link - إرسال رابط صفحة المقلب\\n"
                            "/myid - عرض رقم المحادثة لإعداد صاحب البوت")
                    elif text.startswith("/myid"):
                        send_message(chat_id, f"رقم المحادثة (Chat ID): {chat_id}")
                    elif text.startswith("/link"):
                        if PUBLIC_URL:
                            send_message(chat_id, "هذا رابط صفحة المقلب:\n" + PUBLIC_URL.strip().rstrip("/"))
                        else:
                            send_message(chat_id, "لم يتم ضبط PUBLIC_URL بعد. أضفه في إعدادات الاستضافة.")
                    else:
                        send_message(chat_id, "اكتب /link للحصول على رابط المقلب أو /help للمساعدة.")
        except Exception:
            time.sleep(3)

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/capture")
def capture():
    if not BOT_TOKEN or not OWNER_CHAT_ID:
        return jsonify(ok=False, error="إعدادات البوت غير مكتملة."), 503
    payload = request.get_json(silent=True) or {}
    data_url = payload.get("image", "")
    prefix = "data:image/jpeg;base64,"
    if not data_url.startswith(prefix):
        return jsonify(ok=False, error="صيغة الصورة غير صحيحة."), 400
    import base64
    try:
        image_bytes = base64.b64decode(data_url[len(prefix):], validate=True)
    except Exception:
        return jsonify(ok=False, error="تعذر قراءة الصورة."), 400
    if len(image_bytes) > 8 * 1024 * 1024:
        return jsonify(ok=False, error="حجم الصورة كبير جداً."), 413
    try:
        r = requests.post(API + "/sendPhoto",
            data={"chat_id": OWNER_CHAT_ID, "caption": "صورة أُرسلت بموافقة المستخدم من صفحة المقلب."},
            files={"photo": ("prank.jpg", image_bytes, "image/jpeg")},
            timeout=30)
        result = r.json()
        if not result.get("ok"):
            return jsonify(ok=False, error="رفض تيليجرام إرسال الصورة."), 502
        return jsonify(ok=True)
    except requests.RequestException:
        return jsonify(ok=False, error="تعذر الاتصال بتيليجرام."), 502

# Start Telegram polling when the web server imports this module (e.g. under Gunicorn).
threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
