import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# إعدادات الصفحة والتحديث التلقائي المدمج
# ==========================================
st.set_page_config(page_title="نظام تحويلات الفروع", page_icon="📦", layout="wide")

# زر يدوي سريع أو إعادة تحميل تلقائي بـ HTML بسيط لو محتاجه


# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="نظام تحويلات الفروع", page_icon="📦", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .stDataFrame { direction: rtl; }
</style>
""", unsafe_allow_html=True)

st.title("📦 نظام تسجيل واستلام التحويلات بين الفروع")

# ==========================================
# 2. الاتصال بقاعدة بيانات Supabase
# ==========================================
# يمكنك وضع القيم هنا مباشرة أو في Secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "ضع_رابط_المشروع_هنا")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "ضع_المفتاح_الخاص_هنا")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error("⚠️ يرجى ضبط بيانات الاتصال بـ Supabase")

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
    
    res = supabase.table("transfers").select("*").eq("target_branch", current_branch).eq("status", "قيد الانتظار").execute()
    incoming_data = res.data
    
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
    st.subheader("📋 السجل العام لكافة التحويلات بين الفروع")
    
    res_all = supabase.table("transfers").select("*").order("id", desc=True).execute()
    if res_all.data:
        df_all = pd.DataFrame(res_all.data)
        df_all_renamed = df_all[['from_branch', 'transfer_date', 'transfer_code', 'sender_name', 'target_branch', 'receiver_name', 'receipt_date', 'status', 'notes']].rename(columns={
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

st.markdown("<div class='main-header'><h1>📦 نظام تسجيل واستلام التحويلات بين الفروع</h1></div>", unsafe_allow_html=True)

# ==========================================
# 2. إعداد قاعدة البيانات (SQLite)
# ==========================================
DB_FILE = "transfers_db.sqlite"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
CREATE TABLE IF NOT EXISTS transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_branch TEXT NOT NULL,
    transfer_date TEXT NOT NULL,
    transfer_code TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    receiver_name TEXT,
    receipt_date TEXT,
    status TEXT DEFAULT 'قيد الانتظار',
    notes TEXT
)
    ''')
    conn.commit()
    conn.close()

init_db()

# قائمة الفروع المتاحة
BRANCHES = ["دمياط", "المعادي", "الجلاء", "المطار", "المهندسين"]

# ==========================================
# 3. إعدادات القائمة الجانبية
# ==========================================
with st.sidebar:
    st.header("⚙️ إعدادات الجهاز")
    current_user_branch = st.selectbox("اختر الفرع الحالي للجهاز:", BRANCHES, index=0)
    st.divider()
    st.info("""
💡 **ملاحظة:** 
هذا التطبيق مصمم للعمل كـ Web App أو تطبيق محلي للربط بين الفروع مباشرة وتحديث جدول التحويلات في الوقت الفعلي.
""")

# ==========================================
# 4. تبويبات النظام (إرسال / استلام / تقارير)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📤 تسجيل تحويل جديد (إرسال)", "📥 استلام التحويلات الواردة", "📊 سجل التحويلات الشامل"])

# --- التبويب الأول: إرسال تحويل ---
with tab1:
    st.subheader("إرسال تحويل جديد إلى فرع آخر")
    
    with st.form("new_transfer_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            from_branch = st.selectbox("الفرع المصدر:", [current_user_branch] + [b for b in BRANCHES if b != current_user_branch])
            transfer_date = st.date_input("تاريخ التحويل", value=datetime.today())
            
        with col2:
            transfer_code = st.text_input("رقم التحويلة / الفاتورة (مثال: 12351)")
            sender_name = st.text_input("القائم بالتحويل (اسم الموظف):")
            
        with col3:
            target_branch = st.selectbox("الفرع المحول إليه:", [b for b in BRANCHES if b != from_branch])
            notes = st.text_area("ملحوظات / الأصناف المحولة:", height=100)
            
        submit_btn = st.form_submit_button("🚀 إرسال التحويلة", use_container_width=True)
        
        if submit_btn:
            if not transfer_code or not sender_name:
                st.error("⚠️ يرجى ملء كافة البيانات الأساسية (رقم التحويلة واسم الموظف).")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO transfers (from_branch, transfer_date, transfer_code, sender_name, target_branch, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (from_branch, str(transfer_date), transfer_code, sender_name, target_branch, notes))
                conn.commit()
                conn.close()
                st.success(f"✅ تم تسجيل التحويلة رقم ({transfer_code}) بنجاح وإرسالها إلى فرع {target_branch}!")

# --- التبويب الثاني: استلام التحويلات الواردة مع إشعارات لحظية ---
with tab2:
    # جلب التحويلات الواردة للفرع الحالي
    res = supabase.table("transfers").select("*").eq("target_branch", current_branch).eq("status", "قيد الانتظار").execute()
    incoming_data = res.data
    
    # 🔔 آلية الإشعارات:
    if incoming_data:
        count = len(incoming_data)
        # 1. إشعار منبثق سريع في أسفل الشاشة
        st.toast(f"🔔 لديك {count} تحويلة/تحويلات جديدة بانتظار التأكيد!", icon="📦")
        
        # 2. تنبيه بارز ملون أعلى الصفحة
        st.error(f"🚨 **تنبيه فرع [{current_branch}]:** يوجد عدد ({count}) تحويلة واردة جديدة إليك الآن. يرجى مراجعتها وتأكيد الاستلام بالأسفل.")
    else:
        st.success("✨ لا توجد أي تحويلات قيد الانتظار لهذا الفرع حالياً.")

    st.subheader(f"قائمة التحويلات الواردة إلى فرع [{current_branch}]")
    
    if incoming_data:
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
        
        # نموذج الاستلام
        st.subheader("تأكيد استلام تحويلة")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        
        options = {row['id']: f"تحويلة رقم: {row['transfer_code']} من فرع {row['from_branch']}" for row in incoming_data}
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
    st.subheader("📋 السجل العام لكافة التحويلات بين الفروع (مطابق للجدول المطلوبة)")
    
    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query('''
        SELECT 
            from_branch AS 'الفرع',
            transfer_date AS 'تاريخ التحويل',
            transfer_code AS 'رقم التحويلة',
            sender_name AS 'القائم بالتحويل',
            target_branch AS 'الفرع المحول إليه',
            sender_name AS 'القائم بالاستلام',
            receipt_date AS 'تاريخ الاستلام',
            status AS 'الحالة',
            notes AS 'ملحوظات'
        FROM transfers
        ORDER BY id DESC
    ''', conn)
    conn.close()
    
    st.dataframe(df_all, use_container_width=True)

