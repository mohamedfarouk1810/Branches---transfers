import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import streamlit.components.v1 as components

# ==========================================
# 1. إعدادات الصفحة والتنسيق العام
# ==========================================
st.set_page_config(
    page_title="نظام تحويلات الفروع",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Cairo', Tahoma, Arial, sans-serif !important;
    }

    .stMarkdown, p, h1, h2, h3, h4, label {
        direction: rtl !important;
        text-align: right !important;
        white-space: normal !important;
        word-break: normal !important;
    }

    .main-header {
        background: #0d6efd;
        color: white;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 16px;
    }

    .main-header h1 {
        margin: 0;
        font-size: clamp(20px, 4vw, 32px);
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<div class='main-header'><h1>📦 نظام تسجيل واستلام التحويلات بين الفروع</h1></div>",
    unsafe_allow_html=True
)

# ==========================================
# 2. أدوات الإشعارات والتنبيهات (Web + Sound)
# ==========================================
def trigger_browser_notification(title, body):
    """إرسال إشعار متصفح ناطق"""
    js_code = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("{title}", {{
            body: "{body}",
            icon: "https://em-content.zobj.net/source/apple/391/package_1f4e6.png"
        }});
    }}
    </script>
    """
    components.html(js_code, height=0, width=0)

def play_alert_sound():
    """تشغيل صوت تنبيه خفيف"""
    sound_html = """
    <audio autoplay>
        <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
    </audio>
    """
    components.html(sound_html, height=0, width=0)

# ==========================================
# 3. الاتصال بقاعدة بيانات Supabase
# ==========================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase(url: str, key: str) -> Client:
    return create_client(url, key)

supabase = None
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "⚠️ بيانات Supabase غير مضبوطة. أضف SUPABASE_URL و SUPABASE_KEY "
        "في Streamlit Secrets ثم أعد تشغيل التطبيق."
    )
    st.stop()

try:
    supabase = init_supabase(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"⚠️ تعذر الاتصال بـ Supabase: {e}")
    st.stop()

BRANCHES = ["دمياط", "المعادي", "المطار", "الجلاء", "المهندسين"]

# --- الشريط الجانبي ---
with st.sidebar:
    st.header("⚙️ إعدادات الجهاز")
    current_branch = st.selectbox("اختر الفرع الحالي للجهاز:", BRANCHES)
   
    st.divider()
    st.markdown("### 🔔 إشعارات التنبيه")
   
    # مكون تفاعلي يختفي فور السماح بالإشعارات
    components.html("""
        <div id="notif-box">
            <button id="notif-btn" onclick="requestPermission()" style="
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 10px 14px;
                border-radius: 8px;
                cursor: pointer;
                width: 100%;
                font-family: Cairo, sans-serif;
                font-weight: bold;
                font-size: 14px;
            ">🔔 تفعيل إشعارات المتصفح</button>
           
            <div id="notif-active" style="
                display: none;
                background-color: #d1e7dd;
                color: #0f5132;
                padding: 8px 12px;
                border-radius: 8px;
                text-align: center;
                font-family: Cairo, sans-serif;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #badbcc;
            ">
                ✅ الإشعارات مفعلة على هذا الجهاز
            </div>
        </div>

        <script>
        function updateUI() {
            if (Notification.permission === "granted") {
                document.getElementById("notif-btn").style.display = "none";
                document.getElementById("notif-active").style.display = "block";
            }
        }

        function requestPermission() {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    updateUI();
                } else if (permission === "denied") {
                    alert("⚠️ الإشعارات محظورة. يرجى تفعيلها من إعدادات المتصفح (رمز القفل بجوار رابط الموقع).");
                }
            });
        }

        // الفحص التلقائي فور فتح الصفحة
        updateUI();
        </script>
    """, height=50)

# ==========================================
# 4. تبويبات النظام
# ==========================================
tab1, tab2, tab3 = st.tabs(["📤 تسجيل تحويل جديد (إرسال)", "📥 استلام التحويلات الواردة", "📊 سجل التحويلات الشامل"])

# --- التبويب الأول: إرسال تحويل ---
with tab1:
    st.subheader("إرسال تحويل جديد إلى فرع آخر")
   
    with st.form("new_transfer_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
       
        with col1:
            from_b = st.selectbox("الفرع المصدر:", [current_branch] + [b for b in BRANCHES if b != current_branch])
            transfer_date = st.date_input("تاريخ التحويل", value=datetime.today())
           
        with col2:
            transfer_code = st.text_input("رقم التحويلة / الفاتورة:")
            sender_name = st.text_input("القائم بالتحويل (اسم الموظف):")
           
        with col3:
            target_branch = st.selectbox("الفرع المحول إليه:", [b for b in BRANCHES if b != from_b])
            notes = st.text_area("ملحوظات / الأصناف المحولة:", height=100)
           
        submit_btn = st.form_submit_button("🚀 إرسال التحويلة", use_container_width=True)
       
        if submit_btn:
            if not transfer_code or not sender_name:
                st.error("⚠️ يرجى ملء كافة البيانات الأساسية (رقم التحويلة واسم الموظف).")
            else:
                try:
                    data = {
                        "from_branch": from_b,
                        "transfer_date": str(transfer_date),
                        "transfer_code": transfer_code,
                        "sender_name": sender_name,
                        "target_branch": target_branch,
                        "notes": notes,
                        "status": "قيد الانتظار"
                    }
                    supabase.table("transfers").insert(data).execute()
                   
                    # تنبيه عائم سريع عند الإرسال
                    st.toast(f"تم إرسال التحويلة رقم {transfer_code} إلى فرع {target_branch}", icon="🚀")
                    st.success(f"✅ تم تسجيل التحويلة رقم ({transfer_code}) بنجاح في السحابة!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء إرسال البيانات: {e}")

# --- التبويب الثاني: استلام التحويلات الواردة ---
with tab2:
    st.subheader(f"التحويلات الواردة إلى فرع [{current_branch}] (بانتظار التأكيد)")
      
    try:
        if current_branch:
            res = (supabase.table("transfers")
                   .select("*")
                   .eq("target_branch", str(current_branch))
                   .eq("status", "قيد الانتظار")
                   .execute())
            incoming_data = res.data
        else:
            incoming_data = []
    except Exception as e:
        st.error(f"تنبيه من قاعدة البيانات: {e}")
        incoming_data = []

    if not incoming_data:
        st.info("✨ لا توجد تحويلات قيد الانتظار لهذا الفرع حالياً.")
    else:
        # 🚨 تشغيل الإشعارات والصوت في حالة وجود شحنات معلقة للفرع الحالي
        count_pending = len(incoming_data)
        latest_item = incoming_data[0]
       
        # 1. إشعار عائم في الواجهة
        st.toast(f"🔔 يوجد {count_pending} تحويلة بانتظار الاستلام لفرع {current_branch}!", icon="📦")
       
        # 2. إشعار المتصفح وصوت التنبيه
        trigger_browser_notification(
            title=f"تنبيه شحنة واردة - فرع {current_branch}",
            body=f"وصلت تحويلة رقم {latest_item['transfer_code']} من فرع {latest_item['from_branch']}"
        )
        play_alert_sound()

        df_incoming = pd.DataFrame(incoming_data)
        display_df = df_incoming[['from_branch', 'transfer_date', 'transfer_code', 'sender_name', 'notes', 'status']].rename(columns={
            'from_branch': 'الفرع المرسل',
            'transfer_date': 'تاريخ التحويل',
            'transfer_code': 'رقم التحويلة',
            'sender_name': 'القائم بالتحويل',
            'notes': 'الملاحظات',
            'status': 'الحالة'
        })
        st.dataframe(display_df, use_container_width=True)
        st.divider()
       
        st.subheader("تأكيد استلام تحويلة")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
       
        options = {row['id']: f"تحويلة رقم: {row['transfer_code']} من {row['from_branch']}" for row in incoming_data}
        selected_id = col_rec1.selectbox("اختر رقم التحويلة للاستلام:", list(options.keys()), format_func=lambda x: options[x])
        receiver_name = col_rec2.text_input("القائم بالاستلام (اسم الموظف المستلم):")
        receipt_date = col_rec3.date_input("تاريخ الاستلام", value=datetime.today())
       
        if st.button("✅ تأكيد استلام الشحنة", type="primary"):
            if not receiver_name:
                st.error("⚠️ يرجى كتابة اسم الموظف المستلم.")
            else:
                try:
                    update_data = {
                        "receiver_name": receiver_name,
                        "receipt_date": str(receipt_date),
                        "status": "تم الاستلام"
                    }
                    supabase.table("transfers").update(update_data).eq("id", selected_id).execute()
                    st.toast("🎉 تم تأكيد الاستلام بنجاح!", icon="✅")
                    st.success("🎉 تم تأكيد استلام التحويلة وتحديث قاعدة البيانات السحابية!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء تأكيد الاستلام: {e}")
               
# --- التبويب الثالث: سجل التحويلات الكلي ---
with tab3:
    st.subheader("السجل العام لكافة التحويلات بين الفروع 📋")

    try:
        res_all = supabase.table("transfers").select("*").order("id", desc=True).execute()
       
        if res_all.data:
            df_all = pd.DataFrame(res_all.data)
           
            cols_to_show = [
                'transfer_code', 'from_branch', 'target_branch',
                'transfer_date', 'sender_name', 'status',
                'receipt_date', 'receiver_name', 'notes'
            ]
            existing_cols = [c for c in cols_to_show if c in df_all.columns]
           
            df_all_renamed = df_all[existing_cols].rename(columns={
                'transfer_code': 'رقم التحويلة',
                'from_branch': 'من فرع',
                'target_branch': 'إلى فرع',
                'transfer_date': 'تاريخ التحويل',
                'sender_name': 'القائم بالتحويل',
                'status': 'الحالة',
                'receipt_date': 'تاريخ الاستلام',
                'receiver_name': 'القائم بالاستلام',
                'notes': 'ملحوظات'
            })
           
            st.dataframe(df_all_renamed, use_container_width=True)
        else:
            st.info("لا توجد تحويلات مسجلة بعد.")
           
    except Exception as e:
        st.error(f"تنبيه من قاعدة البيانات: {e}")
