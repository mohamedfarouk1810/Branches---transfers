import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime


# ==========================================
# 1. إعدادات الصفحة والواجهة
# ==========================================
st.set_page_config(
    page_title="نظام إدارة تحويلات الفروع",
    page_icon="📦",
    layout="wide"
)


# تحسين مظهر الواجهة بدعم اللغة العربية (RTL)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .stTable, .stDataFrame {
        direction: rtl;
    }
    .main-header {
        background-color: #0d6efd;
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


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
BRANCHES = ["دمياط", "المعادي", "الجلاء", "المهندسين"]


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


# --- التبويب الثاني: استلام التحويلات الواردة ---
with tab2:
    st.subheader(f"التحويلات الواردة إلى فرع [{current_user_branch}] (بانتظار التأكيد)")
    
    conn = sqlite3.connect(DB_FILE)
    df_incoming = pd.read_sql_query('''
        SELECT id, from_branch AS 'الفرع المرسل', transfer_date AS 'تاريخ التحويل', 
               transfer_code AS 'رقم التحويلة', sender_name AS 'القائم بالتحويل', 
               notes AS 'الملاحظات', status AS 'الحالة'
        FROM transfers 
        WHERE target_branch = ? AND status = 'قيد الانتظار'
    ''', conn, params=(current_user_branch,))
    conn.close()
    
    if df_incoming.empty:
        st.info("✨ لا توجد تحويلات قيد الانتظار لهذا الفرع حالياً.")
    else:
        st.dataframe(df_incoming.drop(columns=['id']), use_container_width=True)
        st.divider()
        
        st.subheader("تأكيد استلام تحويلة")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        
        selected_id = col_rec1.selectbox("اختر رقم التحويلة للاستلام:", df_incoming['id'].tolist(), 
                                         format_func=lambda x: f"تحويلة رقم: {df_incoming[df_incoming['id']==x]['رقم التحويلة'].values[0]} من {df_incoming[df_incoming['id']==x]['الفرع المرسل'].values[0]}")
        receiver_name = col_rec2.text_input("القائم بالاستلام (اسم الموظف المستلم):")
        receipt_date = col_rec3.date_input("تاريخ الاستلام", value=datetime.today())
        
        if st.button("✅ تأكيد استلام الشحنة", type="primary"):
            if not receiver_name:
                st.error("⚠️ يرجى كتابة اسم الموظف المستلم.")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    UPDATE transfers 
                    SET receiver_name = ?, receipt_date = ?, status = 'تم الاستلام'
                    WHERE id = ?
                ''', (receiver_name, str(receipt_date), selected_id))
                conn.commit()
                conn.close()
                st.success("🎉 تم تأكيد استلام التحويلة وتحديث السجل بنجاح!")
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
