import sqlite3
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# إعدادات الصفحة والتحديث التلقائي المدمج
# ==========================================
st.set_page_config(
    page_title="نظام تحويلات الفروع",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# واجهة عربية RTL بدون تطبيق direction على كل عناصر Streamlit الداخلية.
# هذا يمنع ظهور الحروف العربية حرفاً تحت حرف على الموبايل.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, .stApp {
        font-family: 'Cairo', Tahoma, Arial, sans-serif !important;
        direction: rtl !important;
    }

    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }

    [data-testid="stMarkdownContainer"] {
        direction: rtl !important;
        text-align: right !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        direction: rtl !important;
        text-align: right !important;
    }

    .stSelectbox label,
    .stTextInput label,
    .stTextArea label,
    .stDateInput label {
        white-space: normal !important;
        word-break: normal !important;
        overflow-wrap: break-word !important;
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
        font-size: clamp(22px, 4vw, 36px);
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.7rem !important;
        }

        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }

        .main-header h1 {
            font-size: 23px !important;
            line-height: 1.55 !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            white-space: nowrap !important;
        }

        .stTabs [data-baseweb="tab"] {
            flex-shrink: 0 !important;
            white-space: nowrap !important;
        }

        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<div class='main-header'><h1>📦 نظام تسجيل واستلام التحويلات بين الفروع</h1></div>",
    unsafe_allow_html=True
)

# ==========================================
# 2. الاتصال بقاعدة بيانات Supabase
# ==========================================
# يمكنك وضع القيم هنا مباشرة أو في Secrets
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

with st.sidebar:
    st.header("⚙️ إعدادات الجهاز")
    current_branch = st.selectbox("اختر الفرع الحالي للجهاز:", BRANCHES)

# ==========================================
# 3. تبويبات النظام
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
                st.success(f"✅ تم تسجيل التحويلة رقم ({transfer_code}) بنجاح في السحابة!")
                st.rerun()

# --- التبويب الثاني: استلام التحويلات الواردة ---
with tab2:
    st.subheader(f"التحويلات الواردة إلى فرع [{current_branch}] (بانتظار التأكيد)")
       
    try:
       if current_branch:
            res = (supabase.table("transfers").select("*").eq("target_branch", str(current_branch)).eq("status", "قيد الانتظار").execute())
            incoming_data = res.data
       else:
            incoming_data = []
    except Exception as e:
        st.error(f"تنبيه من قاعدة البيانات: {e}")
        incoming_data = []

    if not incoming_data:
        st.info("✨ لا توجد تحويلات قيد الانتظار لهذا الفرع حالياً.")
    else:
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
                update_data = {
                    "receiver_name": receiver_name,
                    "receipt_date": str(receipt_date),
                    "status": "تم الاستلام"
                }
                supabase.table("transfers").update(update_data).eq("id", selected_id).execute()
                st.success("🎉 تم تأكيد استلام التحويلة وتحديث قاعدة البيانات السحابية!")
                st.rerun()
                
# --- التبويب الثالث: سجل التحويلات الكلي ---
with tab3:
    st.subheader("السجل العام لكافة التحويلات بين الفروع 📋")

    try:
        res_all = supabase.table("transfers").select("*").order("id", desc=True).execute()
        
        if res_all.data:
            df_all = pd.DataFrame(res_all.data)
            
            # إعادة تسمية الأعمدة للعرض باللغة العربية
            df_all_renamed = df_all.rename(columns={
                'from_branch': 'الفرع',
                'transfer_date': 'تاريخ التحويل',
                'transfer_code': 'رقم التحويلة',
                'sender_name': 'القائم بالتحويل',
                'target_branch': 'الفرع المحول إليه',
                'receiver_name': 'القائم بالاستلام',
                'receipt_date': 'تاريخ الاستلام',
                'status': 'الحالة',
                'notes': 'ملحوظات'
            })
            
            st.dataframe(df_all_renamed, use_container_width=True)
        else:
            st.info("لا توجد تحويلات مسجلة بعد.")
            
    except Exception as e:
        st.error(f"تنبيه من قاعدة البيانات: {e}")
